import os
import sys
import warnings
import uuid
import time
import threading
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import pymysql

warnings.filterwarnings("ignore")

# ========== 环境变量（屏蔽XNNPACK/GPU崩溃）==========
os.environ["TF_XNNPACK_DELEGATE"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
os.environ["MEDIAPIPE_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"
sys.path.insert(0, os.getcwd())

app = Flask(__name__)
token_store = {}

# ====================== 异步任务管理 ======================
# 存储正在进行的识别任务状态，key=task_id
_task_status = {}
# task结构: {"status": "processing"/"done"/"error", "result": {...}, "msg": "..."}


# ====================== 跨域配置 ======================
CORS(
    app,
    resources={r"/api/*": {
        "origins": "*",
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"]
    }}
)


@app.route('/api/<path:path>', methods=["OPTIONS"])
def handle_options(path):
    return jsonify({"code": 200, "msg": "ok"}), 200


@app.after_request
def add_cors_headers(response):
    request_origin = request.headers.get('Origin', '')
    response.headers['Access-Control-Allow-Origin'] = request_origin if request_origin else '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PUT,DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


# ====================== 数据库连接 ======================
def get_db_conn():
    max_retry = 3
    retry_count = 0
    while retry_count < max_retry:
        try:
            conn = pymysql.connect(
                host="127.0.0.1",
                user="root",
                password="123456",
                database="ai_db",
                charset="utf8mb4",
                connect_timeout=5,
                autocommit=False
            )
            return conn
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retry:
                raise Exception(f"数据库连接失败（重试{max_retry}次）：{str(e)}")
            time.sleep(1)


# ====================== Token验证装饰器 ======================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"code": 401, "msg": "缺少token，请重新登录"}), 401
        if token.startswith("Bearer "):
            token = token[7:]
        if token not in token_store:
            return jsonify({"code": 401, "msg": "token无效，请重新登录"}), 401
        token_info = token_store[token]
        if time.time() > token_info["expire"]:
            del token_store[token]
            return jsonify({"code": 401, "msg": "token过期，请重新登录"}), 401
        request.user_info = token_info
        return f(*args, **kwargs)
    return decorated


# ====================== 后台识别线程函数 ======================
def _bg_run_video(task_id, video_path, uid):
    """
    【核心】在后台线程中运行main.py的run_video()。
    这会在后端电脑上弹出cv2窗口，实时显示识别标注（和直接运行main.py一样的效果）。
    窗口关闭后，run_video()返回识别结果，写入数据库，更新任务状态。
    """
    try:
        from main import run_video_return
    except ImportError:
        try:
            # 兼容不同目录结构
            import importlib
            main_mod = importlib.import_module("main")
            run_video_return = main_mod.run_video_return
        except Exception as e:
            _task_status[task_id] = {
                "status": "error",
                "msg": f"main.py模块加载失败: {str(e)}"
            }
            return

    try:
        # 确定合成视频输出路径（保存到 upload_temp）
        output_dir = "./upload_temp"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"result_{os.path.basename(video_path)}"
        output_path = os.path.join(output_dir, output_filename)

        # 调用run_video_return —— 弹出cv2窗口，同时保存合成视频
        result = run_video_return(video_path, uid, output_path=output_path)

        if result is None:
            _task_status[task_id] = {
                "status": "error",
                "msg": "视频处理失败，可能视频无法打开"
            }
            return

        # 写入数据库
        video_id = _insert_video_record(
            uid=uid,
            action_type=result["action_type"],
            count=result["repeat_count"],
            avg_score=result["avg_score"],
            avg_conf=result["avg_confidence"],
            source_name="web_video",
            video_filename=os.path.basename(video_path),
            output_video=output_filename,
            original_video=os.path.basename(video_path)
        )
        result["video_id"] = video_id
        result["output_video"] = output_filename
        result["original_video"] = os.path.basename(video_path)

        _task_status[task_id] = {
            "status": "done",
            "result": result,
            "msg": "识别完成"
        }
    except Exception as e:
        _task_status[task_id] = {
            "status": "error",
            "msg": f"识别过程异常: {str(e)}"
        }
    finally:
        # 不删除文件，原视频和合成视频都保留在 upload_temp/
        pass


def _insert_video_record(uid, action_type, count, avg_score, avg_conf, source_name, video_filename, output_video=None, original_video=None):
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        video_name = f"{action_type}_{count}times_{source_name}"
        sql = """
            INSERT INTO videos (uid, name, type, count, score, model_accuracy, avg_confidence, createTime)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        cur.execute(sql, (uid, video_name, action_type, count, avg_score, 0.91, avg_conf))
        conn.commit()
        vid = cur.lastrowid
        # 尝试更新视频文件名字段（如果表中有这些字段）
        if output_video or original_video:
            try:
                cur.execute("UPDATE videos SET original_video=%s, output_video=%s WHERE id=%s",
                            (original_video or "", output_video or "", vid))
                conn.commit()
            except Exception:
                pass
        return vid
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"入库失败：{e}")
        return 0
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ====================== 登录接口 ======================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "uid" not in data or "password" not in data or "role" not in data:
        return jsonify({"code": 400, "msg": "账号、密码、身份不能为空"}), 400
    uid = data["uid"]
    pwd = data["password"]
    req_role = data["role"]
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        # 第一步：先查学号是否存在
        if req_role == "student":
            cur.execute("SELECT id,uid,name,password FROM students WHERE uid=%s", (uid,))
        elif req_role == "teacher":
            cur.execute("SELECT id,uid,name,password FROM teacher WHERE uid=%s", (uid,))
        else:
            return jsonify({"code": 400, "msg": "身份只能是student/teacher"}), 400

        row = cur.fetchone()
        if not row:
            return jsonify({"code": 401, "msg": "账号不存在，请检查学号是否正确"})

        # 第二步：账号存在，校验密码
        if row[3] != pwd:
            return jsonify({"code": 402, "msg": "密码错误，请重新输入"})

        # 第三步：密码正确，生成token
        role_str = "student" if req_role == "student" else "teacher"
        token = str(uuid.uuid4())
        token_store[token] = {
            "uid": row[1], "name": row[2], "role": role_str,
            "expire": time.time() + 3600
        }
        return jsonify({
            "code": 200, "msg": "登录成功",
            "data": {"uid": row[1], "name": row[2], "type": role_str, "token": token}
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"数据库异常：{str(e)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ====================== 核心：前端上传视频 → 后端弹cv2窗口识别 ======================
@app.route("/api/upload_video_analyze", methods=["POST"])
@token_required
def upload_video_analyze():
    """
    前端点击上传MP4 → Flask保存视频 → 启动后台线程 → 后端弹出cv2窗口
    → 窗口中实时显示识别标注（和直接运行main.py一样的效果）
    → 用户关闭cv2窗口后 → 结果写入数据库 → 前端通过task_id轮询获取结果
    """
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生可上传视频"}), 403

    uid = request.user_info["uid"]

    if "video_file" not in request.files:
        return jsonify({"code": 400, "msg": "未检测到上传的视频文件"}), 400

    video_file = request.files["video_file"]
    if not video_file.filename:
        return jsonify({"code": 400, "msg": "视频文件名为空"}), 400

    # 保存原视频到 upload_temp 目录（使用纯ASCII文件名避免中文编码问题）
    temp_dir = "./uploads"
    os.makedirs(temp_dir, exist_ok=True)
    # 提取原始扩展名，文件名用 uuid 保证唯一且纯ASCII
    _ext = os.path.splitext(video_file.filename)[1] or ".mp4"
    safe_filename = f"{uid}_{uuid.uuid4()}{_ext}"
    temp_save_path = os.path.join(temp_dir, safe_filename)
    try:
        video_file.save(temp_save_path)
        print(f"原视频已保存: {temp_save_path}")
    except Exception as e:
        return jsonify({"code": 500, "msg": f"文件保存失败: {e}"}), 500

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 启动后台线程 —— 在后端电脑弹出cv2窗口进行识别
    _task_status[task_id] = {"status": "processing", "msg": "正在后端弹出识别窗口..."}
    thread = threading.Thread(
        target=_bg_run_video,
        args=(task_id, temp_save_path, uid),
        daemon=True
    )
    thread.start()

    return jsonify({
        "code": 200,
        "msg": "视频已提交，后端正在弹出识别窗口，请查看后端电脑",
        "data": {
            "task_id": task_id,
            "video_name": video_file.filename
        }
    })


# ====================== 轮询识别状态 ======================
@app.route("/api/task_status/<task_id>", methods=["GET"])
@token_required
def get_task_status(task_id):
    """
    前端通过task_id轮询识别状态。
    返回: {"status": "processing"/"done"/"error", "result": {...}}
    """
    task = _task_status.get(task_id)
    if task is None:
        return jsonify({"code": 404, "msg": "任务不存在"}), 404

    if task["status"] == "processing":
        return jsonify({"code": 200, "data": {"status": "processing", "msg": task.get("msg", "识别中...")}})
    elif task["status"] == "done":
        return jsonify({"code": 200, "data": {"status": "done", "result": task.get("result", {})}})
    else:
        return jsonify({"code": 200, "data": {"status": "error", "msg": task.get("msg", "未知错误")}})


# ====================== 视频文件服务接口 ======================
@app.route("/api/video/file/<filename>", methods=["GET"])
def serve_video_file(filename):
    """提供视频文件的HTTP访问（原视频从uploads/，合成视频从upload_temp/）"""
    if ".." in filename or "/" in filename:
        return jsonify({"code": 400, "msg": "非法文件名"}), 400
    # 先查 upload_temp（合成视频）
    temp_path = os.path.join("./upload_temp", filename)
    if os.path.exists(temp_path):
        from flask import send_file
        return send_file(temp_path, mimetype="video/mp4")
    # 再查 uploads（原视频）
    upload_path = os.path.join("./uploads", filename)
    if os.path.exists(upload_path):
        from flask import send_file
        return send_file(upload_path, mimetype="video/mp4")
    return jsonify({"code": 404, "msg": "视频文件不存在"}), 404


# ====================== 学生视频列表查询 ======================
@app.route("/api/video/my", methods=["GET"])
@token_required
def get_my_video():
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生可查看"}), 403
    uid = request.user_info["uid"]
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id,name,type,count,score,model_accuracy,avg_confidence,createTime,
                   IFNULL(original_video,'') as original_video, IFNULL(output_video,'') as output_video
            FROM videos WHERE uid=%s ORDER BY createTime DESC
        """, (uid,))
        rows = cur.fetchall()
        videoList = []
        for item in rows:
            videoList.append({
                "id": item[0] if item[0] else "",
                "video_name": item[1] if item[1] is not None else "",
                "action_type": item[2] if item[2] is not None else "",
                "repeat_count": int(item[3]) if item[3] is not None else 0,
                "avg_score": float(item[4]) if item[4] is not None else 0.0,
                "model_accuracy": float(item[5]) if item[5] is not None else 0.0,
                "avg_confidence": float(item[6]) if item[6] is not None else 0.0,
                "upload_time": str(item[7]) if item[7] is not None else "",
                "original_video": item[8] if len(item) > 8 and item[8] else "",
                "output_video": item[9] if len(item) > 9 and item[9] else ""
            })
        return jsonify({"code": 200, "data": videoList, "msg": "查询成功"})
    except Exception as err:
        print("查询异常", err)
        return jsonify({"code": 500, "msg": f"查询失败：{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ====================== 摄像头识别接口 ======================
@app.route("/api/camera_analyze", methods=["POST"])
@token_required
def camera_analyze():
    """
    前端点击"打开摄像头" → 后端弹出摄像头cv2窗口 → 实时标注 → 关闭后返回结果
    注意：这个接口会阻塞直到用户关闭摄像头窗口（因为需要等待run_camera执行完）
    """
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生可使用"}), 403
    uid = request.user_info["uid"]
    try:
        from main import run_camera_return
    except ImportError:
        try:
            import importlib
            main_mod = importlib.import_module("main")
            run_camera_return = main_mod.run_camera_return
        except Exception as e:
            return jsonify({"code": 500, "msg": f"main.py加载失败: {e}"}), 500
    try:
        result = run_camera_return(uid)
        if result:
            return jsonify({"code": 200, "msg": "摄像头识别结束", "data": result})
        return jsonify({"code": 200, "msg": "摄像头识别结束（无结果），刷新表格查看"})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"摄像头异常: {str(e)}"}), 500


# ====================== 测试接口 ======================
@app.route("/api/test", methods=["GET"])
def test_conn():
    return jsonify({"code": 200, "msg": "后端服务正常运行（前端触发 → 后端弹cv2窗口识别）"})


# ====================== 教师接口 ======================
@app.route("/api/student/all", methods=["GET"])
@token_required
def get_all_student():
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        keyword = request.args.get("keyword", "").strip()
        if keyword:
            cur.execute(
                "SELECT id,uid,name,sex,age,height,weight,createTime FROM students WHERE uid LIKE %s OR name LIKE %s ORDER BY createTime DESC",
                (f"%{keyword}%", f"%{keyword}%")
            )
        else:
            cur.execute("SELECT id,uid,name,sex,age,height,weight,createTime FROM students ORDER BY createTime DESC")
        rows = cur.fetchall()
        studentList = [{
            "id": item[0], "uid": item[1] or "", "name": item[2] or "",
            "sex": item[3] or "", "age": item[4] or "",
            "height": item[5] or "", "weight": item[6] or "",
            "create_time": str(item[7]) if item[7] else ""
        } for item in rows]
        return jsonify({"code": 200, "data": studentList, "msg": "查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败：{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/student/add", methods=["POST"])
@token_required
def add_student():
    """添加学生（字段与students表匹配，password默认123456）"""
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    data = request.get_json()
    uid = data.get("uid", "").strip()
    name = data.get("name", "").strip()
    sex = data.get("sex", "").strip()
    age = str(data.get("age", "")).strip()
    height = str(data.get("height", "")).strip()
    weight = str(data.get("weight", "")).strip()
    if not uid or not name:
        return jsonify({"code": 400, "msg": "学号和姓名不能为空"}), 400
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM students WHERE uid=%s", (uid,))
        if cur.fetchone():
            return jsonify({"code": 400, "msg": "该学号已存在"}), 400
        cur.execute(
            "INSERT INTO students (uid, password, name, sex, age, height, weight, createTime) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())",
            (uid, "123456", name, sex, age, height, weight)
        )
        conn.commit()
        return jsonify({"code": 200, "msg": "添加成功"})
    except Exception as err:
        if conn:
            conn.rollback()
        return jsonify({"code": 500, "msg": f"添加失败：{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/student/update", methods=["PUT"])
@token_required
def update_student():
    """编辑学生信息（可修改姓名、性别、年龄、身高、体重）"""
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    data = request.get_json()
    sid = data.get("id")
    name = str(data.get("name", "")).strip()
    sex = str(data.get("sex", "")).strip()
    age = str(data.get("age", "")).strip()
    height = str(data.get("height", "")).strip()
    weight = str(data.get("weight", "")).strip()
    if not sid:
        return jsonify({"code": 400, "msg": "缺少学生ID"}), 400
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE students SET name=%s, sex=%s, age=%s, height=%s, weight=%s WHERE id=%s",
            (name, sex, age, height, weight, sid)
        )
        conn.commit()
        return jsonify({"code": 200, "msg": "修改成功"})
    except Exception as err:
        if conn:
            conn.rollback()
        return jsonify({"code": 500, "msg": f"修改失败：{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/student/delete", methods=["DELETE"])
@token_required
def delete_student():
    """删除学生（连同关联的videos和message记录）"""
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    data = request.get_json()
    sid = data.get("id")
    if not sid:
        return jsonify({"code": 400, "msg": "缺少学生ID"}), 400
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        # 先查询uid，用于清理关联数据
        cur.execute("SELECT uid FROM students WHERE id=%s", (sid,))
        row = cur.fetchone()
        if not row:
            return jsonify({"code": 400, "msg": "学生不存在"}), 400
        stu_uid = row[0]
        # 删除关联的留言
        cur.execute("DELETE FROM message WHERE stu_uid=%s", (stu_uid,))
        # 删除关联的视频
        cur.execute("DELETE FROM videos WHERE uid=%s", (stu_uid,))
        # 删除学生
        cur.execute("DELETE FROM students WHERE id=%s", (sid,))
        conn.commit()
        return jsonify({"code": 200, "msg": "删除成功"})
    except Exception as err:
        if conn:
            conn.rollback()
        return jsonify({"code": 500, "msg": f"删除失败：{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/video/all", methods=["GET"])
@token_required
def get_all_video():
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id,v.uid,v.name,v.type,v.count,v.score,v.model_accuracy,v.avg_confidence,v.createTime,s.name,
                   IFNULL(v.original_video,'') as original_video, IFNULL(v.output_video,'') as output_video
            FROM videos v LEFT JOIN students s ON v.uid = s.uid ORDER BY v.createTime DESC
        """)
        rows = cur.fetchall()
        videoAllList = [{
            "id": item[0], "stu_uid": item[1] or "", "video_name": item[2] or "",
            "action_type": item[3] or "", "repeat_count": int(item[4]) if item[4] else 0,
            "avg_score": float(item[5]) if item[5] else 0.0,
            "model_accuracy": float(item[6]) if item[6] else 0.0,
            "avg_confidence": float(item[7]) if item[7] else 0.0,
            "upload_time": str(item[8]) if item[8] else "",
            "stu_name": item[9] if len(item) > 9 and item[9] else "未知学生",
            "original_video": item[10] if len(item) > 10 and item[10] else "",
            "output_video": item[11] if len(item) > 11 and item[11] else ""
        } for item in rows]
        return jsonify({"code": 200, "data": videoAllList, "msg": "查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/report/all", methods=["GET"])
@token_required
def get_all_report():
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.uid,s.name,AVG(v.score) as avg_total_score,SUM(v.count) as total_times,COUNT(v.id) as video_num
            FROM students s LEFT JOIN videos v ON s.uid = v.uid GROUP BY s.uid,s.name
        """)
        rows = cur.fetchall()
        reportList = [{
            "stu_uid": item[0], "stu_name": item[1],
            "avg_total_score": round(float(item[2]) if item[2] else 0, 2),
            "total_train_times": int(item[3]) if item[3] else 0,
            "upload_video_count": int(item[4]) if item[4] else 0
        } for item in rows]
        return jsonify({"code": 200, "data": reportList, "msg": "报表查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/message/tea", methods=["GET"])
@token_required
def get_tea_message():
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    tea_uid = request.user_info["uid"]
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT m.id,m.stu_uid,s.name,m.content,m.reply,m.create_time
            FROM message m LEFT JOIN students s ON m.stu_uid = s.uid
            WHERE m.tea_uid=%s ORDER BY m.create_time DESC
        """, (tea_uid,))
        rows = cur.fetchall()
        msgList = [{
            "id": item[0], "stu_uid": item[1], "stu_name": item[2] or "未知学生",
            "content": item[3], "reply": item[4] or "暂未回复",
            "create_time": str(item[5])
        } for item in rows]
        return jsonify({"code": 200, "data": msgList, "msg": "留言查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/message/reply", methods=["POST"])
@token_required
def reply_message():
    if request.user_info["role"] != "teacher":
        return jsonify({"code": 403, "msg": "仅教师访问"}), 403
    data = request.get_json()
    msg_id = data.get("id")
    reply_text = data.get("reply")
    if not msg_id or not reply_text:
        return jsonify({"code": 400, "msg": "参数不全"}), 400
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("UPDATE message SET reply=%s WHERE id=%s", (reply_text, msg_id))
        conn.commit()
        return jsonify({"code": 200, "msg": "回复成功"})
    except Exception as err:
        conn.rollback()
        return jsonify({"code": 500, "msg": f"回复失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ====================== 学生端接口 ======================
@app.route("/api/score/my", methods=["GET"])
@token_required
def get_my_score():
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生访问"}), 403
    uid = request.user_info["uid"]
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id,type,count,score,model_accuracy,avg_confidence,createTime FROM videos WHERE uid=%s ORDER BY createTime DESC", (uid,))
        rows = cur.fetchall()
        scoreList = [{
            "id": item[0], "action_type": item[1], "repeat_count": int(item[2]) if item[2] else 0,
            "avg_score": float(item[3]) if item[3] else 0,
            "model_accuracy": float(item[4]) if item[4] else 0,
            "avg_confidence": float(item[5]) if item[5] else 0,
            "upload_time": str(item[6])
        } for item in rows]
        return jsonify({"code": 200, "data": scoreList, "msg": "查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/report/my", methods=["GET"])
@token_required
def get_my_report():
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生访问"}), 403
    uid = request.user_info["uid"]
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT AVG(score) as avg_score,SUM(count) as total_times,COUNT(id) as video_count FROM videos WHERE uid=%s", (uid,))
        row = cur.fetchone()
        data = {
            "avg_total_score": round(float(row[0]) if row[0] else 0, 2),
            "total_train_times": int(row[1]) if row[1] else 0,
            "upload_video_num": int(row[2]) if row[2] else 0
        }
        return jsonify({"code": 200, "data": data, "msg": "报表查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/message/send", methods=["POST"])
@token_required
def send_message():
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生访问"}), 403
    data = request.get_json()
    stu_uid = request.user_info["uid"]
    tea_uid = data.get("tea_uid")
    content = data.get("content")
    if not tea_uid or not content:
        return jsonify({"code": 400, "msg": "参数缺失"}), 400
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO message(stu_uid,tea_uid,content) VALUES (%s,%s,%s)", (stu_uid, tea_uid, content))
        conn.commit()
        return jsonify({"code": 200, "msg": "留言提交成功"})
    except Exception as err:
        conn.rollback()
        return jsonify({"code": 500, "msg": f"提交失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/message/my", methods=["GET"])
@token_required
def get_my_msg():
    if request.user_info["role"] != "student":
        return jsonify({"code": 403, "msg": "仅学生访问"}), 403
    stu_uid = request.user_info["uid"]
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT m.id,t.name,m.content,m.reply,m.create_time
            FROM message m LEFT JOIN teacher t ON m.tea_uid = t.uid
            WHERE m.stu_uid=%s ORDER BY m.create_time DESC
        """, (stu_uid,))
        rows = cur.fetchall()
        msgList = [{
            "id": item[0], "tea_name": item[1] or "未知教师",
            "content": item[2], "reply": item[3] or "老师未回复",
            "create_time": str(item[4])
        } for item in rows]
        return jsonify({"code": 200, "data": msgList, "msg": "查询成功"})
    except Exception as err:
        return jsonify({"code": 500, "msg": f"查询失败:{str(err)}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/api/ai/chat", methods=["POST"])
@token_required
def ai_chat():
    data = request.get_json()
    msg = data.get("msg", "").strip()
    if "俯卧撑" in msg or "push-up" in msg.lower():
        reply = "俯卧撑：双手与肩同宽，全程身体一条直线，每组10-15次。"
    elif "深蹲" in msg or "squat" in msg.lower():
        reply = "深蹲：双脚与肩同宽，下蹲大腿平行地面，膝盖不超脚尖。"
    else:
        reply = f"AI回复：{msg}，运动前热身，运动后拉伸。"
    return jsonify({"code": 200, "data": {"reply": reply}, "msg": "回复成功"})


# ====================== 启动 ======================
if __name__ == "__main__":
    print("=" * 60)
    print("  AI健身后端服务启动")
    print("  流程：前端上传视频 → 后端弹出cv2窗口识别 → 结果返回前端")
    print("=" * 60)
    run_port = 5000
    try:
        app.run(host="0.0.0.0", port=run_port, debug=False, threaded=True, use_reloader=False)
    except OSError as e:
        if "Only one usage of each socket address" in str(e):
            run_port += 1
            print(f"\n端口{run_port-1}占用，切换端口{run_port}")
            app.run(host="0.0.0.0", port=run_port, debug=False, threaded=True, use_reloader=False)
        else:
            raise
