-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_db;

-- 1.学生表 students
CREATE TABLE `students` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `uid` VARCHAR(100) NOT NULL COMMENT '学生登录账号，唯一',
  `password` VARCHAR(100) NOT NULL COMMENT '登录密码',
  `name` VARCHAR(100) NOT NULL COMMENT '姓名',
  `sex` VARCHAR(100) NOT NULL COMMENT '性别',
  `age` VARCHAR(100) NOT NULL COMMENT '年龄',
  `height` VARCHAR(100) NOT NULL COMMENT '身高cm',
  `weight` VARCHAR(100) NOT NULL COMMENT '体重kg',
  `createTime` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uid_unique` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2.教师表 teacher
CREATE TABLE `teacher` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `uid` VARCHAR(100) NOT NULL COMMENT '教师账号',
  `password` VARCHAR(100) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uid_unique` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3.视频训练主表 videos
CREATE TABLE `videos` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键视频ID',
  `uid` VARCHAR(100) NOT NULL COMMENT '关联学生uid',
  `name` VARCHAR(100) NOT NULL COMMENT '来源标识：local_video / camera_realtime',
  `type` VARCHAR(100) NOT NULL COMMENT '运动类型: push-up / pull Up / squat',
  `video` VARCHAR(100) DEFAULT NULL COMMENT '视频存储路径',
  `count` INT DEFAULT 0 COMMENT '运动总次数',
  `score` FLOAT DEFAULT 0 COMMENT '本次动作平均分',
  `model_accuracy` FLOAT DEFAULT 0 COMMENT '模型整体准确率',
  `avg_confidence` FLOAT DEFAULT 0 COMMENT '识别平均置信度',
  `createTime` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE videos ADD COLUMN original_video VARCHAR(255) DEFAULT NULL COMMENT '原视频文件名';
ALTER TABLE videos ADD COLUMN output_video VARCHAR(255) DEFAULT NULL COMMENT 'AI合成视频文件名';



-- 4.逐帧明细日志 history（修复video_id缺少反引号语法错误）
CREATE TABLE `history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `video_id` INT NOT NULL COMMENT '关联videos.id',
  `abdomen_angle` FLOAT DEFAULT 0 COMMENT '腰腹角度',
  `left_leg_angle` FLOAT DEFAULT 0 COMMENT '左腿角度',
  `right_leg_angle` FLOAT DEFAULT 0 COMMENT '右腿角度',
  `frame_score` FLOAT DEFAULT 0 COMMENT '单帧分数',
  `frame_no` INT NOT NULL COMMENT '帧序号',
  `single_conf` FLOAT DEFAULT 0 COMMENT '当前帧识别置信度',
  `createTime` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5.留言表 message
CREATE TABLE `message` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `stu_uid` VARCHAR(100) NOT NULL COMMENT '学生账号',
  `tea_uid` VARCHAR(100) NOT NULL COMMENT '教师账号',
  `content` TEXT NOT NULL COMMENT '留言内容',
  `reply` TEXT DEFAULT NULL COMMENT '教师回复',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 初始化测试账号
INSERT INTO teacher(uid,password,name) VALUES ('tea001','123456','张老师');
INSERT INTO students(uid,password,name,sex,age,height,weight) VALUES ('stu001','123456','小明','男','20','175','65');