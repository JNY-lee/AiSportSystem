
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report

os.makedirs("models", exist_ok=True)
# 修复：特征维度更新为132（33点 * 4维）
FEAT_TYPE_DIM = 132

def train_type_model():
    print("====训练动作分类模型（修复版）====")
    X_train_raw = None
    y_train_raw = None
    X_test_raw = None
    y_test_raw = None

    # 读取训练集
    if os.path.exists("type_train.csv"):
        df_train = pd.read_csv("type_train.csv")
        if not df_train.empty and len(df_train) > 0:
            # 修复：正确提取前132维特征
            feat_cols = [c for c in df_train.columns if c.startswith(("x", "y", "z", "v"))]
            if len(feat_cols) >= FEAT_TYPE_DIM:
                X_train_raw = df_train[feat_cols[:FEAT_TYPE_DIM]].values
            else:
                # 兼容旧版66维
                X_train_raw = df_train.iloc[:, :min(FEAT_TYPE_DIM, len(feat_cols))].values
            y_train_raw = df_train["sport_type"].values
    # 读取测试集
    if os.path.exists("type_test.csv"):
        df_test = pd.read_csv("type_test.csv")
        if not df_test.empty and len(df_test) > 0:
            feat_cols = [c for c in df_test.columns if c.startswith(("x", "y", "z", "v"))]
            if len(feat_cols) >= FEAT_TYPE_DIM:
                X_test_raw = df_test[feat_cols[:FEAT_TYPE_DIM]].values
            else:
                X_test_raw = df_test.iloc[:, :min(FEAT_TYPE_DIM, len(feat_cols))].values
            y_test_raw = df_test["sport_type"].values

    # 多层校验
    if (X_train_raw is None or len(X_train_raw) == 0 or
        y_train_raw is None or len(y_train_raw) == 0 or
        X_test_raw is None or len(X_test_raw) == 0 or
        y_test_raw is None or len(y_test_raw) == 0):
        print("❌ 动作分类数据集为空，请重新运行 feature_extract.py 生成足量特征数据！")
        return

    print(f"训练样本: {len(X_train_raw)}, 测试样本: {len(X_test_raw)}")
    print(f"特征维度: {X_train_raw.shape[1]}")

    # 标准化
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    le = LabelEncoder()
    y_train = le.fit_transform(y_train_raw)
    y_test = le.transform(y_test_raw)

    # 校验训练样本数量
    if len(X_train) < 20:
        print(f"⚠️ 训练样本仅{len(X_train)}条，不足20，跳过5折交叉验证")
        skf = None
    else:
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # 修复：优化模型参数，增加泛化能力
    model = RandomForestClassifier(
        n_estimators=500,        # 增加树数量
        max_depth=15,            # 适当增加深度
        min_samples_split=3,     # 降低分裂阈值
        min_samples_leaf=1,      # 允许单样本叶子
        class_weight="balanced",
        random_state=42,
        n_jobs=-1                # 使用所有CPU核心
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
    print(f"动作分类模型测试准确率: {acc:.4f}")
    print(classification_report(y_test, pred, target_names=le.classes_))

    # 有足够样本才执行交叉验证
    if skf is not None:
        cv_scores = cross_val_score(model, X_train, y=y_train, cv=skf)
        print(f"5折交叉均值：{cv_scores.mean():.4f}，标准差：{cv_scores.std():.4f}")

    joblib.dump(model, "models/type_model.pkl")
    joblib.dump(scaler, "models/type_scaler.pkl")
    joblib.dump(le, "models/type_le.pkl")
    print("✅ 动作分类模型保存完成\n")

def train_quality_model():
    print("====训练质量评估模型（修复版）====")
    X_train_raw = None
    y_train_raw = None
    X_test_raw = None
    y_test_raw = None

    if os.path.exists("quality_train.csv"):
        df_train = pd.read_csv("quality_train.csv")
        if not df_train.empty and len(df_train) > 0:
            # 修复：正确提取特征列（排除最后3列：body_scale, sport_type, quality）
            feat_cols = [c for c in df_train.columns if c not in ["sport_type", "quality", "body_scale"]]
            X_train_raw = df_train[feat_cols].values
            y_train_raw = df_train["quality"].values
    if os.path.exists("quality_test.csv"):
        df_test = pd.read_csv("quality_test.csv")
        if not df_test.empty and len(df_test) > 0:
            feat_cols = [c for c in df_test.columns if c not in ["sport_type", "quality", "body_scale"]]
            X_test_raw = df_test[feat_cols].values
            y_test_raw = df_test["quality"].values

    if (X_train_raw is None or len(X_train_raw) == 0 or
        y_train_raw is None or len(y_train_raw) == 0 or
        X_test_raw is None or len(X_test_raw) == 0 or
        y_test_raw is None or len(y_test_raw) == 0):
        print("❌ 质量分类数据集为空，请重新运行 feature_extract.py 生成足量特征数据！")
        return

    print(f"训练样本: {len(X_train_raw)}, 测试样本: {len(X_test_raw)}")
    print(f"特征维度: {X_train_raw.shape[1]}")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    le = LabelEncoder()
    y_train = le.fit_transform(y_train_raw)
    y_test = le.transform(y_test_raw)

    if len(X_train) < 20:
        print(f"⚠️ 训练样本仅{len(X_train)}条，不足20，跳过5折交叉验证")
        skf = None
    else:
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # 修复：优化质量模型参数
    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=12,
        min_samples_split=3,
        min_samples_leaf=1,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
    print(f"质量二分类测试准确率: {acc:.4f}")
    print(classification_report(y_test, pred, target_names=le.classes_))

    if skf is not None:
        cv_scores = cross_val_score(model, X_train, y=y_train, cv=skf)
        print(f"5折交叉均值：{cv_scores.mean():.4f}，标准差：{cv_scores.std():.4f}")

    joblib.dump(model, "models/quality_model.pkl")
    joblib.dump(scaler, "models/quality_scaler.pkl")
    joblib.dump(le, "models/quality_le.pkl")
    print("✅ 质量评估模型保存完成")

if __name__ == "__main__":
    train_type_model()
    train_quality_model()
    print("\n===== 全部模型训练流程执行完毕（修复版） =====")