Page({
  data: {
    result: {}
  },

  onLoad() {
    // 获取全局的检测结果
    const result = getApp().globalData.checkResult;
    this.setData({
      result: result
    });
  },

  // 重新检测
  recheck() {
    tt.redirectTo({
      url: '/pages/check/check'
    });
  },

  // 生成分享图（抖音版）
  share() {
    tt.showToast({
      title: '分享图生成中...',
      icon: 'loading'
    });
    // 抖音分享逻辑：生成海报+调起分享
    setTimeout(() => {
      tt.showShareMenu({
        withShareTicket: true
      });
      tt.showToast({
        title: '可分享到抖音好友/动态',
        icon: 'success'
      });
    }, 1000);
  },

  // 抖音分享到好友
  onShareAppMessage() {
    return {
      title: '我测了我的信息茧房指数，快来看看你的！',
      path: '/pages/index/index'
    };
  },

  // 抖音分享到动态
  onShareTimeline() {
    return {
      title: '原来我真的有信息茧房…太准了！'
    };
  }
});