<template>
  <div style="padding: 20px">
    <!-- 顶部操作栏 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <el-row :gutter="15" align="middle">
        <el-col :span="6">
          <el-input
            v-model="keyword"
            placeholder="输入学号或姓名搜索"
            prefix-icon="el-icon-search"
            clearable
            @keyup.enter.native="searchStudent"
            @clear="searchStudent"
          />
        </el-col>
        <el-col :span="3">
          <el-button type="primary" icon="el-icon-search" @click="searchStudent">搜索</el-button>
        </el-col>
        <el-col :span="3">
          <el-button icon="el-icon-refresh" @click="resetSearch">重置</el-button>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-button type="success" icon="el-icon-plus" @click="openAddDialog">添加学生</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 学生表格 -->
    <el-card shadow="hover">
      <div slot="header">
        <span style="font-weight: bold; font-size: 16px">学生信息管理</span>
        <span style="float: right; color: #909399; font-size: 13px">共 {{ studentList.length }} 条记录</span>
      </div>
      <el-table :data="studentList" border v-loading="loading" stripe style="width: 100%">
        <el-table-column label="学号" prop="uid" width="120" />
        <el-table-column label="姓名" prop="name" width="100" />
        <el-table-column label="性别" prop="sex" width="80" align="center">
          <template slot-scope="scope">
            <el-tag :type="scope.row.sex === '男' ? '' : 'danger'" size="mini">
              {{ scope.row.sex || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="年龄" prop="age" width="80" align="center" />
        <el-table-column label="身高(cm)" prop="height" width="100" align="center" />
        <el-table-column label="体重(kg)" prop="weight" width="100" align="center" />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template slot-scope="scope">
            <el-button type="text" icon="el-icon-edit" @click="openEditDialog(scope.row)">编辑</el-button>
            <el-button type="text" icon="el-icon-delete" style="color: #f56c6c" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
        <template slot="empty">
          <div style="padding: 30px; color: #909399">
            <i class="el-icon-user" style="font-size: 40px"></i>
            <p style="margin-top: 10px">暂无学生数据</p>
          </div>
        </template>
      </el-table>
    </el-card>

    <!-- 添加/编辑学生弹窗 -->
    <el-dialog
      :title="dialogMode === 'add' ? '添加学生' : '编辑学生'"
      :visible.sync="dialogVisible"
      width="500px"
      :close-on-click-modal="false"
      @close="resetForm"
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="学号" prop="uid">
          <el-input v-model="form.uid" placeholder="请输入学号" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="性别" prop="sex">
          <el-radio-group v-model="form.sex">
            <el-radio label="男">男</el-radio>
            <el-radio label="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年龄" prop="age">
          <el-input v-model="form.age" placeholder="请输入年龄" />
        </el-form-item>
        <el-form-item label="身高(cm)" prop="height">
          <el-input v-model="form.height" placeholder="请输入身高" />
        </el-form-item>
        <el-form-item label="体重(kg)" prop="weight">
          <el-input v-model="form.weight" placeholder="请输入体重" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'add'" label="默认密码">
          <span style="color: #909399">123456（学生登录后可自行修改）</span>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitForm">确 定</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import request from '@/api/request'

export default {
  name: 'StudentManage',
  data() {
    return {
      studentList: [],
      loading: false,
      keyword: '',
      dialogVisible: false,
      dialogMode: 'add',
      submitLoading: false,
      editId: null,
      form: {
        uid: '',
        name: '',
        sex: '男',
        age: '',
        height: '',
        weight: ''
      },
      formRules: {
        uid: [{ required: true, message: '请输入学号', trigger: 'blur' }],
        name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
        sex: [{ required: true, message: '请选择性别', trigger: 'change' }]
      }
    }
  },
  mounted() {
    this.getStudentList()
  },
  methods: {
    /** 获取学生列表（支持keyword模糊搜索） */
    async getStudentList() {
      this.loading = true
      try {
        const params = this.keyword ? { keyword: this.keyword } : {}
        const res = await request.get('/student/all', { params })
        if (res.code === 200 && res.data) {
          this.studentList = res.data
        }
      } catch (err) {
        this.$message.error('学生数据加载失败')
      } finally {
        this.loading = false
      }
    },

    /** 搜索 */
    searchStudent() {
      this.getStudentList()
    },

    /** 重置搜索 */
    resetSearch() {
      this.keyword = ''
      this.getStudentList()
    },

    /** 打开添加弹窗 */
    openAddDialog() {
      this.dialogMode = 'add'
      this.editId = null
      this.form = { uid: '', name: '', sex: '男', age: '', height: '', weight: '' }
      this.dialogVisible = true
    },

    /** 打开编辑弹窗（预填数据，学号不可修改） */
    openEditDialog(row) {
      this.dialogMode = 'edit'
      this.editId = row.id
      this.form = {
        uid: row.uid || '',
        name: row.name || '',
        sex: row.sex || '男',
        age: row.age || '',
        height: row.height || '',
        weight: row.weight || ''
      }
      this.dialogVisible = true
    },

    /** 提交表单 */
    submitForm() {
      this.$refs.formRef.validate(async (valid) => {
        if (!valid) return
        this.submitLoading = true
        try {
          let res
          if (this.dialogMode === 'add') {
            res = await request.post('/student/add', this.form)
          } else {
            res = await request.put('/student/update', {
              id: this.editId,
              name: this.form.name,
              sex: this.form.sex,
              age: this.form.age,
              height: this.form.height,
              weight: this.form.weight
            })
          }
          if (res.code === 200) {
            this.$message.success(res.msg)
            this.dialogVisible = false
            this.getStudentList()
          } else {
            this.$message.error(res.msg || '操作失败')
          }
        } catch (err) {
          if (err.response && err.response.status === 401) {
            this.$message.error('登录已过期，请重新登录')
            this.$router.push('/login')
          } else {
            this.$message.error('操作失败，请检查后端服务')
          }
        } finally {
          this.submitLoading = false
        }
      })
    },

    /** 删除学生（确认弹窗） */
    handleDelete(row) {
      this.$confirm(`确定要删除学生「${row.name}」(${row.uid})吗？删除后该学生的训练记录也将一并清除。`, '删除确认', {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const res = await request.delete('/student/delete', { data: { id: row.id } })
          if (res.code === 200) {
            this.$message.success('删除成功')
            this.getStudentList()
          } else {
            this.$message.error(res.msg || '删除失败')
          }
        } catch (err) {
          this.$message.error('删除失败，请检查后端服务')
        }
      }).catch(() => {})
    },

    /** 重置表单 */
    resetForm() {
      if (this.$refs.formRef) {
        this.$refs.formRef.resetFields()
      }
    }
  }
}
</script>
