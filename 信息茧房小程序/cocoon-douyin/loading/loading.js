Page({
  onShow() {
    // 获取全局的检测内容
    const content = getApp().globalData.checkContent;
    // 调用后端接口（抖音用tt.request替换wx.request）
    tt.request({
      url: 'https://你的后端域名/api/check-cocoon', // 替换成你的后端HTTPS地址
      method: 'POST',
      data: {
        content: content
      },
      success: (res) => {
        // 保存结果到全局
        getApp().globalData.checkResult = res.data;
        // 跳转到结果页
        tt.redirectTo({
          url: '/pages/result/result'
        });
      },
      fail: (err) => {
        tt.showToast({
          title: '检测失败，请重试',
          icon: 'none'
        });
        // 返回上一页
        tt.navigateBack();
      }
    });
  }
});