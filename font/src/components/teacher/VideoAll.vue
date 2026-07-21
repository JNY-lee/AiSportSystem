<template>
  <div style="padding: 20px; min-height: 600px;">
    <h2>全部学生训练视频汇总</h2>

    <!-- 搜索栏 -->
    <div style="margin: 16px 0; display: flex; align-items: center; gap: 12px;">
      <el-input
        id="searchKeyword"
        v-model="keyword"
        placeholder="输入学生学号搜索"
        clearable
        style="width: 300px"
        @keyup.enter.native="searchVideo"
        @clear="resetSearch"
      >
        <i slot="prefix" class="el-icon-search" style="padding-top:12px;"></i>
      </el-input>
      <el-button type="primary" icon="el-icon-search" @click="searchVideo">搜索</el-button>
      <el-button icon="el-icon-refresh" @click="resetSearch">重置</el-button>
    </div>

    <el-table
      :data="filteredList"
      border
      style="margin-top: 8px; width: 100%;"
      v-loading="loading"
    >
      <el-table-column label="学生账号" prop="stu_uid" width="120"/>
      <el-table-column label="学生姓名" prop="stu_name" width="100"/>
      <el-table-column label="视频名称" prop="video_name" min-width="180" show-overflow-tooltip/>
      <el-table-column label="运动类型" prop="action_type" width="120">
        <template slot-scope="scope">
          <el-tag :type="getActionTag(scope.row.action_type)" size="small">
            {{ scope.row.action_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="完成次数" prop="repeat_count" width="100" align="center"/>
      <el-table-column label="平均分" prop="avg_score" width="90" align="center">
        <template slot-scope="scope">
          <span :style="{color: getScoreColor(scope.row.avg_score)}">
            {{ scope.row.avg_score }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="模型准确率" prop="model_accuracy" width="110" align="center"/>
      <el-table-column label="平均置信度" prop="avg_confidence" width="110" align="center"/>
      <el-table-column label="上传时间" prop="upload_time" width="170"/>
      <el-table-column label="操作" width="220" align="center" fixed="right">
        <template slot-scope="scope">
          <el-button
            type="info"
            size="mini"
            icon="el-icon-video-camera"
            :disabled="!scope.row.original_video"
            @click="playOriginal(scope.row)"
          >查看原始视频</el-button>
          <el-button
            type="success"
            size="mini"
            icon="el-icon-view"
            :disabled="!scope.row.output_video"
            @click="playOutput(scope.row)"
          >查看AI合成视频</el-button>
        </template>
      </el-table-column>
      <template slot="empty">
        <div style="padding:40px; color:#999;">{{ keyword ? '未找到匹配的学生训练视频' : '暂无学生训练视频数据' }}</div>
      </template>
    </el-table>

    <!-- 原始视频播放弹窗 -->
    <el-dialog
      :title="'原始视频 — ' + currentRow.stu_name + '（' + currentRow.stu_uid + '）'"
      :visible.sync="originalDialogVisible"
      width="70%"
      :close-on-click-modal="false"
    >
      <div style="margin-bottom:12px">
        <el-descriptions :column="4" size="small" border>
          <el-descriptions-item label="运动类型">
            <el-tag :type="getActionTag(currentRow.action_type)" size="mini">{{ currentRow.action_type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="完成次数">{{ currentRow.repeat_count }}</el-descriptions-item>
          <el-descriptions-item label="平均分">
            <span :style="{color: getScoreColor(currentRow.avg_score), fontWeight:'bold'}">{{ currentRow.avg_score }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ currentRow.upload_time }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-if="originalVideoUrl" style="text-align:center">
        <video
          :src="originalVideoUrl"
          controls
          style="max-width:100%; max-height:65vh; border-radius:8px; background:#000"
        >
          您的浏览器不支持视频播放
        </video>
      </div>
      <div v-else style="text-align:center;padding:60px;color:#909399">
        <i class="el-icon-video-camera" style="font-size:60px"></i>
        <p style="margin-top:10px">原始视频文件不存在</p>
      </div>
    </el-dialog>

    <!-- AI合成视频播放弹窗 -->
    <el-dialog
      :title="'AI合成视频（带动作识别+计数+质量评估） — ' + currentRow.stu_name + '（' + currentRow.stu_uid + '）'"
      :visible.sync="outputDialogVisible"
      width="70%"
      :close-on-click-modal="false"
    >
      <div style="margin-bottom:12px">
        <el-descriptions :column="4" size="small" border>
          <el-descriptions-item label="运动类型">
            <el-tag :type="getActionTag(currentRow.action_type)" size="mini">{{ currentRow.action_type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="完成次数">{{ currentRow.repeat_count }}</el-descriptions-item>
          <el-descriptions-item label="平均分">
            <span :style="{color: getScoreColor(currentRow.avg_score), fontWeight:'bold'}">{{ currentRow.avg_score }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ currentRow.upload_time }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-if="outputVideoUrl" style="text-align:center">
        <video
          :src="outputVideoUrl"
          controls
          autoplay
          style="max-width:100%; max-height:65vh; border-radius:8px; background:#000"
        >
          您的浏览器不支持视频播放
        </video>
      </div>
      <div v-else style="text-align:center;padding:60px;color:#909399">
        <i class="el-icon-video-camera" style="font-size:60px"></i>
        <p style="margin-top:10px">AI合成视频文件不存在或尚未生成</p>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import request from '@/api/request'
export default {
  name: "VideoAll",
  data() {
    return {
      allData: [],
      keyword: "",
      loading: false,
      currentRow: {},
      originalDialogVisible: false,
      outputDialogVisible: false,
      originalVideoUrl: '',
      outputVideoUrl: ''
    }
  },
  computed: {
    filteredList() {
      if (!this.keyword.trim()) {
        return this.allData
      }
      const kw = this.keyword.trim().toLowerCase()
      return this.allData.filter(item => {
        return (item.stu_uid && item.stu_uid.toLowerCase().includes(kw)) ||
               (item.stu_name && item.stu_name.toLowerCase().includes(kw))
      })
    }
  },
  mounted() {
    console.log("教师VideoAll页面挂载成功，发起请求")
    this.fetchAllVideo()
  },
  methods: {
    async fetchAllVideo() {
      const token = localStorage.getItem('token')
      const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
      if (!token) {
        this.$message.warning('登录失效，请重新登录')
        this.$router.push('/login')
        return
      }
      if (userInfo.type !== 'teacher') {
        this.$message.error('仅管理员可访问')
        return
      }
      this.loading = true
      try {
        const res = await request.get('/video/all')
        console.log("后端返回数据：", res)
        if (res.code === 200) {
          this.allData = res.data || []
        } else {
          this.$message.warning(res.msg)
        }
      } catch (err) {
        console.error("请求报错：", err)
        this.$message.error("加载数据失败")
      } finally {
        this.loading = false
      }
    },

    searchVideo() {
      // filteredList computed 属性根据 keyword 自动过滤
    },

    resetSearch() {
      this.keyword = ""
    },

    /** 查看原始视频 */
    playOriginal(row) {
      if (!row.original_video) {
        this.$message.warning('该记录暂无原始视频文件')
        return
      }
      this.currentRow = row
      this.originalVideoUrl = `http://localhost:5000/api/video/file/${row.original_video}`
      this.originalDialogVisible = true
    },

    /** 查看AI合成视频 */
    playOutput(row) {
      if (!row.output_video) {
        this.$message.warning('该记录暂无AI合成视频文件')
        return
      }
      this.currentRow = row
      this.outputVideoUrl = `http://localhost:5000/api/video/file/${row.output_video}`
      this.outputDialogVisible = true
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
