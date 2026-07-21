
import os
import cv2
import pandas as pd
from pose_detector import extract_full_feature
from download_dataset import read_split_folder

def generate_feature_csv(split_path, out_csv):
    print(f"【开始处理】数据集路径: {split_path}, 输出文件: {out_csv}")
    if not os.path.exists(split_path):
        print(f"【错误】文件夹不存在: {split_path}")
        return
    samples = read_split_folder(split_path)
    print(f"【读取标注完成】总样本数量: {len(samples)}")
    if len(samples) == 0:
        print("【警告】没有读取到任何视频样本，直接退出")
        return
    rows = []
    for idx, (file_path, act, quality) in enumerate(samples):
        vid_path = file_path.replace("\\", "/")
        print(f"[{idx+1}/{len(samples)}] 处理视频: {vid_path}, 动作:{act}, 质量:{quality}")
        if not os.path.exists(vid_path):
            print(f"  跳过：视频文件不存在 {vid_path}")
            continue
        try:
            cap = cv2.VideoCapture(vid_path)
        except Exception as e:
            print(f"  视频打开异常，跳过: {vid_path}, 错误:{e}")
            continue

        frame_cnt = 0
        fail_cnt = 0
        max_fail = 5

        # 修复：提取更多帧（最多30帧），增加时序多样性
        max_frames_to_extract = 30  # 从10增加到30
        frame_interval = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / max_frames_to_extract)) if cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0 else 1

        while cap.isOpened():
            try:
                ret, f = cap.read()
            except Exception as e:
                print(f"  读取帧异常，跳过当前帧，错误:{e}")
                frame_cnt += 1
                fail_cnt += 1
                if fail_cnt >= max_fail:
                    print(f"  连续{max_fail}帧提取失败，放弃该视频")
                    break
                continue
            if not ret:
                break

            # 按间隔采样，覆盖整个视频
            if frame_cnt % frame_interval != 0:
                frame_cnt += 1
                continue
            if frame_cnt // frame_interval >= max_frames_to_extract:
                break

            try:
                feats = extract_full_feature(f)
            except Exception as e:
                print(f"  第{frame_cnt+1}帧骨骼提取崩溃，跳过，错误:{e}")
                frame_cnt += 1
                fail_cnt += 1
                if fail_cnt >= max_fail:
                    print(f"  连续{max_fail}帧提取失败，放弃该视频")
                    break
                continue
            if feats is None:
                frame_cnt += 1
                fail_cnt += 1
                print(f"  第{frame_cnt}帧无有效人体关键点，跳过")
                if fail_cnt >= max_fail:
                    print(f"  连续{max_fail}帧提取失败，放弃该视频")
                    break
                continue
            fail_cnt = 0
            type_feat, quality_feat = feats
            row = type_feat + quality_feat + [act, quality]
            rows.append(row)
            frame_cnt += 1
        cap.release()
        print(f"  该视频有效帧数: {frame_cnt}")
    print(f"【提取结束】总有效特征行数: {len(rows)}")
    if len(rows) == 0:
        print("【警告】无有效特征，不生成CSV")
        return

    # 修复：更新列名，匹配132维特征
    col_names = []
    for i in range(33):
        col_names.extend([f"x{i}", f"y{i}", f"z{i}", f"v{i}"])
    col_names += ["knee_off","waist_diff","hip_amp","body_scale","sport_type","quality"]

    df = pd.DataFrame(rows, columns=col_names)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"✅ 导出完成：{out_csv}，样本数{len(df)}")

if __name__ == "__main__":
    print("===== 批量特征提取工具启动（修复版） =====")
    generate_feature_csv("./dataset/Splitted_full_data/train", "type_train.csv")
    generate_feature_csv("./dataset/Splitted_full_data/test", "type_test.csv")
    generate_feature_csv("./dataset/Splitted_full_data/train", "quality_train.csv")
    generate_feature_csv("./dataset/Splitted_full_data/test", "quality_test.csv")
    print("===== 全部提取任务执行完毕 =====")