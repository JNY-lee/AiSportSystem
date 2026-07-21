import os
os.environ["TF_XNNPACK_DELEGATE"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
os.environ["MEDIAPIPE_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MEDIAPIPE_DISABLE_MODEL_DOWNLOAD"] = "1"

import cv2
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

pose_model = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

LANDMARK_IDX = {
    "NOSE":0, "L_SHOULDER":11, "R_SHOULDER":12,
    "L_ELBOW":13, "R_ELBOW":14, "L_WRIST":15, "R_WRIST":16,
    "L_HIP":23, "R_HIP":24, "L_KNEE":25, "R_KNEE":26,
    "L_ANKLE":27, "R_ANKLE":28
}

ACTION_THRESH = {
    "push-up": {
        "elbow_up": 140,
        "elbow_down": 100,
        "body_vertical": 0.40
    },
    "pullUp": {
        "elbow_up": 145,
        "elbow_down": 95,
        "body_vertical": 0.60
    },
    "squat": {
        "knee_up": 130,
        "knee_down": 105,
        "knee_active": 120
    }
}

SMOOTH_FRAME = 6
COOL_DOWN_FRAMES = 5
MIN_VALID_FRAMES = 2

def calc_angle(p1, p2, p3):
    if p1 is None or p2 is None or p3 is None:
        return np.nan
    v1 = np.array([p1[0]-p2[0], p1[1]-p2[1]])
    v2 = np.array([p3[0]-p2[0], p3[1]-p2[1]])
    dot = np.dot(v1, v2)
    mag1 = np.linalg.norm(v1)
    mag2 = np.linalg.norm(v2)
    if mag1 < 1e-6 or mag2 < 1e-6:
        return np.nan
    rad = np.arccos(np.clip(dot/(mag1*mag2), -1.0, 1.0))
    return np.rad2deg(rad)

def get_defect_landmarks(frame):
    """提取人体关键点和计算角度，返回 (landmarks, body_vertical, avg_elbow, avg_knee, angles)"""
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = pose_model.process(rgb)
    default_ret = (None, 0.0, np.nan, np.nan, [np.nan]*4)
    if not res.pose_landmarks:
        return default_ret

    landmarks = []
    for lm in res.pose_landmarks.landmark:
        landmarks.append([lm.x, lm.y, lm.z, lm.visibility])

    def get_pt(name):
        idx = LANDMARK_IDX[name]
        point = landmarks[idx]
        if point[3] < 0.1:
            return None
        return (point[0], point[1])

    ls = get_pt("L_SHOULDER")
    rs = get_pt("R_SHOULDER")
    le = get_pt("L_ELBOW")
    re = get_pt("R_ELBOW")
    lw = get_pt("L_WRIST")
    rw = get_pt("R_WRIST")
    lh = get_pt("L_HIP")
    rh = get_pt("R_HIP")
    lk = get_pt("L_KNEE")
    rk = get_pt("R_KNEE")
    la = get_pt("L_ANKLE")
    ra = get_pt("R_ANKLE")

    l_el = calc_angle(ls, le, lw) if all([ls,le,lw]) else np.nan
    r_el = calc_angle(rs, re, rw) if all([rs,re,rw]) else np.nan
    l_kn = calc_angle(lh, lk, la) if all([lh,lk,la]) else np.nan
    r_kn = calc_angle(rh, rk, ra) if all([rh,rk,ra]) else np.nan
    angles = [l_el, r_el, l_kn, r_kn]

    body_vertical = 0.0
    if ls and rs and lh and rh:
        shoulder_y = (ls[1] + rs[1]) / 2
        hip_y = (lh[1] + rh[1]) / 2
        body_vertical = abs(shoulder_y - hip_y)

    avg_knee = np.nanmean([x for x in [l_kn, r_kn] if not np.isnan(x)])
    avg_elbow = np.nanmean([x for x in [l_el, r_el] if not np.isnan(x)])
    return landmarks, body_vertical, avg_elbow, avg_knee, angles

def extract_full_feature(frame):
    """提取完整的66维类型特征 + 3维质量特征"""
    res = get_defect_landmarks(frame)
    lm, body_vert, avg_el, avg_kn, angs = res
    if lm is None:
        return None
    type_feat = []
    for point in lm:
        type_feat.append(point[0])
        type_feat.append(point[1])
    if len(type_feat) < 66:
        type_feat += [0.0]*(66-len(type_feat))
    type_feat = type_feat[:66]

    l_hip_x = lm[LANDMARK_IDX["L_HIP"]][0]
    r_hip_x = lm[LANDMARK_IDX["R_HIP"]][0]
    waist_diff = abs(l_hip_x - r_hip_x)
    l_hip_y = lm[LANDMARK_IDX["L_HIP"]][1]
    l_ank_y = lm[LANDMARK_IDX["L_ANKLE"]][1]
    hip_amp = abs(l_hip_y - l_ank_y)
    l_knee_x = lm[LANDMARK_IDX["L_KNEE"]][0]
    r_knee_x = lm[LANDMARK_IDX["R_KNEE"]][0]
    knee_offset = abs(l_knee_x - r_knee_x)
    quality_feat = [knee_offset, waist_diff, hip_amp]
    return type_feat, quality_feat


def predict(frame):
    """单帧动作预测（简化版，供Flask接口使用）"""
    try:
        try:
            from ml_predict import predict_frame as _pf
        except ImportError:
            from utils.ml_predict import predict_frame as _pf
        act, conf, good_conf, ko, wd, ha = _pf(frame)
        if conf < 0.5:
            return "none", 0.0
        return act, conf
    except Exception:
        pass

    res = get_defect_landmarks(frame)
    lm, body_vert, avg_elbow, avg_knee, angles = res
    if lm is None:
        return "none", 0.0

    if not np.isnan(avg_knee) and avg_knee < 110:
        return "squat", 0.3
    elif body_vert < 0.40:
        return "push-up", 0.3
    else:
        return "pullUp", 0.3


class TimeWindowCounter:
    def __init__(self, window_sec=2.0, default_fps=25):
        self.count_dict = {"push-up": 0, "pullUp": 0, "squat": 0}
        self.state_dict = {"push-up": "UP", "pullUp": "UP", "squat": "UP"}
        self.cool_down_dict = {"push-up": 0, "pullUp": 0, "squat": 0}
        self.angle_buffer = {"elbow": [], "knee": []}
        self.state_switch_count = {"push-up": 0, "pullUp": 0, "squat": 0}
        self.current_action = "push-up"
        self.cool_max = max(3, int(default_fps * 0.2))
        self.smooth_max = max(3, int(default_fps * 0.25))
        self.min_valid = 2

    def _smooth(self, key, val):
        if np.isnan(val):
            return 0.0
        buf = self.angle_buffer[key]
        buf.append(val)
        if len(buf) > self.smooth_max:
            buf.pop(0)
        valid = [x for x in buf if not np.isnan(x)]
        return np.mean(valid) if valid else 0.0

    def update(self, action_name):
        if action_name is None or action_name == "none" or action_name == "unknown":
            action_name = self.current_action
        if action_name in self.count_dict:
            self.current_action = action_name
        else:
            self.current_action = "push-up"
        for k in self.cool_down_dict:
            if self.cool_down_dict[k] > 0:
                self.cool_down_dict[k] -= 1
        return self.count_dict[self.current_action], self.current_action

    def update_with_frame(self, frame, action_name, conf=0.0):
        res = get_defect_landmarks(frame)
        lm, body_vert, raw_elbow, raw_knee, angs = res
        avg_elbow = self._smooth("elbow", raw_elbow)
        avg_knee = self._smooth("knee", raw_knee)

        if action_name in self.count_dict:
            self.current_action = action_name
        else:
            if not np.isnan(avg_knee) and avg_knee < 110:
                self.current_action = "squat"
            elif body_vert < 0.40:
                self.current_action = "push-up"
            else:
                self.current_action = "pullUp"

        for k in self.cool_down_dict:
            if self.cool_down_dict[k] > 0:
                self.cool_down_dict[k] -= 1

        fix_act = self.current_action
        cnt = self.count_dict[fix_act]
        th = ACTION_THRESH[fix_act]

        if self.cool_down_dict[fix_act] == 0:
            if fix_act in ("push-up", "pullUp"):
                if self.state_dict[fix_act] == "UP" and avg_elbow < th["elbow_down"]:
                    self.state_switch_count[fix_act] += 1
                    if self.state_switch_count[fix_act] >= self.min_valid:
                        self.state_dict[fix_act] = "DOWN"
                        self.state_switch_count[fix_act] = 0
                elif self.state_dict[fix_act] == "DOWN" and avg_elbow > th["elbow_up"]:
                    self.state_switch_count[fix_act] += 1
                    if self.state_switch_count[fix_act] >= self.min_valid:
                        self.state_dict[fix_act] = "UP"
                        self.count_dict[fix_act] += 1
                        cnt = self.count_dict[fix_act]
                        self.cool_down_dict[fix_act] = self.cool_max
                        self.state_switch_count[fix_act] = 0
            elif fix_act == "squat":
                if self.state_dict["squat"] == "UP" and avg_knee < th["knee_down"]:
                    self.state_switch_count["squat"] += 1
                    if self.state_switch_count["squat"] >= self.min_valid:
                        self.state_dict["squat"] = "DOWN"
                        self.state_switch_count["squat"] = 0
                elif self.state_dict["squat"] == "DOWN" and avg_knee > th["knee_up"]:
                    self.state_switch_count["squat"] += 1
                    if self.state_switch_count["squat"] >= self.min_valid:
                        self.state_dict["squat"] = "UP"
                        self.count_dict["squat"] += 1
                        cnt = self.count_dict["squat"]
                        self.cool_down_dict["squat"] = self.cool_max
                        self.state_switch_count["squat"] = 0

        return cnt, avg_elbow, avg_knee, fix_act

    @property
    def count(self):
        return self.count_dict[self.current_action]


class ActionCounter:
    """
    核心计数器。
    关键修改:
    1. else分支不清零state_switch_count，允许慢速运动累积
    2. 冷却帧数基于实际帧率
    3. 放宽了计数阈值，适配真实运动幅度
    4. 新增角度变化趋势检测
    5. 【修复核心】动作类型锁定（anti-jitter）：一旦确认动作类型，
       需要连续N帧检测到不同类型才能切换，避免蹲起间隙被误判为push-up
    """
    def __init__(self, video_fps=25):
        self.count_dict = {"push-up": 0, "pullUp": 0, "squat": 0}
        self.state_dict = {"push-up": "UP", "pullUp": "UP", "squat": "UP"}
        self.cool_down_dict = {"push-up": 0, "pullUp": 0, "squat": 0}
        self.angle_buffer = {"elbow": [], "knee": []}
        self.state_switch_count = {"push-up": 0, "pullUp": 0, "squat": 0}
        self.video_fps = max(10, video_fps)
        self.cool_max = max(3, int(self.video_fps * 0.15))
        self.smooth_max = max(3, int(self.video_fps * 0.10))
        self.min_valid = 2
        # 动作类型缓冲区
        self.action_buffer = []
        # 峰值和谷值角度
        self.peak_angle = {"push-up": 170.0, "pullUp": 170.0, "squat": 170.0}
        self.trough_angle = {"push-up": 50.0, "pullUp": 50.0, "squat": 50.0}
        self.min_amplitude = 25.0
        # 【新增】动作锁定机制
        self._locked_action = None          # 当前锁定的动作类型
        self._lock_switch_count = 0         # 连续检测到不同类型的帧数
        self._lock_threshold = max(5, int(self.video_fps * 0.5))  # 需要连续0.5秒才切换

    def smooth_angle(self, angle_type, value):
        if np.isnan(value):
            return 0.0
        buf = self.angle_buffer[angle_type]
        buf.append(value)
        if len(buf) > self.smooth_max:
            buf.pop(0)
        valid = [x for x in buf if not np.isnan(x)]
        return np.mean(valid) if valid else 0.0

    def _get_angle_trend(self, angle_type):
        buf = self.angle_buffer[angle_type]
        if len(buf) < 3:
            return "stable"
        recent = [x for x in buf[-3:] if not np.isnan(x)]
        if len(recent) < 3:
            return "stable"
        diff = recent[-1] - recent[0]
        if diff < -3:
            return "decreasing"
        elif diff > 3:
            return "increasing"
        return "stable"

    def _rule_classify(self, avg_knee, avg_elbow, body_vertical, lm=None):
        """基于关节角度的规则分类（单帧瞬时判断）"""
        has_knee = not np.isnan(avg_knee)
        has_elbow = not np.isnan(avg_elbow)

        # 第一优先：引体向上（手腕在肩膀上方）
        is_pullup_by_wrist = False
        if lm is not None:
            try:
                lw_y = lm[LANDMARK_IDX["L_WRIST"]][1]
                rw_y = lm[LANDMARK_IDX["R_WRIST"]][1]
                ls_y = lm[LANDMARK_IDX["L_SHOULDER"]][1]
                rs_y = lm[LANDMARK_IDX["R_SHOULDER"]][1]
                avg_wrist_y = (lw_y + rw_y) / 2
                avg_shoulder_y = (ls_y + rs_y) / 2
                if avg_shoulder_y - avg_wrist_y > 0.05:
                    is_pullup_by_wrist = True
            except (IndexError, TypeError):
                pass
        if is_pullup_by_wrist:
            return "pullUp"

        # 第二优先：深蹲（膝盖明显弯曲 < 120°）
        if has_knee and avg_knee < 120:
            if not has_elbow or avg_elbow > 130:
                return "squat"

        # 第三优先：body_vertical辅助
        if body_vertical > 0.50:
            return "pullUp"
        elif body_vertical < 0.38:
            return "push-up"

        # 第四优先：模糊区间
        if has_knee and avg_knee > 150:
            if body_vertical < 0.45:
                return "push-up"
            else:
                return "pullUp"

        return "push-up"

    def _lock_action_type(self, raw_action):
        """
        【核心】动作类型锁定（anti-jitter）。
        - 如果当前没有锁定类型，直接使用raw_action并锁定
        - 如果有锁定类型，需要连续N帧检测到不同类型才能解锁切换
        - 深蹲站起时膝盖角度变大（>120），raw_action可能是push-up，
          但不会立刻切换，需要连续0.5秒都是push-up才切换
        """
        if self._locked_action is None:
            self._locked_action = raw_action
            self._lock_switch_count = 0
            return self._locked_action

        if raw_action == self._locked_action:
            self._lock_switch_count = 0  # 重置切换计数
            return self._locked_action

        # 检测到不同类型
        self._lock_switch_count += 1
        if self._lock_switch_count >= self._lock_threshold:
            # 连续N帧都是不同类型，允许切换
            self._locked_action = raw_action
            self._lock_switch_count = 0
            return self._locked_action

        # 还没达到切换阈值，保持锁定
        return self._locked_action

    def update(self, frame, act_model_pred, conf=0.0):
        # 递减所有动作的冷却计数
        for k in self.cool_down_dict:
            if self.cool_down_dict[k] > 0:
                self.cool_down_dict[k] -= 1

        res = get_defect_landmarks(frame)
        lm, body_vert, raw_elbow, raw_knee, angs = res
        avg_elbow = self.smooth_angle("elbow", raw_elbow)
        avg_knee = self.smooth_angle("knee", raw_knee)

        # 规则分类用原始角度（实时性）
        rule_elbow = raw_elbow if not np.isnan(raw_elbow) else avg_elbow
        rule_knee = raw_knee if not np.isnan(raw_knee) else avg_knee

        # 单帧规则分类
        raw_classified = act_model_pred.strip() if act_model_pred else ""
        if conf >= 0.6 and raw_classified in self.count_dict:
            self.action_buffer.append(raw_classified)
            if len(self.action_buffer) > 5:
                self.action_buffer.pop(0)
            if self.action_buffer.count(raw_classified) >= 3:
                pass
            else:
                raw_classified = self._rule_classify(rule_knee, rule_elbow, body_vert, lm)
        else:
            self.action_buffer.clear()
            raw_classified = self._rule_classify(rule_knee, rule_elbow, body_vert, lm)

        if raw_classified not in self.count_dict:
            raw_classified = "push-up"

        # 【修复核心】通过动作锁定机制防抖，避免蹲起间隙切换类型
        fix_act = self._lock_action_type(raw_classified)

        cnt = self.count_dict[fix_act]
        th = ACTION_THRESH[fix_act]

        if self.cool_down_dict[fix_act] == 0:
            if fix_act in ("push-up", "pullUp"):
                self._update_push_or_pull(fix_act, avg_elbow, th)
            elif fix_act == "squat":
                self._update_squat(avg_knee, th)

            cnt = self.count_dict[fix_act]

        return cnt, avg_elbow, avg_knee, fix_act

    def _update_push_or_pull(self, act, avg_elbow, th):
        """俯卧撑/引体向上状态机"""
        state = self.state_dict[act]
        switch_cnt = self.state_switch_count[act]
        trend = self._get_angle_trend("elbow")

        if avg_elbow > self.peak_angle[act]:
            self.peak_angle[act] = avg_elbow
        if avg_elbow < self.trough_angle[act]:
            self.trough_angle[act] = avg_elbow

        if state == "UP":
            going_down = False
            if avg_elbow < th["elbow_down"]:
                going_down = True
            elif trend == "decreasing" and avg_elbow < th["elbow_down"] + 15:
                amplitude = self.peak_angle[act] - avg_elbow
                if amplitude >= self.min_amplitude:
                    going_down = True
            if going_down:
                switch_cnt += 1
                if switch_cnt >= self.min_valid:
                    self.state_dict[act] = "DOWN"
                    self.state_switch_count[act] = 0
                    self.peak_angle[act] = avg_elbow
                else:
                    self.state_switch_count[act] = switch_cnt

        elif state == "DOWN":
            going_up = False
            if avg_elbow > th["elbow_up"]:
                going_up = True
            elif trend == "increasing" and avg_elbow > th["elbow_up"] - 15:
                amplitude = avg_elbow - self.trough_angle[act]
                if amplitude >= self.min_amplitude:
                    going_up = True
            if going_up:
                switch_cnt += 1
                if switch_cnt >= self.min_valid:
                    self.state_dict[act] = "UP"
                    self.count_dict[act] += 1
                    self.cool_down_dict[act] = self.cool_max
                    self.state_switch_count[act] = 0
                    self.trough_angle[act] = avg_elbow
                else:
                    self.state_switch_count[act] = switch_cnt

    def _update_squat(self, avg_knee, th):
        """深蹲状态机"""
        state = self.state_dict["squat"]
        switch_cnt = self.state_switch_count["squat"]
        trend = self._get_angle_trend("knee")

        if avg_knee > self.peak_angle["squat"]:
            self.peak_angle["squat"] = avg_knee
        if avg_knee < self.trough_angle["squat"]:
            self.trough_angle["squat"] = avg_knee

        if state == "UP":
            going_down = False
            if avg_knee < th["knee_down"]:
                going_down = True
            elif trend == "decreasing" and avg_knee < th["knee_down"] + 15:
                amplitude = self.peak_angle["squat"] - avg_knee
                if amplitude >= self.min_amplitude:
                    going_down = True
            if going_down:
                switch_cnt += 1
                if switch_cnt >= self.min_valid:
                    self.state_dict["squat"] = "DOWN"
                    self.state_switch_count["squat"] = 0
                    self.peak_angle["squat"] = avg_knee
                else:
                    self.state_switch_count["squat"] = switch_cnt

        elif state == "DOWN":
            going_up = False
            if avg_knee > th["knee_up"]:
                going_up = True
            elif trend == "increasing" and avg_knee > th["knee_up"] - 15:
                amplitude = avg_knee - self.trough_angle["squat"]
                if amplitude >= self.min_amplitude:
                    going_up = True
            if going_up:
                switch_cnt += 1
                if switch_cnt >= self.min_valid:
                    self.state_dict["squat"] = "UP"
                    self.count_dict["squat"] += 1
                    self.cool_down_dict["squat"] = self.cool_max
                    self.state_switch_count["squat"] = 0
                    self.trough_angle["squat"] = avg_knee
                else:
                    self.state_switch_count["squat"] = switch_cnt
