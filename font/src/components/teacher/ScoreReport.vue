<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <h4>全体学生训练成绩报表</h4>
          <el-table :data="reportList" border style="margin-top:10px;">
            <el-table-column label="学生账号" prop="stu_uid"/>
            <el-table-column label="学生姓名" prop="stu_name"/>
            <el-table-column label="平均总分" prop="avg_total_score"/>
            <el-table-column label="总训练次数" prop="total_train_times"/>
            <el-table-column label="上传视频数" prop="upload_video_count"/>
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
      reportList:[]
    }
  },
  mounted(){
    request.get('/report/all')
    .then(res=>{
      if(res.code===200) this.reportList = res.data
    })
    .catch(err=>console.error("报表加载失败",err))
  }
}
</script>