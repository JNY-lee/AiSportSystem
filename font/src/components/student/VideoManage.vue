<template>
  <div style="padding: 20px">
    <el-row :gutter="20">
      <!-- 左侧操作区 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <div slot="header"><span style="font-weight:bold;font-size:16px">运动识别操作</span></div>

          <!-- 上传视频按钮 -->
          <el-button
            type="primary"
            icon="el-icon-upload2"
            :loading="uploadLoading"
            @click="dialogVisible = true"
          >
            {{ uploadLoading ? '后端识别窗口运行中...' : '上传本地MP4视频识别' }}
          </el-button>

          <el-divider></el-divider>

          <!-- 摄像头按钮 -->
          <el-button
            type="success"
            icon="el-icon-video-camera"
            :loading="cameraLoading"
            @click="openCamera"
          >
            {{ cameraLoading ? '摄像头运行中...' : '打开摄像头实时检测' }}
          </el-button>

          <el-divider></el-divider>

          <!-- 识别状态提示 -->
          <el-alert
            v-if="uploadLoading"
            title="后端正在弹出识别窗口，请在后端电脑上查看cv2窗口..."
            type="warning"
            :closable="false"
            show-icon
            style="margin-top:10px"
          />

          <!-- 本次识别结果卡片 -->
          <el-card v-if="latestResult" shadow="never" style="background:#f0f9eb;margin-top:10px">
            <div slot="header"><span style="font-weight:bold;font-size:14px;color:#67c23a">本次识别结果</span></div>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="运动类型">{{ latestResult.action_type }}</el-descriptions-item>
              <el-descriptions-item label="完成次数">{{ latestResult.repeat_count }}</el-descriptions-item>
              <el-descriptions-item label="动作质量分">{{ latestResult.avg_score }}</el-descriptions-item>
              <el-descriptions-item label="模型置信度">{{ latestResult.avg_confidence }}</el-descriptions-item>
              <el-descriptions-item v-if="latestResult.output_video" label="合成视频">
                <el-button type="text" size="small" @click="playResultVideo(latestResult.output_video)">
                  点击查看AI合成视频
                </el-button>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-card>
      </el-col>

      <!-- 右侧历史记录表格 -->
      <el-col :span="16">
        <el-card shadow="hover">
          <div slot="header">
            <span style="font-weight:bold;font-size:16px">运动训练历史记录</span>
            <el-button
              type="text"
              icon="el-icon-refresh"
              style="float:right"
              @click="getVideoList"
            >刷新</el-button>
          </div>
          <el-table :data="videoList" border v-loading="loading" stripe>
            <el-table-column label="视频名称" prop="video_name" min-width="180" show-overflow-tooltip/>
            <el-table-column label="运动类型" prop="action_type" width="120">
              <template slot-scope="scope">
                <el-tag :type="getActionTag(scope.row.action_type)" size="small">
                  {{ scope.row.action_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="完成次数" prop="repeat_count" width="90" align="center"/>
            <el-table-column label="动作质量分" width="100" align="center">
              <template slot-scope="scope">
                <span :style="{color: getScoreColor(scope.row.avg_score)}">
                  {{ scope.row.avg_score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="模型准确率" prop="model_accuracy" width="100" align="center"/>
            <el-table-column label="平均置信度" prop="avg_confidence" width="100" align="center"/>
            <el-table-column label="上传时间" prop="upload_time" width="170"/>
            <template slot="empty">
              <div style="padding:30px;color:#909399">
                <i class="el-icon-folder-opened" style="font-size:40px"></i>
                <p style="margin-top:10px">暂无运动训练数据，请上传视频开始识别</p>
              </div>
            </template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 上传视频对话框 -->
    <el-dialog
      title="上传本地MP4视频进行AI识别"
      :visible.sync="dialogVisible"
      width="50%"
      :close-on-click-modal="false"
      :close-on-press-escape="!uploadLoading"
      :show-close="!uploadLoading"
    >
      <el-alert
        title="上传后后端会弹出cv2窗口播放视频并实时标注识别结果（和直接运行main.py一样的效果），窗口关闭后结果自动返回"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom:20px"
      />

      <el-upload
        ref="uploadRef"
        accept=".mp4,.avi,.mov"
        drag
        :auto-upload="false"
        :on-change="onFileChange"
        :limit="1"
        :file-list="fileList"
      >
        <i class="el-icon-upload"></i>
        <div class="el-upload__text">将MP4视频文件拖到此处，或<em>点击选择文件</em></div>
        <div class="el-upload__tip" slot="tip">仅支持 MP4/AVI/MOV 格式，原始视频保存至 backend/uploads，AI合成视频保存至 backend/upload_temp</div>
      </el-upload>

      <span slot="footer" class="dialog-footer">
        <el-button @click="dialogVisible = false" :disabled="uploadLoading">取消</el-button>
        <el-button
          type="primary"
          :loading="uploadLoading"
          :disabled="!selectedFile"
          @click="submitUpload"
        >
          {{ uploadLoading ? '后端识别窗口运行中，请等待...' : '开始识别' }}
        </el-button>
      </span>
    </el-dialog>

    <!-- 合成视频查看弹窗 -->
    <el-dialog
      title="AI合成视频（带关键点、分数标注）"
      :visible.sync="videoDialogVisible"
      width="70%"
      :close-on-click-modal="false"
    >
      <div v-if="videoDialogUrl" style="text-align:center">
        <video
          :src="videoDialogUrl"
          controls
          autoplay
          style="max-width:100%; max-height:70vh; border-radius:8px; background:#000"
        >
          您的浏览器不支持视频播放
        </video>
      </div>
      <div v-else style="text-align:center;padding:40px;color:#909399">
        <i class="el-icon-video-camera" style="font-size:60px"></i>
        <p style="margin-top:10px">合成视频文件不存在或尚未生成</p>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import request from '@/api/request'

export default {
  name: 'VideoManage',
  data() {
    return {
      videoList: [],
      loading: false,
      uploadLoading: false,
      cameraLoading: false,
      dialogVisible: false,
      selectedFile: null,
      fileList: [],
      latestResult: null,
      currentTaskId: null,
      pollTimer: null,
      videoDialogVisible: false,
      videoDialogUrl: ''
    }
  },
  mounted() {
    this.getVideoList()
  },
  beforeDestroy() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  },
  methods: {
    /** 获取历史视频列表 */
    async getVideoList() {
      this.loading = true
      try {
        const res = await request.get('/video/my')
        if (res.code === 200 && res.data) {
          this.videoList = res.data
        }
      } catch (err) {
        this.$message.error('列表加载失败，请检查后端服务是否启动')
      } finally {
        this.loading = false
      }
    },

    /** 文件选择回调 */
    onFileChange(file) {
      if (file && file.raw) {
        this.selectedFile = file.raw
      }
    },

    /** 提交上传 —— 启动后端识别（会弹cv2窗口） */
    async submitUpload() {
      if (!this.selectedFile) {
        this.$message.warning('请先选择一个视频文件')
        return
      }

      this.uploadLoading = true
      const formData = new FormData()
      formData.append('video_file', this.selectedFile)

      try {
        const res = await request.post('/upload_video_analyze', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000
        })

        if (res.code === 200 && res.data && res.data.task_id) {
          this.currentTaskId = res.data.task_id
          this.dialogVisible = false
          this.$message.info('视频已提交，后端正在弹出识别窗口，请查看后端电脑')
          this.fileList = []
          this.selectedFile = null
          this.startPolling()
        } else {
          this.$message.error(res.msg || '提交失败')
          this.uploadLoading = false
        }
      } catch (err) {
        console.error('提交失败:', err)
        this.uploadLoading = false
        if (err.response && err.response.status === 401) {
          this.$message.error('登录已过期，请重新登录')
          this.$router.push('/login')
        } else {
          this.$message.error('视频提交失败，请检查后端服务')
        }
      }
    },

    /** 开始轮询识别状态 */
    startPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
      }
      this.pollTimer = setInterval(() => {
        this.pollTaskStatus()
      }, 2000)
    },

    /** 轮询后端识别状态 */
    async pollTaskStatus() {
      if (!this.currentTaskId) return
      try {
        const res = await request.get(`/task_status/${this.currentTaskId}`)
        if (res.code === 200 && res.data) {
          const { status, result, msg } = res.data
          if (status === 'done') {
            this.stopPolling()
            this.uploadLoading = false
            this.latestResult = result
            this.$message.success(
              `识别完成！运动: ${result.action_type}，次数: ${result.repeat_count}，质量分: ${result.avg_score}`
            )
            this.getVideoList()
          } else if (status === 'error') {
            this.stopPolling()
            this.uploadLoading = false
            this.$message.error(msg || '识别过程出错')
          }
        }
      } catch (err) {
        console.error('轮询失败:', err)
      }
    },

    /** 停止轮询 */
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
      this.currentTaskId = null
    },

    /** 播放合成视频 */
    playResultVideo(filename) {
      if (!filename) {
        this.$message.warning('合成视频文件不存在')
        return
      }
      this.videoDialogUrl = `http://localhost:5000/api/video/file/${filename}`
      this.videoDialogVisible = true
    },

    /** 摄像头识别 —— 后端弹cv2摄像头窗口 */
    async openCamera() {
      this.cameraLoading = true
      try {
        this.$message.info('正在启动摄像头，请在后端电脑上查看摄像头窗口')
        const res = await request.post('/camera_analyze', {}, {
          timeout: 600000
        })
        if (res.code === 200 && res.data) {
          this.latestResult = res.data
          this.$message.success('摄像头识别结束')
        } else {
          this.$message.success(res.msg || '摄像头识别结束')
        }
        this.getVideoList()
      } catch (err) {
        if (err.response && err.response.status === 401) {
          this.$message.error('登录已过期，请重新登录')
          this.$router.push('/login')
        } else {
          this.$message.error('摄像头启动失败，请检查后端是否有摄像头设备')
        }
      } finally {
        this.cameraLoading = false
      }
    },

    getActionTag(type) {
      const map = { 'push-up': 'danger', 'squat': 'warning', 'pullUp': 'success' }
      return map[type] || 'info'
    },

    getScoreColor(score) {
      if (score >= 80) return '#67c23a'
      if (score >= 60) return '#e6a23c'
      return '#f56c6c'
    }
  }
}
</script>
