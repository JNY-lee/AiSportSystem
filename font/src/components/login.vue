<template>
  <div class="login-box">
    <el-form ref="loginRef" :model="loginForm" label-width="60px">
      <el-form-item label="账号">
        <el-input id="uid" v-model="loginForm.uid" placeholder="请输入账号"></el-input>
      </el-form-item>
      <el-form-item label="密码">
        <el-input id="pwd" v-model="loginForm.password" show-password placeholder="请输入密码"></el-input>
      </el-form-item>
      <el-form-item label="身份">
        <el-radio-group id="role" v-model="loginForm.role">
          <el-radio label="student">学生</el-radio>
          <el-radio label="teacher">管理员</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loginLoading" @click="handleLogin">登录</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>
<script>
import request from '@/api/request'
export default {
  data() {
    return {
      loginForm: {
        uid: '',
        password: '',
        role: 'teacher'
      },
      loginLoading: false
    }
  },
  methods: {
    async handleLogin() {
      if (!this.loginForm.uid.trim()) {
        this.$message.warning('请输入账号')
        return
      }
      if (!this.loginForm.password.trim()) {
        this.$message.warning('请输入密码')
        return
      }

      this.loginLoading = true
      try {
        const res = await request.post('/login', this.loginForm)
        if (res.code === 200) {
          this.$message.success('登录成功')
          // 存储token和用户信息
          localStorage.setItem('token', res.data.token)
          localStorage.setItem('userInfo', JSON.stringify(res.data))
          // 学生跳学生首页，教师跳教师首页
          if (res.data.type === 'student') {
            this.$router.push('/student/video')
          } else {
            this.$router.push('/teacher/video')
          }
        } else {
          // 不跳转页面，弹窗提示错误信息
          this.$message.error(res.msg || '登录失败')
        }
      } catch (err) {
        // 网络异常等情况，不跳转页面
        console.error('登录请求失败:', err)
        this.$message.error('网络异常，请检查后端服务是否启动')
      } finally {
        this.loginLoading = false
      }
    }
  }
}
</script>
