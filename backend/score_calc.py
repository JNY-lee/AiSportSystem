import numpy as np

DEFECT_RULE = {
    "push-up": {
        "knee_check": False,
        "waist_thresh": 0.15,
        "hip_thresh": 0.10,
        "hip_text": "身体幅度不足"
    },
    "pullUp": {
        "knee_check": False,
        "waist_thresh": 0.13,
        "hip_thresh": 0.15,
        "hip_text": "拉升幅度不足"
    },
    "squat": {
        "knee_check": True,
        "knee_thresh": 0.10,
        "waist_thresh": 0.12,
        "hip_thresh": 0.12,
        "hip_text": "臀部幅度不足"
    }
}

# 【修复】默认规则：任何未知动作类型都能安全处理
_DEFAULT_RULE = {
    "knee_check": False,
    "waist_thresh": 0.15,
    "hip_thresh": 0.10,
    "hip_text": "动作幅度不足"
}


def calc_score(good_conf, knee_offset, waist_diff, hip_amp, act_type):
    """
    计算动作质量分数，返回 (score, defects_list)
    【修复】增强参数安全校验，防止NaN/None/非法值导致连锁报错
    """
    # 参数防御：确保所有数值参数是合法数字
    try:
        if good_conf is None or (isinstance(good_conf, float) and (np.isnan(good_conf) or np.isinf(good_conf))):
            good_conf = 0.0
        good_conf = float(good_conf)
    except (TypeError, ValueError):
        good_conf = 0.0

    try:
        if knee_offset is None or (isinstance(knee_offset, float) and (np.isnan(knee_offset) or np.isinf(knee_offset))):
            knee_offset = 0.0
        knee_offset = float(knee_offset)
    except (TypeError, ValueError):
        knee_offset = 0.0

    try:
        if waist_diff is None or (isinstance(waist_diff, float) and (np.isnan(waist_diff) or np.isinf(waist_diff))):
            waist_diff = 0.0
        waist_diff = float(waist_diff)
    except (TypeError, ValueError):
        waist_diff = 0.0

    try:
        if hip_amp is None or (isinstance(hip_amp, float) and (np.isnan(hip_amp) or np.isinf(hip_amp))):
            hip_amp = 0.0
        hip_amp = float(hip_amp)
    except (TypeError, ValueError):
        hip_amp = 0.0

    if not act_type or not isinstance(act_type, str):
        act_type = "push-up"

    # 【修复】安全获取规则，未知动作使用默认规则
    rule = DEFECT_RULE.get(act_type, _DEFAULT_RULE)

    # 【修复】基础分计算：
    # 原逻辑：good_conf=0.5时基础分=50，太低了（good_conf是质量模型预测的概率值，不代表分数）
    # 新逻辑：以80分为基准，good_conf越高分数越高，good_conf越低分数越低
    # good_conf在0.3~0.7之间浮动是正常的（3分类模型概率），不应直接乘以100
    if good_conf <= 0.0 or np.isnan(good_conf):
        base = 75.0  # 无质量模型信息时，给一个中等偏上的基础分
    else:
        # good_conf范围通常在0.3~0.9，映射到60~100分
        base = 60.0 + good_conf * 44.0  # 0.5→82, 0.7→91, 0.9→100

    deduct = 0
    defects = []

    if rule["knee_check"] and knee_offset > rule["knee_thresh"]:
        d = np.clip((knee_offset - rule["knee_thresh"]) * 150, 5, 15)
        deduct += d
        defects.append("膝盖内扣")

    if waist_diff > rule["waist_thresh"]:
        d = np.clip((waist_diff - rule["waist_thresh"]) * 200, 8, 20)
        deduct += d
        defects.append("腰部塌陷")

    if hip_amp < rule["hip_thresh"]:
        d = np.clip((rule["hip_thresh"] - hip_amp) * 100, 5, 15)
        deduct += d
        defects.append(rule["hip_text"])

    final_score = np.clip(base - deduct, 0, 100)
    return round(final_score, 1), defects
