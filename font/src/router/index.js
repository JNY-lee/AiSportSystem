import Vue from 'vue'
import VueRouter from 'vue-router'
Vue.use(VueRouter)
const routes = [
    {
        path: '/',
        redirect: '/login'
    },
    {
        path: '/login',
        component: () => import('@/components/login.vue')
    },
    {
        path: '/student',
        component: () => import('@/components/layout/layout.vue'),
        meta: { role: 'student' },
        children: [
            { path: 'video', component: () => import('@/components/student/VideoManage.vue') },
            { path: 'score', component: () => import('@/components/student/HistoryScore.vue') },
            { path: 'report', component: () => import('@/components/student/TrainReport.vue') },
            { path: 'ai', component: () => import('@/components/student/AIAssistant.vue') },
            { path: 'message', component: () => import('@/components/student/MessageBoard.vue') }
        ]
    },
    {
        path: '/teacher',
        component: () => import('@/components/layout/layout.vue'),
        meta: { role: 'teacher' },
        children: [
            { path: 'student', component: () => import('@/components/teacher/StudentManage.vue') },
            { path: 'video', component: () => import('@/components/teacher/VideoAll.vue') },
            { path: 'report', component: () => import('@/components/teacher/ScoreReport.vue') },
            { path: 'message', component: () => import('@/components/teacher/MessageManage.vue') }
        ]
    }
]
const router = new VueRouter({
    mode: 'history',
    routes
})
router.beforeEach((to, from, next) => {
    const user = localStorage.getItem("userInfo")
    if (to.path === '/login') return next()
    if (!user) return next('/login')
    const userInfo = JSON.parse(user)
    // 本地身份与页面权限不匹配，清除缓存跳转登录
    if (to.meta.role && to.meta.role !== userInfo.type) {
        localStorage.removeItem("userInfo")
        return next('/login')
    }
    next()
})
export default router