Page({
  data: {
    content: ''
  },

  onContentInput(e) {
    this.setData({
      content: e.detail.value.trim()
    });
  },

  submitContent() {
    // 保存内容到全局
    getApp().globalData.checkContent = this.data.content;
    // 跳转到加载页
    tt.navigateTo({
      url: '/pages/loading/loading'
    });
  }
});