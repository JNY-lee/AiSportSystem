<template>
  <el-container style="height:100vh;">
    <el-aside width="220px" style="background:#304156;">
      <el-menu
        default-active="$route.path"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
      >
        <template v-if="user.type === 'teacher'">
          <el-menu-item index="/teacher/student">学生管理</el-menu-item>
          <el-menu-item index="/teacher/video">视频管理</el-menu-item>
          <el-menu-item index="/teacher/report">报告中心</el-menu-item>
          <el-menu-item index="/teacher/message">留言管理</el-menu-item>
        </template>
        <template v-if="user.type === 'student'">
          <el-menu-item index="/student/video">视频列表</el-menu-item>
          <el-menu-item index="/student/score">历史成绩</el-menu-item>
          <el-menu-item index="/student/report">学生报告</el-menu-item>
          <el-menu-item index="/student/ai">AI体育助手</el-menu-item>
          <el-menu-item index="/student/message">留言板</el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-main>
        <router-view/>
      </el-main>
    </el-container>
  </el-container>
</template>
<script>
export default {
  data(){
    return {
      user:JSON.parse(localStorage.getItem('userInfo'))
    }
  }
}
</script>