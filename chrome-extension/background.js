// 后台服务脚本
let dataCollector;
let spreadAnalyzer;

// 初始化
chrome.runtime.onInstalled.addListener(() => {
  console.log('PerpDEX 套利监控插件已安装');
  initialize();
});

chrome.runtime.onStartup.addListener(() => {
  console.log('PerpDEX 套利监控插件已启动');
  initialize();
});

function initialize() {
  // 这里可以初始化数据采集器等
  // 由于service worker的限制，主要逻辑在sidepanel中
}

// 点击插件图标时打开侧边栏
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ windowId: tab.windowId });
});

// 定时任务：每分钟更新一次数据
chrome.alarms.create('updatePrices', {
  periodInMinutes: 1
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'updatePrices') {
    // 通知popup更新（如果打开的话）
    chrome.runtime.sendMessage({ type: 'priceUpdate' }).catch(() => {
      // popup可能没有打开，忽略错误
    });
  }
});

// 监听消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'getPrices') {
    // 返回价格数据
    // 这里可以从storage中读取
    chrome.storage.local.get('lastPrices', (result) => {
      sendResponse(result.lastPrices || null);
    });
    return true;  // 异步响应
  }
});

// 通知功能（当检测到信号时）
async function showNotification(signal) {
  try {
    await chrome.notifications.create({
      type: 'basic',
      iconUrl: chrome.runtime.getURL('assets/icons/icon48.png'),
      title: '套利信号',
      message: `${signal.symbol}: ${signal.high_dex} 做空, ${signal.low_dex} 做多`,
    });
  } catch (error) {
    console.error('显示通知失败:', error);
  }
}
