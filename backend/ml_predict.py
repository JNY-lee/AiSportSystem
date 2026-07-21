import os
os.environ["TF_XNNPACK_DELEGATE"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
os.environ["MEDIAPIPE_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MEDIAPIPE_DISABLE_MODEL_DOWNLOAD"] = "1"

import joblib
import numpy as np
try:
    from pose_detector import extract_full_feature, get_defect_landmarks
except ImportError:
    from utils.pose_detector import extract_full_feature, get_defect_landmarks

FEAT_TYPE_DIM = 66
MODEL_PATHS = {
    "type_model": "models/type_model.pkl",
    "type_scaler": "models/type_scaler.pkl",
    "type_le": "models/type_le.pkl",
    "quality_model": "models/quality_model.pkl",
    "quality_scaler": "models/quality_scaler.pkl",
    "quality_le": "models/quality_le.pkl"
}
GLOBAL_MODELS = None
ACT_VOTE_WIN = 8


class _ActionVoteBuffer:
    """
    【修复】将投票缓冲区从模块级全局变量改为类实例。
    解决多视频/多请求共享同一个buffer导致识别错乱的问题。
    """
    def __init__(self, win_size=ACT_VOTE_WIN):
        self.win_size = win_size
        self.buffer = []

    def append(self, action, conf):
        self.buffer.append((action, conf))
        if len(self.buffer) > self.win_size:
            self.buffer.pop(0)

    def vote(self):
        """加权投票，返回 (best_action, avg_conf)"""
        if not self.buffer:
            return "push-up", 0.0
        vote_dict = {"push-up": 0.0, "pullUp": 0.0, "squat": 0.0}
        for act, conf in self.buffer:
            if act in vote_dict:
                vote_dict[act] += conf
        final_act = max(vote_dict.items(), key=lambda x: x[1])[0]
        final_conf = vote_dict[final_act] / len(self.buffer)
        return final_act, round(final_conf, 4)

    def reset(self):
        self.buffer.clear()


class _ScoreBuffer:
    """
    【修复】将分数缓冲区从模块级全局变量改为类实例。
    """
    def __init__(self, win_size=8):
        self.win_size = win_size
        self.buffer = []

    def append(self, val):
        if not isinstance(val, (int, float)) or np.isnan(val) or np.isinf(val):
            val = 0.0
        self.buffer.append(val)
        if len(self.buffer) > self.win_size:
            self.buffer.pop(0)

    def mean(self):
        if not self.buffer:
            return 0.0
        return round(np.mean(self.buffer), 1)

    def reset(self):
        self.buffer.clear()


# 创建全局单例（向后兼容，但每次处理新视频时应调用 reset_instance_buffers）
_global_vote = _ActionVoteBuffer()
_global_score = _ScoreBuffer()


def reset_instance_buffers():
    """【修复】新增 —— 处理新视频/新请求前重置全局缓冲区"""
    _global_vote.reset()
    _global_score.reset()


def load_models():
    global GLOBAL_MODELS
    if GLOBAL_MODELS is not None:
        return GLOBAL_MODELS
    models = {}
    for name, path in MODEL_PATHS.items():
        if not os.path.exists(path):
            print(f"警告：缺失模型 {path}，将使用规则兜底")
            return None
        models[name] = joblib.load(path)
    GLOBAL_MODELS = models
    return models

def smooth_score(raw_score):
    """【修复】保留向后兼容的接口，内部委托给实例缓冲区"""
    _global_score.append(raw_score)
    return _global_score.mean()

def predict_frame(img):
    """
    单帧预测，返回 (action, act_conf, good_conf, knee_offset, waist_diff, hip_amp)
    【修复】使用实例缓冲区替代模块级全局变量
    """
    md = load_models()
    if md is None:
        # 模型缺失：使用规则简单分类（基于角度）
        res = get_defect_landmarks(img)
        if res is None or res[0] is None:
            return "push-up", 0.0, 0.5, 0.0, 0.0, 0.0
        _, body_vert, avg_elbow, avg_knee, _ = res
        if np.isnan(avg_knee) and np.isnan(avg_elbow):
            return "push-up", 0.0, 0.5, 0.0, 0.0, 0.0
        # 简单规则
        if avg_knee < 110:
            act = "squat"
        elif body_vert < 0.40:
            act = "push-up"
        else:
            act = "pullUp"
        return act, 0.0, 0.5, 0.0, 0.0, 0.0

    TYPE_MODEL = md["type_model"]
    TYPE_SCALER = md["type_scaler"]
    TYPE_LE = md["type_le"]
    QUALITY_MODEL = md["quality_model"]
    QUALITY_SCALER = md["quality_scaler"]
    QUALITY_LE = md["quality_le"]

    feats = extract_full_feature(img)
    if feats is None:
        return "push-up", 0.0, 0.5, 0.0, 0.0, 0.0
    type_feat, quality_feat = feats
    if len(type_feat) != FEAT_TYPE_DIM:
        return "push-up", 0.0, 0.5, 0.0, 0.0, 0.0

    try:
        X_type = TYPE_SCALER.transform(np.array(type_feat, dtype=np.float32).reshape(1, -1))
        prob = TYPE_MODEL.predict_proba(X_type)[0]
        idx = np.argmax(prob)
        raw_act = TYPE_LE.inverse_transform([idx])[0]
        raw_conf = float(prob[idx])
    except Exception:
        # 预测异常时兜底
        return "push-up", 0.0, 0.5, 0.0, 0.0, 0.0

    # 【修复】使用实例缓冲区投票
    _global_vote.append(raw_act, raw_conf)
    final_act, final_conf = _global_vote.vote()

    # 质量预测
    try:
        full_feat = type_feat + quality_feat
        X_qual = QUALITY_SCALER.transform(np.array(full_feat, dtype=np.float32).reshape(1, -1))
        qual_prob = QUALITY_MODEL.predict_proba(X_qual)[0]
        good_idx = list(QUALITY_LE.classes_).index("good") if "good" in QUALITY_LE.classes_ else 0
        good_conf = round(float(qual_prob[good_idx]), 4)
    except Exception:
        good_conf = 0.5

    knee_offset, waist_diff, hip_amp = quality_feat
    return final_act, round(final_conf, 4), good_conf, knee_offset, waist_diff, hip_amp
