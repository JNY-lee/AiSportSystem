<template>
  <div style="width:80%;margin:0 auto;">
    <el-card title="AI健身助手">
      <el-input v-model="askText" placeholder="输入健身问题" @keyup.enter="chat"/>
      <el-button type="primary" style="margin:10px 0" @click="chat">发送提问</el-button>
      <div v-if="replyText" style="background:#f5f7fa;padding:10px;border-radius:4px;">
        <b>AI回复：</b>{{replyText}}
      </div>
    </el-card>
  </div>
</template>
<script>
import request from '@/api/request'
export default {
  data(){
    return {
      askText:"",
      replyText:""
    }
  },
  methods:{
    async chat(){
      if(!this.askText) return this.$message.warning("请输入问题")
      const res = await request.post('/ai/chat',{msg:this.askText})
      if(res.code===200){
        this.replyText = res.data.reply
      }
    }
  }
}
</script>