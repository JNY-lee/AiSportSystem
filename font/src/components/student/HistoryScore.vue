<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <h4>我的训练历史成绩</h4>
          <el-table :data="scoreList" border style="margin-top:10px;">
            <el-table-column label="运动类型" prop="action_type"/>
            <el-table-column label="完成次数" prop="repeat_count"/>
            <el-table-column label="平均分" prop="avg_score"/>
            <el-table-column label="模型准确率" prop="model_accuracy"/>
            <el-table-column label="上传时间" prop="upload_time"/>
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
      scoreList:[],
      userInfo:JSON.parse(localStorage.getItem("userInfo"))
    }
  },
  mounted(){
    request.get('/score/my',{params:{uid:this.userInfo.uid}})
    .then(res=>{
      if(res.code===200) this.scoreList = res.data
    })
    .catch(err=>console.error("成绩加载失败",err))
  }
}
</script>