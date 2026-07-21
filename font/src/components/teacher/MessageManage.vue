<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <h4>学生留言管理</h4>
          <el-table :data="msgList" border style="margin-top:10px;" v-loading="loading">
            <el-table-column label="留言ID" prop="id" width="80"/>
            <el-table-column label="学生账号" prop="stu_uid" width="120"/>
            <el-table-column label="学生姓名" prop="stu_name" width="100"/>
            <el-table-column label="留言内容" prop="content" min-width="200" show-overflow-tooltip/>
            <el-table-column label="我的回复" prop="reply" min-width="180" show-overflow-tooltip>
              <template slot-scope="scope">
                <span :style="{color: scope.row.reply && scope.row.reply !== '暂未回复' ? '#67c23a' : '#909399'}">
                  {{ scope.row.reply || '暂未回复' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="留言时间" prop="create_time" width="170"/>
            <el-table-column label="操作" width="100" align="center">
              <template slot-scope="scope">
                <el-button type="primary" size="mini" @click="openReply(scope.row)">回复</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 回复弹窗 -->
    <el-dialog
      title="回复留言"
      :visible.sync="dialogVisible"
      width="500px"
      :close-on-click-modal="false"
    >
      <div style="margin-bottom:12px;color:#606266;">
        <strong>学生：</strong>{{ currentRow.stu_name }}（{{ currentRow.stu_uid }}）
      </div>
      <div style="margin-bottom:12px;color:#909399;">
        <strong>留言内容：</strong>{{ currentRow.content }}
      </div>
      <el-input
        id="replyText"
        v-model="replyText"
        type="textarea"
        :rows="4"
        placeholder="请输入回复内容"
        maxlength="500"
        show-word-limit
      />
      <div slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="replyLoading" :disabled="!replyText.trim()" @click="submitReply">提交回复</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import request from '@/api/request'
export default {
  data() {
    return {
      msgList: [],
      loading: false,
      dialogVisible: false,
      replyLoading: false,
      currentId: 0,
      currentRow: {},   // 当前回复的留言行数据
      replyText: "",
      teaInfo: JSON.parse(localStorage.getItem("userInfo") || '{}')
    }
  },
  mounted() {
    this.loadMsg()
  },
  methods: {
    async loadMsg() {
      this.loading = true
      try {
        const res = await request.get('/message/tea', { params: { tea_uid: this.teaInfo.uid } })
        if (res.code === 200) {
          this.msgList = res.data || []
        }
      } catch (err) {
        this.$message.error('加载留言失败')
      } finally {
        this.loading = false
      }
    },

    /** 打开回复弹窗 */
    openReply(row) {
      this.currentId = row.id
      this.currentRow = row
      // 如果已有回复内容，显示在输入框中方便修改
      this.replyText = (row.reply && row.reply !== '暂未回复') ? row.reply : ''
      this.dialogVisible = true
    },

    /** 提交回复 */
    async submitReply() {
      if (!this.replyText.trim()) {
        this.$message.warning('请输入回复内容')
        return
      }

      this.replyLoading = true
      try {
        const res = await request.post('/message/reply', {
          id: this.currentId,
          reply: this.replyText.trim()
        })
        if (res.code === 200) {
          this.$message.success('回复成功')
          this.dialogVisible = false
          this.loadMsg()
        } else {
          this.$message.error(res.msg || '回复失败')
        }
      } catch (err) {
        this.$message.error('回复请求失败')
      } finally {
        this.replyLoading = false
      }
    }
  }
}
</script>
