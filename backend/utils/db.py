
import pymysql
from datetime import datetime

def get_mysql_conn():
    """获取数据库连接（增加超时配置和容错）"""
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="123456",
            database="ai_db",
            charset="utf8mb4",
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except pymysql.Error as e:
        print(f"数据库连接失败：{e}")
        return None

def insert_local_video_record(action_type, total_count, model_acc, avg_conf, source_name, avg_score):
    """
    本地视频/摄像头识别写入videos主表
    :return: 当前插入视频自增id，失败返回0
    """
    conn = get_mysql_conn()
    if conn is None:
        print("数据库连接失败，跳过入库")
        return 0

    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            video VARCHAR(512),
            count INT DEFAULT 0,
            score FLOAT DEFAULT 0.0,
            model_accuracy FLOAT DEFAULT 0.0,
            avg_confidence FLOAT DEFAULT 0.0,
            createTime DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        sql = """
        INSERT INTO videos
        (uid, name, type, video, count, score, model_accuracy, avg_confidence, createTime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        action_type = action_type.replace(" ", "") if action_type else "unknown"
        cur.execute(sql, (
            "stu001",
            source_name,
            action_type,
            "",
            total_count,
            avg_score,
            model_acc,
            avg_conf,
            datetime.now()
        ))
        conn.commit()
        video_id = cur.lastrowid
        cur.close()
        conn.close()
        return video_id
    except pymysql.Error as e:
        print(f"videos表插入失败: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return 0

def insert_upload_video_record(uid, filename, action, save_path, total_cnt, avg_score, model_acc, avg_conf):
    """Web端上传视频入库接口函数"""
    conn = get_mysql_conn()
    if conn is None:
        print("数据库连接失败，跳过入库")
        return 0

    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            video VARCHAR(512),
            count INT DEFAULT 0,
            score FLOAT DEFAULT 0.0,
            model_accuracy FLOAT DEFAULT 0.0,
            avg_confidence FLOAT DEFAULT 0.0,
            createTime DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        sql = """
        INSERT INTO videos
        (uid, name, type, video, count, score, model_accuracy, avg_confidence, createTime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        action = action.replace(" ", "") if action else "unknown"
        cur.execute(sql, (
            uid, filename, action, save_path, total_cnt, 
            avg_score, model_acc, avg_conf, datetime.now()
        ))
        conn.commit()
        video_id = cur.lastrowid
        cur.close()
        conn.close()
        return video_id
    except pymysql.Error as e:
        print(f"上传视频入库失败: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return 0

def insert_frame_history(video_id, frame_no, ab_angle, l_leg, r_leg, f_score, single_conf):
    """
    写入逐帧明细表history
    """
    conn = get_mysql_conn()
    if conn is None:
        print("数据库连接失败，跳过帧历史入库")
        return

    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            video_id INT NOT NULL,
            abdomen_angle FLOAT DEFAULT 0.0,
            left_leg_angle FLOAT DEFAULT 0.0,
            right_leg_angle FLOAT DEFAULT 0.0,
            frame_score FLOAT DEFAULT 0.0,
            frame_no INT DEFAULT 0,
            single_conf FLOAT DEFAULT 0.0,
            createTime DATETIME,
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        sql = """
        INSERT INTO history
        (video_id, abdomen_angle, left_leg_angle, right_leg_angle, frame_score, frame_no, single_conf, createTime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql, (
            video_id, ab_angle, l_leg, r_leg, f_score, 
            frame_no, single_conf, datetime.now()
        ))
        conn.commit()
        cur.close()
        conn.close()
    except pymysql.Error as e:
        print(f"帧{frame_no} history插入失败: {e}")
        if conn:
            conn.rollback()
            conn.close()