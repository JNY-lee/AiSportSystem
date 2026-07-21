import axios from 'axios'
const service = axios.create({
    baseURL: 'http://127.0.0.1:5000/api', // 全局只加一次/api
    timeout: 10000,
    withCredentials: true
})

// 请求拦截器：自动带上token
service.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
}, err => Promise.reject(err))

// 响应拦截器：401自动跳登录
service.interceptors.response.use(res => res.data, err => {
    if (err.response && err.response.status === 401) {
        localStorage.clear()
        location.href = '/login'
    }
    return Promise.reject(err)
})

export default service