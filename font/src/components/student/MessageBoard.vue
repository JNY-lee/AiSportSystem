<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card title="给老师留言">
          <el-input v-model="content" type="textarea" rows="5" placeholder="输入留言内容"/>
          <el-button type="primary" style="margin-top:10px" @click="sendMsg">提交留言</el-button>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card title="我的留言记录">
          <el-table :data="msgList" border style="margin-top:10px;">
            <el-table-column label="老师" prop="tea_name"/>
            <el-table-column label="我的留言" prop="content"/>
            <el-table-column label="老师回复" prop="reply"/>
            <el-table-column label="时间" prop="create_time"/>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script>
import request from '@/api/request'
export default {
  data(){
    return {
      content:"",
      msgList:[],
      userInfo:JSON.parse(localStorage.getItem("userInfo"))
    }
  },
  mounted(){
    this.loadMsg()
  },
  methods:{
    loadMsg(){
      request.get('/message/my',{params:{stu_uid:this.userInfo.uid}})
      .then(res=>{
        if(res.code===200) this.msgList = res.data
      })
    },
    async sendMsg(){
      // 固定发给张老师tea001
      const res = await request.post('/message/send',{
        stu_uid:this.userInfo.uid,
        tea_uid:"tea001",
        content:this.content
      })
      if(res.code===200){
        this.$message.success("留言发送成功")
        this.content = ""
        this.loadMsg()
      }else{
        this.$message.error(res.msg)
      }
    }
  }
}
</script>