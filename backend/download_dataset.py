import os
import cv2
import pandas as pd

DATA_ROOT = r"./dataset/Splitted_full_data"
train_dir = os.path.join(DATA_ROOT, "train")
test_dir = os.path.join(DATA_ROOT, "test")
TARGET_LABELS = {"pull Up", "squat", "push-up"}

def manual_label_quality(vid_path):
    """人工标注函数，实际项目替换可视化标注工具，这里模拟"""
    # 真实项目：打开视频人工标记 good / bad
    cap = cv2.VideoCapture(vid_path)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return "bad"
    # 模拟均衡数据集，随机划分（实际人工标注替换此处）
    import random
    return "good" if random.random() > 0.4 else "bad"

def read_split_folder(split_path):
    samples = []
    action_folders = os.listdir(split_path)
    for act_name in action_folders:
        if act_name not in TARGET_LABELS:
            continue
        act_path = os.path.join(split_path, act_name)
        if not os.path.isdir(act_path):
            continue
        file_list = os.listdir(act_path)
        for fname in file_list:
            if not fname.endswith(".mp4"):
                continue
            fpath = os.path.join(act_path, fname)
            if os.path.getsize(fpath) < 1024:
                continue
            quality = manual_label_quality(fpath)
            samples.append([fpath, act_name, quality])
    return samples

if __name__ == "__main__":
    train_samples = read_split_folder(train_dir)
    test_samples = read_split_folder(test_dir)
    train_df = pd.DataFrame(train_samples, columns=["file_path", "sport_type", "quality"])
    test_df = pd.DataFrame(test_samples, columns=["file_path", "sport_type", "quality"])
    train_df.to_csv("dataset_quality_train.csv", index=False, encoding="utf-8")
    test_df.to_csv("dataset_quality_test.csv", index=False, encoding="utf-8")
    print("数据集标注完成，字段：file_path,sport_type,quality")
    print(train_df["sport_type"].value_counts())
    print(train_df["quality"].value_counts())