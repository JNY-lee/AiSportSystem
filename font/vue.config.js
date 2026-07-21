module.exports = {
  lintOnSave: false, // ✅ 顶层配置，和devServer同级
  devServer: {
    allowedHosts: "all"
    // 这里只保留devServer专属配置：port、proxy、open等
  }
}