# # 全局屏蔽TFLite XNNPACK崩溃代理，必须置顶
# import os
# import sys
# sys.path.append(os.getcwd())

# os.environ["TF_XNNPACK_DELEGATE"] = "0"
# os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
# os.environ["MEDIAPIPE_NUM_THREADS"] = "1"
# os.environ["OMP_NUM_THREADS"] = "1"
# os.environ["MEDIAPIPE_DISABLE_MODEL_DOWNLOAD"] = "1"

# import cv2
# import numpy as np
# from PIL import Image, ImageDraw, ImageFont
# import warnings
# import pymysql
# warnings.filterwarnings("ignore")

# # ========== 配置 ==========
# CONF_THRESHOLD = 0.4
# MODEL_ACC = 0.91


# # ========== 数据库连接 ==========
# def get_db_conn():
#     try:
#         conn = pymysql.connect(
#             host="127.0.0.1",
#             user="root",
#             password="123456",
#             database="ai_db",
#             charset="utf8mb4"
#         )
#         return conn
#     except Exception as e:
#         raise Exception(f"数据库连接失败：{str(e)}")


# # ========== 统一入库函数 ==========
# def insert_record(action_type, count, model_acc, avg_conf, source_type, avg_score, uid=None):
#     conn = None
#     cur = None
#     try:
#         conn = get_db_conn()
#         cur = conn.cursor()
#         uid_val = uid if uid else "test_user"
#         video_name = f"{action_type}_{count}times_{source_type}"
#         sql = """
#             INSERT INTO videos (uid, name, type, count, score, model_accuracy, avg_confidence, createTime)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
#         """
#         cur.execute(sql, (uid_val, video_name, action_type, count, avg_score, model_acc, avg_conf))
#         conn.commit()
#         return cur.lastrowid
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         raise Exception(f"入库失败：{str(e)}")
#     finally:
#         if cur:
#             cur.close()
#         if conn:
#             conn.close()


# # ========== 中文绘制工具 ==========
# # 预定义系统字体完整路径（Windows/Linux/macOS）
# _SYSTEM_FONT_DIRS = [
#     r"C:\Windows\Fonts",           # Windows
#     r"C:\Users\Public\Documents",  # Windows备选
#     "/usr/share/fonts/truetype/",  # Linux
#     "/System/Library/Fonts/",     # macOS
#     "/usr/local/share/fonts/",     # Linux备选
#     os.path.dirname(os.path.abspath(__file__)),  # 当前脚本目录
# ]

# _CN_FONT_CANDIDATES = [
#     "msyh.ttc", "msyhbd.ttc",       # 微软雅黑
#     "simhei.ttf", "simfang.ttf",    # 黑体/仿宋
#     "simsun.ttc", "simsun.ttf",      # 宋体
#     "STHeiti Medium.ttc",           # macOS华文黑体
#     "NotoSansCJK-Regular.ttc",      # Linux Noto
#     "WenQuanYiMicroHei.ttf",       # Linux文泉驿
#     "Arial Unicode.ttf",            # 跨平台Unicode
#     "arial.ttf",                    # 英文兜底
# ]


# def _find_font_file():
#     """在系统字体目录中查找可用的中文字体文件"""
#     for font_name in _CN_FONT_CANDIDATES:
#         # 先按纯文件名在当前目录找
#         if os.path.exists(font_name):
#             return font_name
#         # 再按系统字体目录搜索
#         for font_dir in _SYSTEM_FONT_DIRS:
#             full_path = os.path.join(font_dir, font_name)
#             if os.path.exists(full_path):
#                 return full_path
#     return None


# _FOUND_FONT = None
# _FOUND_FONT_PATH = None


# def _get_font(font_size):
#     global _FOUND_FONT, _FOUND_FONT_PATH
#     if _FOUND_FONT is None:
#         _FOUND_FONT_PATH = _find_font_file()
#         if _FOUND_FONT_PATH:
#             try:
#                 _FOUND_FONT = ImageFont.truetype(_FOUND_FONT_PATH, font_size)
#             except Exception:
#                 _FOUND_FONT = ImageFont.load_default()
#                 _FOUND_FONT_PATH = None
#         else:
#             _FOUND_FONT = ImageFont.load_default()
#     else:
#         # 字体文件找到了但字号不同，重新创建
#         try:
#             _FOUND_FONT = ImageFont.truetype(_FOUND_FONT_PATH, font_size)
#         except Exception:
#             _FOUND_FONT = ImageFont.load_default()
#     return _FOUND_FONT


# def put_cn_text(img, text, pos, font_size, color_bgr):
#     """在cv2图像上绘制中文文字（通过PIL渲染解决cv2不支持中文的问题）"""
#     font = _get_font(font_size)

#     if len(img.shape) != 3:
#         img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
#     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     pil = Image.fromarray(img_rgb)
#     draw = ImageDraw.Draw(pil)
#     draw.text(pos, text, font=font, fill=(color_bgr[2], color_bgr[1], color_bgr[0]))
#     return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


# # ========== Tk文件选择弹窗 ==========
# def select_mp4():
#     import tkinter as tk
#     from tkinter import filedialog
#     root = tk.Tk()
#     root.withdraw()
#     root.attributes("-topmost", True)
#     file_path = filedialog.askopenfilename(
#         title="请选择MP4视频文件",
#         filetypes=[("MP4视频文件", "*.mp4"), ("全部文件", "*.*")]
#     )
#     root.destroy()
#     return file_path if file_path else None


# # ========== 核心视频识别逻辑（弹cv2窗口，和直接运行main.py一样的效果） ==========
# def _do_video_recognize(vid_path, uid=None, output_path=None):
#     """
#     内部核心函数：弹出cv2窗口播放视频并实时标注识别结果。
#     窗口关闭后返回结果dict。
#     """
#     # 兼容两种目录结构
#     try:
#         from pose_detector import ActionCounter
#     except ImportError:
#         from utils.pose_detector import ActionCounter
#     try:
#         from ml_predict import predict_frame, smooth_score
#     except ImportError:
#         from utils.ml_predict import predict_frame, smooth_score
#     try:
#         from score_calc import calc_score
#     except ImportError:
#         from utils.score_calc import calc_score
#     try:
#         from ml_predict import reset_instance_buffers
#     except ImportError:
#         try:
#             from utils.ml_predict import reset_instance_buffers
#         except ImportError:
#             reset_instance_buffers = None

#     if not os.path.exists(vid_path):
#         print(f"错误：视频文件不存在！{vid_path}")
#         return None

#     cap = cv2.VideoCapture(vid_path)
#     if not cap.isOpened():
#         cap.release()
#         cap = cv2.VideoCapture(vid_path)
#         if not cap.isOpened():
#             print("错误：视频最终打开失败")
#             return None

#     w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#     w = w if w > 0 else 1280
#     h = h if h > 0 else 720
#     fps = fps if fps > 0 else 30

#     print(f"视频信息: {w}x{h} @ {fps:.1f}fps, 总帧数: {total_frames}")

#     # ========== 初始化视频写入器（使用imageio生成H.264 MP4，浏览器可直接播放）==========
#     writer = None
#     if output_path is not None:
#         output_dir = os.path.dirname(output_path)
#         if output_dir:
#             os.makedirs(output_dir, exist_ok=True)
#         try:
#             import imageio.v2 as iio
#             writer = iio.get_writer(output_path, fps=fps, codec='libx264', quality=8)
#             print(f"合成视频将保存到: {output_path} (H.264编码，浏览器可播放)")
#         except ImportError:
#             print("错误：未安装imageio！请执行: pip install imageio imageio-ffmpeg --break-system-packages")
#             writer = None
#         except Exception as e:
#             print(f"警告：video writer初始化失败: {e}")
#             writer = None

#     # ========== 初始化 MediaPipe Pose 用于绘制骨架 ==========
#     mp_pose = None
#     mp_drawing = None
#     try:
#         import mediapipe as mp
#         mp_pose = mp.solutions.pose
#         mp_drawing = mp.solutions.drawing_utils
#         pose = mp_pose.Pose(
#             static_image_mode=False,
#             model_complexity=1,
#             smooth_landmarks=True,
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5
#         )
#         print("MediaPipe Pose 骨架检测已初始化")
#     except Exception as e:
#         print(f"警告：MediaPipe Pose初始化失败，将不绘制骨架: {e}")
#         pose = None

#     win = "健身识别-视频窗口"
#     cv2.namedWindow(win, cv2.WINDOW_NORMAL)
#     cv2.resizeWindow(win, min(w, 1280), min(h, 720))

#     if reset_instance_buffers:
#         reset_instance_buffers()
#     counter = ActionCounter(video_fps=fps)
#     conf_list, score_list = [], []
#     final_act = "push-up"
#     final_cnt = 0
#     frame_no = 0
#     process_every_n = max(1, int(fps / 30))

#     try:
#         while cap.isOpened():
#             ret, frame = cap.read()
#             frame_no += 1
#             if not ret:
#                 break
#             if frame_no % process_every_n != 0:
#                 continue
#             try:
#                 pred_result = predict_frame(frame)
#                 if len(pred_result) >= 7:
#                     act, act_conf, good_conf, ko, wd, ha = pred_result[:6]
#                 else:
#                     act, act_conf, good_conf, ko, wd, ha = pred_result

#                 if act_conf < CONF_THRESHOLD:
#                     act = "unknown"

#                 counter_result = counter.update(frame, act, act_conf)
#                 if len(counter_result) >= 8:
#                     cnt, el, kn, fix_act, knee_off, waist_diff, hip_amp = counter_result[:7]
#                 else:
#                     cnt, el, kn, fix_act = counter_result[:4]
#                     knee_off, waist_diff, hip_amp = ko, wd, ha

#                 # 【调试日志】每30帧打印一次关键角度和分类结果，用于排查识别问题
#                 if frame_no % 30 == 0:
#                     print(f"[调试] 帧{frame_no}: 模型预测={act}(conf={act_conf:.2f}) "
#                           f"→ 规则修正={fix_act} | 肘角度={el:.1f} 膝角度={kn:.1f} "
#                           f"计数={cnt} 分数={sc:.1f}")

#                 sc, defects = calc_score(good_conf, knee_off, waist_diff, hip_amp, fix_act)
#                 sc = smooth_score(sc)

#                 if 0 <= act_conf <= 1:
#                     conf_list.append(act_conf)
#                 if 0 <= sc <= 100:
#                     score_list.append(sc)
#                 # 不再用每帧更新final_act/final_cnt，最终结果从counter中取计数最高的动作
#             except Exception as frame_err:
#                 print(f"跳过异常帧 {frame_no}：{frame_err}")
#                 sc = 0.0
#                 fix_act = final_act if final_act else "push-up"
#                 cnt = final_cnt
#                 defects = []
#                 knee_off, waist_diff, hip_amp = 0.0, 0.0, 0.0

#             # ========== 绘制骨架关键点 ==========
#             if pose:
#                 try:
#                     rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                     results = pose.process(rgb_frame)
#                     if results.pose_landmarks:
#                         # 绘制骨架连线（绿色）和关键点（红色圆点）
#                         mp_drawing.draw_landmarks(
#                             frame,
#                             results.pose_landmarks,
#                             mp_pose.POSE_CONNECTIONS,
#                             mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
#                             mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=3)
#                         )
#                 except Exception as draw_err:
#                     if frame_no % 60 == 0:
#                         print(f"骨架绘制异常(帧{frame_no}): {draw_err}")

#             cv2.putText(frame, f"Action: {fix_act}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
#             cv2.putText(frame, f"Count: {cnt}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
#             cv2.putText(frame, f"Score: {sc}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 0), 2)
#             cv2.putText(frame, f"Conf: {act_conf:.2f}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

#             y_pos = 50
#             for defect in defects[:2]:
#                 frame = put_cn_text(frame, f"Defect: {defect}", (w - 350, y_pos), 20, (0, 0, 255))
#                 y_pos += 35

#             # 将标注后的帧写入合成视频（BGR转RGB，避免色差）
#             if writer:
#                 try:
#                     writer.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#                 except Exception:
#                     pass

#             cv2.imshow(win, frame)
#             key = cv2.waitKey(1) & 0xFF
#             if key == ord("q"):
#                 print("用户手动退出")
#                 break
#             if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
#                 print("窗口已关闭，退出")
#                 break
#     except Exception as loop_err:
#         print(f"视频循环运行异常：{loop_err}")
#     finally:
#         cap.release()
#         cv2.destroyAllWindows()
#         # 关闭imageio writer，完成H.264 MP4文件写入
#         if writer:
#             try:
#                 writer.close()
#                 print(f"合成视频已保存: {output_path}")
#             except Exception as e:
#                 print(f"关闭视频写入器异常: {e}")
#         # 释放MediaPipe Pose资源
#         if pose:
#             try:
#                 pose.close()
#             except Exception:
#                 pass

#     avg_conf = round(np.mean(conf_list), 2) if conf_list else 0.0
#     avg_sc = round(np.mean(score_list), 1) if score_list else 0.0

#     # 【修复核心】最终结果取计数最高的动作类型（而非最后一帧）
#     # 最后一帧人可能站直了，锁定类型是push-up，但实际做的是squat且计数到5
#     final_act = max(counter.count_dict, key=counter.count_dict.get)
#     final_cnt = counter.count_dict[final_act]

#     print(f"识别结果: 动作={final_act}, 次数={final_cnt}, 平均置信度={avg_conf}, 平均分数={avg_sc}")

#     return {
#         "action_type": final_act,
#         "repeat_count": final_cnt,
#         "avg_confidence": avg_conf,
#         "avg_score": avg_sc,
#         "total_frames": frame_no,
#         "fps": fps,
#         "output_path": output_path
#     }


# # ========== 供本地控制台直接运行 ==========
# def run_video(vid_path, uid=None):
#     """
#     本地MP4视频识别 —— 弹出cv2 GUI窗口显示识别过程。
#     识别完后自动入库并打印结果（和原来main.py完全一样的行为）。
#     """
#     result = _do_video_recognize(vid_path, uid)
#     if result is None:
#         return
#     try:
#         video_id = insert_record(
#             result["action_type"], result["repeat_count"],
#             MODEL_ACC, result["avg_confidence"], "local_video",
#             result["avg_score"], uid
#         )
#         print(f"视频数据入库成功，记录ID：{video_id}")
#     except Exception as db_err:
#         print(f"数据库入库失败：{db_err}")


# # ========== 【新增】供app.py调用：弹cv2窗口，返回结果dict ==========
# def run_video_return(vid_path, uid=None, output_path=None):
#     """
#     供Flask的app.py调用 —— 弹出cv2窗口播放视频并实时标注（和直接运行main.py完全一样的效果）。
#     同时将带标注的合成视频保存到output_path（upload_temp/）。
#     cv2窗口关闭后返回识别结果dict（不入库，由app.py负责入库）。
#     """
#     return _do_video_recognize(vid_path, uid, output_path=output_path)


# # ========== 摄像头识别 ==========
# def _do_camera_recognize(uid=None):
#     """内部核心函数：弹出cv2摄像头窗口，实时标注。关闭后返回结果dict。"""
#     try:
#         from pose_detector import ActionCounter
#     except ImportError:
#         from utils.pose_detector import ActionCounter
#     try:
#         from ml_predict import predict_frame, smooth_score
#     except ImportError:
#         from utils.ml_predict import predict_frame, smooth_score
#     try:
#         from score_calc import calc_score
#     except ImportError:
#         from utils.score_calc import calc_score
#     try:
#         from ml_predict import reset_instance_buffers
#     except ImportError:
#         try:
#             from utils.ml_predict import reset_instance_buffers
#         except ImportError:
#             reset_instance_buffers = None

#     cap = cv2.VideoCapture(0)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
#     cap.set(cv2.CAP_PROP_FPS, 30)
#     cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

#     if not cap.isOpened():
#         cap.release()
#         cap = cv2.VideoCapture(1)
#         if not cap.isOpened():
#             print("错误：所有摄像头设备打开失败")
#             return None

#     w, h = 1280, 720
#     win = "健身识别-摄像头实时"
#     cv2.namedWindow(win, cv2.WINDOW_NORMAL)
#     cv2.resizeWindow(win, w, h)

#     if reset_instance_buffers:
#         reset_instance_buffers()
#     counter = ActionCounter(video_fps=30)
#     conf_list, score_list = [], []
#     final_act = "push-up"
#     final_cnt = 0
#     print("摄像头已启动，按Q键关闭窗口")

#     try:
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 continue
#             frame = cv2.flip(frame, 1)
#             try:
#                 pred_result = predict_frame(frame)
#                 if len(pred_result) >= 7:
#                     act, act_conf, good_conf, ko, wd, ha = pred_result[:6]
#                 else:
#                     act, act_conf, good_conf, ko, wd, ha = pred_result

#                 if act_conf < CONF_THRESHOLD:
#                     act = "unknown"

#                 counter_result = counter.update(frame, act, act_conf)
#                 if len(counter_result) >= 8:
#                     cnt, el, kn, fix_act, knee_off, waist_diff, hip_amp = counter_result[:7]
#                 else:
#                     cnt, el, kn, fix_act = counter_result[:4]
#                     knee_off, waist_diff, hip_amp = ko, wd, ha

#                 sc, defects = calc_score(good_conf, knee_off, waist_diff, hip_amp, fix_act)
#                 sc = smooth_score(sc)

#                 if 0 <= act_conf <= 1:
#                     conf_list.append(act_conf)
#                 if 0 <= sc <= 100:
#                     score_list.append(sc)
#                 final_cnt, final_act = cnt, fix_act
#             except Exception as frame_err:
#                 print(f"跳过异常帧：{frame_err}")
#                 sc = 0.0
#                 fix_act = final_act if final_act else "push-up"
#                 cnt = final_cnt
#                 defects = []

#             frame = put_cn_text(frame, f"动作类型:{fix_act}", (20, 40), 26, (0, 255, 0))
#             frame = put_cn_text(frame, f"完成次数:{cnt}", (20, 85), 26, (0, 0, 255))
#             frame = put_cn_text(frame, f"动作分数:{sc}", (w-350, 40), 26, (0, 220, 0))
#             frame = put_cn_text(frame, f"置信度:{act_conf:.2f}", (w-350, 80), 22, (255, 200, 0))

#             y_pos = 130
#             for defect in defects[:2]:
#                 frame = put_cn_text(frame, f"动作缺陷:{defect}", (w-350, y_pos), 20, (0, 0, 255))
#                 y_pos += 35

#             cv2.imshow(win, frame)
#             key = cv2.waitKey(1) & 0xFF
#             if key == ord("q"):
#                 print("用户手动退出摄像头")
#                 break
#             if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
#                 print("摄像头窗口已关闭")
#                 break
#     except Exception as loop_err:
#         print(f"摄像头运行异常：{loop_err}")
#     finally:
#         cap.release()
#         cv2.destroyAllWindows()

#     avg_conf = round(np.mean(conf_list), 2) if conf_list else 0.0
#     avg_sc = round(np.mean(score_list), 1) if score_list else 0.0
#     return {
#         "action_type": final_act,
#         "repeat_count": final_cnt,
#         "avg_confidence": avg_conf,
#         "avg_score": avg_sc
#     }


# def run_camera(uid=None):
#     """供本地控制台直接运行 —— 弹出摄像头窗口，识别完后自动入库"""
#     result = _do_camera_recognize(uid)
#     if result is None:
#         return
#     try:
#         video_id = insert_record(
#             result["action_type"], result["repeat_count"],
#             MODEL_ACC, result["avg_confidence"], "camera_realtime",
#             result["avg_score"], uid
#         )
#         print(f"摄像头记录入库成功，记录ID：{video_id}")
#     except Exception as db_err:
#         print(f"数据库入库失败：{db_err}")


# def run_camera_return(uid=None):
#     """【新增】供app.py调用 —— 弹出摄像头窗口，关闭后返回结果dict"""
#     return _do_camera_recognize(uid)


# # ========== 控制台入口 ==========
# if __name__ == "__main__":
#     print("========== AI健身动作识别系统（控制台本地运行版） ==========")
#     print("1 - 本地MP4视频识别（弹出文件选择窗口）")
#     print("2 - 摄像头实时动作识别")
#     print("=================================================")
#     try:
#         uid = input("请输入用户ID（留空则用测试ID）：").strip() or None
#         user_opt = input("请输入数字选择功能：").strip()
#         if user_opt == "1":
#             print("正在打开文件选择弹窗，请选择视频...")
#             video_path = select_mp4()
#             if video_path:
#                 print(f"已选中视频：{video_path}")
#                 run_video(video_path, uid)
#             else:
#                 print("未选择任何视频文件，程序退出")
#         elif user_opt == "2":
#             run_camera(uid)
#         else:
#             print("输入无效，请重新运行程序输入1或2")
#     except KeyboardInterrupt:
#         print("\n程序被用户中断")
#     except Exception as e:
#         print(f"程序运行异常：{e}")
#     finally:
#         cv2.destroyAllWindows()






# 全局屏蔽TFLite XNNPACK崩溃代理，必须置顶
import os
import sys
sys.path.append(os.getcwd())

os.environ["TF_XNNPACK_DELEGATE"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
os.environ["MEDIAPIPE_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MEDIAPIPE_DISABLE_MODEL_DOWNLOAD"] = "1"

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import warnings
import pymysql
warnings.filterwarnings("ignore")

# ========== 配置 ==========
CONF_THRESHOLD = 0.4
MODEL_ACC = 0.91


# ========== 数据库连接 ==========
def get_db_conn():
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="123456",
            database="ai_db",
            charset="utf8mb4"
        )
        return conn
    except Exception as e:
        raise Exception(f"数据库连接失败：{str(e)}")


# ========== 统一入库函数 ==========
def insert_record(action_type, count, model_acc, avg_conf, source_type, avg_score, uid=None):
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        uid_val = uid if uid else "test_user"
        video_name = f"{action_type}_{count}times_{source_type}"
        sql = """
            INSERT INTO videos (uid, name, type, count, score, model_accuracy, avg_confidence, createTime)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        cur.execute(sql, (uid_val, video_name, action_type, count, avg_score, model_acc, avg_conf))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"入库失败：{str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ========== 中文绘制工具 ==========
# 预定义系统字体完整路径（Windows/Linux/macOS）
_SYSTEM_FONT_DIRS = [
    r"C:\Windows\Fonts",           # Windows
    r"C:\Users\Public\Documents",  # Windows备选
    "/usr/share/fonts/truetype/",  # Linux
    "/System/Library/Fonts/",     # macOS
    "/usr/local/share/fonts/",     # Linux备选
    os.path.dirname(os.path.abspath(__file__)),  # 当前脚本目录
]

_CN_FONT_CANDIDATES = [
    "msyh.ttc", "msyhbd.ttc",       # 微软雅黑
    "simhei.ttf", "simfang.ttf",    # 黑体/仿宋
    "simsun.ttc", "simsun.ttf",      # 宋体
    "STHeiti Medium.ttc",           # macOS华文黑体
    "NotoSansCJK-Regular.ttc",      # Linux Noto
    "WenQuanYiMicroHei.ttf",       # Linux文泉驿
    "Arial Unicode.ttf",            # 跨平台Unicode
    "arial.ttf",                    # 英文兜底
]


def _find_font_file():
    """在系统字体目录中查找可用的中文字体文件"""
    for font_name in _CN_FONT_CANDIDATES:
        # 先按纯文件名在当前目录找
        if os.path.exists(font_name):
            return font_name
        # 再按系统字体目录搜索
        for font_dir in _SYSTEM_FONT_DIRS:
            full_path = os.path.join(font_dir, font_name)
            if os.path.exists(full_path):
                return full_path
    return None


_FOUND_FONT = None
_FOUND_FONT_PATH = None


def _get_font(font_size):
    global _FOUND_FONT, _FOUND_FONT_PATH
    if _FOUND_FONT is None:
        _FOUND_FONT_PATH = _find_font_file()
        if _FOUND_FONT_PATH:
            try:
                _FOUND_FONT = ImageFont.truetype(_FOUND_FONT_PATH, font_size)
            except Exception:
                _FOUND_FONT = ImageFont.load_default()
                _FOUND_FONT_PATH = None
        else:
            _FOUND_FONT = ImageFont.load_default()
    else:
        # 字体文件找到了但字号不同，重新创建
        try:
            _FOUND_FONT = ImageFont.truetype(_FOUND_FONT_PATH, font_size)
        except Exception:
            _FOUND_FONT = ImageFont.load_default()
    return _FOUND_FONT


def put_cn_text(img, text, pos, font_size, color_bgr):
    """在cv2图像上绘制中文文字（通过PIL渲染解决cv2不支持中文的问题）"""
    font = _get_font(font_size)

    if len(img.shape) != 3:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil)
    draw.text(pos, text, font=font, fill=(color_bgr[2], color_bgr[1], color_bgr[0]))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


# ========== Tk文件选择弹窗 ==========
def select_mp4():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="请选择MP4视频文件",
        filetypes=[("MP4视频文件", "*.mp4"), ("全部文件", "*.*")]
    )
    root.destroy()
    return file_path if file_path else None


# ========== 核心视频识别逻辑（弹cv2窗口，和直接运行main.py一样的效果） ==========
def _do_video_recognize(vid_path, uid=None, output_path=None):
    """
    内部核心函数：弹出cv2窗口播放视频并实时标注识别结果。
    窗口关闭后返回结果dict。
    """
    # 兼容两种目录结构
    try:
        from pose_detector import ActionCounter
    except ImportError:
        from utils.pose_detector import ActionCounter
    try:
        from ml_predict import predict_frame, smooth_score
    except ImportError:
        from utils.ml_predict import predict_frame, smooth_score
    try:
        from score_calc import calc_score
    except ImportError:
        from utils.score_calc import calc_score
    try:
        from ml_predict import reset_instance_buffers
    except ImportError:
        try:
            from utils.ml_predict import reset_instance_buffers
        except ImportError:
            reset_instance_buffers = None

    if not os.path.exists(vid_path):
        print(f"错误：视频文件不存在！{vid_path}")
        return None

    cap = cv2.VideoCapture(vid_path)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(vid_path)
        if not cap.isOpened():
            print("错误：视频最终打开失败")
            return None

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = w if w > 0 else 1280
    h = h if h > 0 else 720
    fps = fps if fps > 0 else 30

    print(f"视频信息: {w}x{h} @ {fps:.1f}fps, 总帧数: {total_frames}")

    # ========== 初始化视频写入器（使用imageio生成H.264 MP4，浏览器可直接播放）==========
    writer = None
    if output_path is not None:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        try:
            import imageio.v2 as iio
            writer = iio.get_writer(output_path, fps=fps, codec='libx264', quality=8)
            print(f"合成视频将保存到: {output_path} (H.264编码，浏览器可播放)")
        except ImportError:
            print("错误：未安装imageio！请执行: pip install imageio imageio-ffmpeg --break-system-packages")
            writer = None
        except Exception as e:
            print(f"警告：video writer初始化失败: {e}")
            writer = None

    # ========== 初始化 MediaPipe Pose 用于绘制骨架 ==========
    mp_pose = None
    mp_drawing = None
    try:
        import mediapipe as mp
        mp_pose = mp.solutions.pose
        mp_drawing = mp.solutions.drawing_utils
        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("MediaPipe Pose 骨架检测已初始化")
    except Exception as e:
        print(f"警告：MediaPipe Pose初始化失败，将不绘制骨架: {e}")
        pose = None

    win = "健身识别-视频窗口"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, min(w, 1280), min(h, 720))

    if reset_instance_buffers:
        reset_instance_buffers()
    counter = ActionCounter(video_fps=fps)
    conf_list, score_list = [], []
    final_act = ""
    final_cnt = 0
    frame_no = 0
    process_every_n = max(1, int(fps / 30))

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            frame_no += 1
            if not ret:
                break
            if frame_no % process_every_n != 0:
                continue
            try:
                # ========== 先检测骨架，判断画面中是否有人 ==========
                person_detected = True  # 默认有人
                if pose:
                    try:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pose_results = pose.process(rgb_frame)
                        if pose_results.pose_landmarks:
                            # 有人：绘制骨架连线（绿色）和关键点（红色圆点）
                            mp_drawing.draw_landmarks(
                                frame,
                                pose_results.pose_landmarks,
                                mp_pose.POSE_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=3)
                            )
                        else:
                            person_detected = False
                    except Exception:
                        person_detected = False

                if not person_detected:
                    # 无人：保持上一个有效动作标签，计数不更新，分数为0
                    fix_act = final_act if final_act else "none"
                    cnt = final_cnt
                    sc = 0.0
                    act_conf = 0.0
                    defects = ["No person detected"]
                else:
                    # 有人：正常执行动作识别和计数
                    pred_result = predict_frame(frame)
                    if len(pred_result) >= 7:
                        act, act_conf, good_conf, ko, wd, ha = pred_result[:6]
                    else:
                        act, act_conf, good_conf, ko, wd, ha = pred_result

                    if act_conf < CONF_THRESHOLD:
                        act = "unknown"

                    counter_result = counter.update(frame, act, act_conf)
                    if len(counter_result) >= 8:
                        cnt, el, kn, fix_act, knee_off, waist_diff, hip_amp = counter_result[:7]
                    else:
                        cnt, el, kn, fix_act = counter_result[:4]
                        knee_off, waist_diff, hip_amp = ko, wd, ha

                    # 【调试日志】每30帧打印一次
                    if frame_no % 30 == 0:
                        print(f"[调试] 帧{frame_no}: 模型预测={act}(conf={act_conf:.2f}) "
                              f"→ 规则修正={fix_act} | 肘角度={el:.1f} 膝角度={kn:.1f} "
                              f"计数={cnt} 分数={sc:.1f}")

                    sc, defects = calc_score(good_conf, knee_off, waist_diff, hip_amp, fix_act)
                    sc = smooth_score(sc)

                if 0 <= act_conf <= 1:
                    conf_list.append(act_conf)
                if 0 <= sc <= 100:
                    score_list.append(sc)
            except Exception as frame_err:
                print(f"跳过异常帧 {frame_no}：{frame_err}")
                sc = 0.0
                fix_act = final_act if final_act else "none"
                cnt = final_cnt
                defects = []
                knee_off, waist_diff, hip_amp = 0.0, 0.0, 0.0

            cv2.putText(frame, f"Action: {fix_act}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.putText(frame, f"Count: {cnt}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            cv2.putText(frame, f"Score: {sc}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 0), 2)
            cv2.putText(frame, f"Conf: {act_conf:.2f}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

            y_pos = 50
            for defect in defects[:2]:
                frame = put_cn_text(frame, f"Defect: {defect}", (w - 350, y_pos), 20, (0, 0, 255))
                y_pos += 35

            # 将标注后的帧写入合成视频（BGR转RGB，避免色差）
            if writer:
                try:
                    writer.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                except Exception:
                    pass

            cv2.imshow(win, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("用户手动退出")
                break
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                print("窗口已关闭，退出")
                break
    except Exception as loop_err:
        print(f"视频循环运行异常：{loop_err}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        # 关闭imageio writer，完成H.264 MP4文件写入
        if writer:
            try:
                writer.close()
                print(f"合成视频已保存: {output_path}")
            except Exception as e:
                print(f"关闭视频写入器异常: {e}")
        # 释放MediaPipe Pose资源
        if pose:
            try:
                pose.close()
            except Exception:
                pass

    avg_conf = round(np.mean(conf_list), 2) if conf_list else 0.0
    avg_sc = round(np.mean(score_list), 1) if score_list else 0.0

    # 最终结果取计数最高的动作类型
    # 如果全程无人（counter无有效计数），返回 "none"
    if counter.count_dict and max(counter.count_dict.values()) > 0:
        final_act = max(counter.count_dict, key=counter.count_dict.get)
        final_cnt = counter.count_dict[final_act]
    else:
        final_act = "none"
        final_cnt = 0

    print(f"识别结果: 动作={final_act}, 次数={final_cnt}, 平均置信度={avg_conf}, 平均分数={avg_sc}")

    return {
        "action_type": final_act,
        "repeat_count": final_cnt,
        "avg_confidence": avg_conf,
        "avg_score": avg_sc,
        "total_frames": frame_no,
        "fps": fps,
        "output_path": output_path
    }


# ========== 供本地控制台直接运行 ==========
def run_video(vid_path, uid=None):
    """
    本地MP4视频识别 —— 弹出cv2 GUI窗口显示识别过程。
    识别完后自动入库并打印结果（和原来main.py完全一样的行为）。
    """
    result = _do_video_recognize(vid_path, uid)
    if result is None:
        return
    try:
        video_id = insert_record(
            result["action_type"], result["repeat_count"],
            MODEL_ACC, result["avg_confidence"], "local_video",
            result["avg_score"], uid
        )
        print(f"视频数据入库成功，记录ID：{video_id}")
    except Exception as db_err:
        print(f"数据库入库失败：{db_err}")


# ========== 【新增】供app.py调用：弹cv2窗口，返回结果dict ==========
def run_video_return(vid_path, uid=None, output_path=None):
    """
    供Flask的app.py调用 —— 弹出cv2窗口播放视频并实时标注（和直接运行main.py完全一样的效果）。
    同时将带标注的合成视频保存到output_path（upload_temp/）。
    cv2窗口关闭后返回识别结果dict（不入库，由app.py负责入库）。
    """
    return _do_video_recognize(vid_path, uid, output_path=output_path)


# ========== 摄像头识别 ==========
def _do_camera_recognize(uid=None):
    """内部核心函数：弹出cv2摄像头窗口，实时标注。关闭后返回结果dict。"""
    try:
        from pose_detector import ActionCounter
    except ImportError:
        from utils.pose_detector import ActionCounter
    try:
        from ml_predict import predict_frame, smooth_score
    except ImportError:
        from utils.ml_predict import predict_frame, smooth_score
    try:
        from score_calc import calc_score
    except ImportError:
        from utils.score_calc import calc_score
    try:
        from ml_predict import reset_instance_buffers
    except ImportError:
        try:
            from utils.ml_predict import reset_instance_buffers
        except ImportError:
            reset_instance_buffers = None

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("错误：所有摄像头设备打开失败")
            return None

    w, h = 1280, 720
    win = "健身识别-摄像头实时"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, w, h)

    if reset_instance_buffers:
        reset_instance_buffers()
    counter = ActionCounter(video_fps=30)
    conf_list, score_list = [], []
    final_act = "push-up"
    final_cnt = 0
    print("摄像头已启动，按Q键关闭窗口")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            try:
                pred_result = predict_frame(frame)
                if len(pred_result) >= 7:
                    act, act_conf, good_conf, ko, wd, ha = pred_result[:6]
                else:
                    act, act_conf, good_conf, ko, wd, ha = pred_result

                if act_conf < CONF_THRESHOLD:
                    act = "unknown"

                counter_result = counter.update(frame, act, act_conf)
                if len(counter_result) >= 8:
                    cnt, el, kn, fix_act, knee_off, waist_diff, hip_amp = counter_result[:7]
                else:
                    cnt, el, kn, fix_act = counter_result[:4]
                    knee_off, waist_diff, hip_amp = ko, wd, ha

                sc, defects = calc_score(good_conf, knee_off, waist_diff, hip_amp, fix_act)
                sc = smooth_score(sc)

                if 0 <= act_conf <= 1:
                    conf_list.append(act_conf)
                if 0 <= sc <= 100:
                    score_list.append(sc)
                final_cnt, final_act = cnt, fix_act
            except Exception as frame_err:
                print(f"跳过异常帧：{frame_err}")
                sc = 0.0
                fix_act = final_act if final_act else "none"
                cnt = final_cnt
                defects = []

            frame = put_cn_text(frame, f"动作类型:{fix_act}", (20, 40), 26, (0, 255, 0))
            frame = put_cn_text(frame, f"完成次数:{cnt}", (20, 85), 26, (0, 0, 255))
            frame = put_cn_text(frame, f"动作分数:{sc}", (w-350, 40), 26, (0, 220, 0))
            frame = put_cn_text(frame, f"置信度:{act_conf:.2f}", (w-350, 80), 22, (255, 200, 0))

            y_pos = 130
            for defect in defects[:2]:
                frame = put_cn_text(frame, f"动作缺陷:{defect}", (w-350, y_pos), 20, (0, 0, 255))
                y_pos += 35

            cv2.imshow(win, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("用户手动退出摄像头")
                break
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                print("摄像头窗口已关闭")
                break
    except Exception as loop_err:
        print(f"摄像头运行异常：{loop_err}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    avg_conf = round(np.mean(conf_list), 2) if conf_list else 0.0
    avg_sc = round(np.mean(score_list), 1) if score_list else 0.0
    return {
        "action_type": final_act,
        "repeat_count": final_cnt,
        "avg_confidence": avg_conf,
        "avg_score": avg_sc
    }


def run_camera(uid=None):
    """供本地控制台直接运行 —— 弹出摄像头窗口，识别完后自动入库"""
    result = _do_camera_recognize(uid)
    if result is None:
        return
    try:
        video_id = insert_record(
            result["action_type"], result["repeat_count"],
            MODEL_ACC, result["avg_confidence"], "camera_realtime",
            result["avg_score"], uid
        )
        print(f"摄像头记录入库成功，记录ID：{video_id}")
    except Exception as db_err:
        print(f"数据库入库失败：{db_err}")


def run_camera_return(uid=None):
    """【新增】供app.py调用 —— 弹出摄像头窗口，关闭后返回结果dict"""
    return _do_camera_recognize(uid)


# ========== 控制台入口 ==========
if __name__ == "__main__":
    print("========== AI健身动作识别系统（控制台本地运行版） ==========")
    print("1 - 本地MP4视频识别（弹出文件选择窗口）")
    print("2 - 摄像头实时动作识别")
    print("=================================================")
    try:
        uid = input("请输入用户ID（留空则用测试ID）：").strip() or None
        user_opt = input("请输入数字选择功能：").strip()
        if user_opt == "1":
            print("正在打开文件选择弹窗，请选择视频...")
            video_path = select_mp4()
            if video_path:
                print(f"已选中视频：{video_path}")
                run_video(video_path, uid)
            else:
                print("未选择任何视频文件，程序退出")
        elif user_opt == "2":
            run_camera(uid)
        else:
            print("输入无效，请重新运行程序输入1或2")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行异常：{e}")
    finally:
        cv2.destroyAllWindows()

