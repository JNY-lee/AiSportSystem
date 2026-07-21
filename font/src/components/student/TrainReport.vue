<template>
  <div>
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <h3>平均训练分数</h3>
          <p style="font-size:24px;color:#409EFF">{{ report.avg_total_score }}</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <h3>总训练次数</h3>
          <p style="font-size:24px;color:#67C23A">{{ report.total_train_times }}</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <h3>上传视频总数</h3>
          <p style="font-size:24px;color:#E6A23C">{{ report.upload_video_num }}</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- ECharts 图表区域 -->
    <el-row :gutter="20" style="margin-top:20px">
      <!-- 近7个训练平均分折线图 -->
      <el-col :span="12">
        <el-card>
          <div slot="header"><span style="font-weight:bold">近7次训练平均分趋势</span></div>
          <div ref="lineChart" style="width:100%;height:350px"></div>
        </el-card>
      </el-col>
      <!-- 各类运动次数饼图 -->
      <el-col :span="12">
        <el-card>
          <div slot="header"><span style="font-weight:bold">各类运动训练次数占比</span></div>
          <div ref="pieChart" style="width:100%;height:350px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import request from '@/api/request'
import * as echarts from 'echarts'

export default {
  data() {
    return {
      report: {
        avg_total_score: 0,
        total_train_times: 0,
        upload_video_num: 0
      },
      videoList: [],
      userInfo: JSON.parse(localStorage.getItem('userInfo') || '{}')
    }
  },
  mounted() {
    this.fetchReport()
    this.fetchVideoList()
  },
  beforeDestroy() {
    if (this.lineChartInstance) this.lineChartInstance.dispose()
    if (this.pieChartInstance) this.pieChartInstance.dispose()
  },
  methods: {
    async fetchReport() {
      try {
        const res = await request.get('/report/my', { params: { uid: this.userInfo.uid } })
        if (res.code === 200) this.report = res.data
      } catch (err) {
        console.error('获取报告失败:', err)
      }
    },

    async fetchVideoList() {
      try {
        const res = await request.get('/video/my')
        if (res.code === 200 && res.data) {
          this.videoList = res.data || []
          this.$nextTick(() => {
            this.drawLineChart()
            this.drawPieChart()
          })
        }
      } catch (err) {
        console.error('获取视频列表失败:', err)
      }
    },

    /** 近7个训练平均分折线图 */
    drawLineChart() {
      if (!this.$refs.lineChart) return
      this.lineChartInstance = echarts.init(this.$refs.lineChart)

      // 按时间倒序，取最新7条
      const sorted = [...this.videoList].reverse().slice(0, 7).reverse()
      const xData = sorted.map(v => this.formatTime(v.upload_time))
      const yData = sorted.map(v => parseFloat(v.avg_score) || 0)

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: '{b}<br/>平均分: <b>{c}</b>'
        },
        grid: { left: 50, right: 20, top: 30, bottom: 40 },
        xAxis: {
          type: 'category',
          data: xData,
          axisLabel: { rotate: 30, fontSize: 11 }
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 100,
          name: '分数'
        },
        series: [{
          name: '平均分',
          type: 'line',
          data: yData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { color: '#409EFF', width: 3 },
          itemStyle: { color: '#409EFF' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(64,158,255,0.3)' },
              { offset: 1, color: 'rgba(64,158,255,0.05)' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            fontSize: 11,
            formatter: '{c}'
          }
        }]
      }
      this.lineChartInstance.setOption(option)
    },

    /** 各类运动次数饼图 */
    drawPieChart() {
      if (!this.$refs.pieChart) return
      this.pieChartInstance = echarts.init(this.$refs.pieChart)

      // 统计各运动类型次数
      const typeCount = {}
      this.videoList.forEach(v => {
        const t = v.action_type || 'unknown'
        typeCount[t] = (typeCount[t] || 0) + (parseInt(v.repeat_count) || 0)
      })

      const pieData = Object.entries(typeCount).map(([name, value]) => ({ name, value }))
      // 运动类型颜色映射
      const colorMap = { 'push-up': '#F56C6C', 'squat': '#E6A23C', 'pullUp': '#67C23A' }
      const colors = pieData.map(d => colorMap[d.name] || '#909399')

      // 中文名映射
      const nameMap = { 'push-up': '俯卧撑', 'squat': '深蹲', 'pullUp': '引体向上', 'unknown': '未识别' }
      const pieDataCn = pieData.map(d => ({ name: nameMap[d.name] || d.name, value: d.value }))

      const option = {
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c}次 ({d}%)'
        },
        legend: {
          bottom: 10,
          left: 'center'
        },
        color: colors,
        series: [{
          type: 'pie',
          radius: ['35%', '60%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: {
            show: true,
            formatter: '{b}\n{c}次',
            fontSize: 12
          },
          emphasis: {
            label: { show: true, fontSize: 14, fontWeight: 'bold' },
            itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.3)' }
          },
          data: pieDataCn.length > 0 ? pieDataCn : [{ name: '暂无数据', value: 0 }]
        }]
      }
      this.pieChartInstance.setOption(option)
    },

    /** 格式化时间：MM-DD HH:mm */
    formatTime(t) {
      if (!t) return '--'
      try {
        const d = new Date(t)
        const m = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        const h = String(d.getHours()).padStart(2, '0')
        const min = String(d.getMinutes()).padStart(2, '0')
        return `${m}-${day} ${h}:${min}`
      } catch (e) {
        return String(t).slice(0, 16)
      }
    }
  }
}
</script>
