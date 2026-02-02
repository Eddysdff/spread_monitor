// 设置页面逻辑
document.addEventListener('DOMContentLoaded', async () => {
  // 加载保存的设置
  const result = await chrome.storage.local.get(['updateInterval', 'minSpreadThreshold', 'maxSpreadThreshold']);
  
  if (result.updateInterval) {
    document.getElementById('updateInterval').value = result.updateInterval;
  }
  if (result.minSpreadThreshold) {
    document.getElementById('minSpreadThreshold').value = result.minSpreadThreshold;
  }
  if (result.maxSpreadThreshold) {
    document.getElementById('maxSpreadThreshold').value = result.maxSpreadThreshold;
  }
  
  // 保存按钮事件
  document.getElementById('saveBtn').addEventListener('click', async () => {
    const updateInterval = parseFloat(document.getElementById('updateInterval').value);
    const minSpreadThreshold = parseFloat(document.getElementById('minSpreadThreshold').value) / 100;
    const maxSpreadThreshold = parseFloat(document.getElementById('maxSpreadThreshold').value) / 100;
    
    await chrome.storage.local.set({
      updateInterval,
      minSpreadThreshold,
      maxSpreadThreshold,
    });
    
    alert('设置已保存！');
  });
});
