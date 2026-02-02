// 侧边栏主逻辑（与popup.js相同，但适配侧边栏）
let dataCollector;
let spreadAnalyzer;
let updateInterval;

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
  dataCollector = new DataCollector();
  spreadAnalyzer = new SpreadAnalyzer();
  
  // 加载历史数据
  await spreadAnalyzer.loadHistory();
  
  // 绑定事件
  document.getElementById('refreshBtn').addEventListener('click', () => {
    // 手动刷新时显示连接中
    updateStatus('连接中...', 'loading');
    refreshData();
  });
  document.getElementById('optionsBtn').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
  
  // 初始加载
  updateStatus('连接中...', 'loading');
  await refreshData();
  
  // 设置自动刷新
  updateInterval = setInterval(refreshData, CONFIG.MONITOR_CONFIG.update_interval * 1000);
});

// 刷新数据
async function refreshData() {
  // 只在首次加载或出错后恢复时显示"连接中"
  const currentStatus = document.getElementById('statusText').textContent;
  if (currentStatus === '连接失败' || currentStatus === '连接中...') {
    updateStatus('连接中...', 'loading');
  }
  
  try {
    // 获取价格数据
    const prices = await dataCollector.fetchAllPrices();
    
    // 更新价格表格
    updatePriceTable(prices);
    
    // 更新价差表格
    updateSpreadTable(prices);
    
    // 更新信号表格
    updateSignalTable(prices);
    
    // 保存历史数据
    await spreadAnalyzer.saveHistory();
    
    // 更新状态（只在首次成功或从错误恢复时更新）
    if (currentStatus !== '已连接') {
      updateStatus('已连接', 'active');
    }
    updateLastUpdate();
    
  } catch (error) {
    console.error('刷新数据失败:', error);
    updateStatus('连接失败', 'error');
  }
}

// 更新状态
function updateStatus(text, type) {
  const statusText = document.getElementById('statusText');
  const statusDot = document.getElementById('statusDot');
  
  statusText.textContent = text;
  statusDot.className = 'status-dot ' + type;
}

// 更新最后更新时间
function updateLastUpdate() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('zh-CN');
  document.getElementById('lastUpdate').textContent = `最后更新: ${timeStr}`;
}

// 更新价格表格
function updatePriceTable(prices) {
  const tbody = document.getElementById('priceTableBody');
  tbody.innerHTML = '';
  
  const symbols = CONFIG.MONITOR_CONFIG.symbols;
  const dexes = CONFIG.MONITOR_CONFIG.dexes;
  
  for (const symbol of symbols) {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${symbol}</td>`;
    
    for (const dex of dexes) {
      const dexData = prices[symbol] && prices[symbol][dex];
      if (dexData) {
        row.innerHTML += `<td>${dexData.price.toFixed(2)}</td>`;
      } else {
        row.innerHTML += `<td class="signal-error">N/A</td>`;
      }
    }
    
    tbody.appendChild(row);
  }
}

// 更新价差表格
function updateSpreadTable(prices) {
  const tbody = document.getElementById('spreadTableBody');
  tbody.innerHTML = '';
  
  const dexPairs = [
    ['01.xyz', 'nado'],
    ['01.xyz', 'variational'],
    ['nado', 'variational'],
  ];
  
  const symbols = CONFIG.MONITOR_CONFIG.symbols;
  
  for (const [dex1, dex2] of dexPairs) {
    for (const symbol of symbols) {
      const price1Data = prices[symbol] && prices[symbol][dex1];
      const price2Data = prices[symbol] && prices[symbol][dex2];
      
      if (!price1Data || !price2Data) {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${dex1} vs ${dex2}</td>
          <td>${symbol}</td>
          <td colspan="3" class="signal-error">数据缺失</td>
        `;
        tbody.appendChild(row);
        continue;
      }
      
      const price1 = price1Data.price;
      const price2 = price2Data.price;
      
      const analysis = spreadAnalyzer.analyzeSpreadOpportunity(dex1, dex2, symbol, price1, price2);
      
      const spread = analysis.spread;
      const spreadPct = analysis.spread_percentage;
      const convergence = analysis.convergence;
      
      let statusClass = 'spread-normal';
      let statusText = '正常';
      
      if (convergence) {
        if (spread > convergence.upper) {
          statusClass = 'spread-danger';
          statusText = '超出区间';
        }
      }
      
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${dex1} vs ${dex2}</td>
        <td>${symbol}</td>
        <td>${spread.toFixed(4)}</td>
        <td>${(spreadPct * 100).toFixed(4)}%</td>
        <td class="${statusClass}">${statusText}</td>
      `;
      tbody.appendChild(row);
    }
  }
}

// 更新信号表格
function updateSignalTable(prices) {
  const tbody = document.getElementById('signalTableBody');
  tbody.innerHTML = '';
  
  const dexPairs = [
    ['01.xyz', 'nado'],
    ['01.xyz', 'variational'],
    ['nado', 'variational'],
  ];
  
  const symbols = CONFIG.MONITOR_CONFIG.symbols;
  
  for (const [dex1, dex2] of dexPairs) {
    for (const symbol of symbols) {
      const price1Data = prices[symbol] && prices[symbol][dex1];
      const price2Data = prices[symbol] && prices[symbol][dex2];
      
      if (!price1Data || !price2Data) {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${dex1} vs ${dex2}</td>
          <td>${symbol}</td>
          <td class="signal-none">无信号</td>
          <td class="signal-error">数据缺失</td>
          <td>-</td>
        `;
        tbody.appendChild(row);
        continue;
      }
      
      const price1 = price1Data.price;
      const price2 = price2Data.price;
      
      const opportunity = spreadAnalyzer.checkArbitrageOpportunity(
        dex1, dex2, symbol, price1, price2, 1000, true
      );
      
      const signal = opportunity.signal;
      
      if (signal) {
        const action = signal.action;
        let row;
        
        if (action === 'OPEN') {
          // 开仓信号
          row = document.createElement('tr');
          row.innerHTML = `
            <td>${dex1} vs ${dex2}</td>
            <td>${symbol}</td>
            <td class="signal-open">开仓</td>
            <td class="operation">
              <div class="operation-high">${signal.high_dex} 做空 @ ${signal.high_price.toFixed(2)}</div>
              <div class="operation-low">${signal.low_dex} 做多 @ ${signal.low_price.toFixed(2)}</div>
            </td>
            <td>${opportunity.net_profit.toFixed(4)}</td>
          `;
        } else if (action === 'CLOSE') {
          // 平仓信号
          let reason;
          if (signal.close_threshold !== undefined) {
            reason = `价差已收敛 (当前:${signal.current_spread.toFixed(4)} <= 阈值:${signal.close_threshold.toFixed(4)})`;
          } else {
            reason = signal.reason || '价差收敛';
          }
          
          row = document.createElement('tr');
          row.innerHTML = `
            <td>${dex1} vs ${dex2}</td>
            <td>${symbol}</td>
            <td class="signal-close">平仓</td>
            <td class="operation">
              <div class="operation-high">${signal.high_dex} 平多 @ ${price1Data.price.toFixed(2)}</div>
              <div class="operation-low">${signal.low_dex} 平空 @ ${price2Data.price.toFixed(2)}</div>
              <div style="font-size: 10px; color: #888; margin-top: 4px;">原因: ${reason}</div>
            </td>
            <td>${signal.current_spread.toFixed(4)}</td>
          `;
        }
        
        if (row) {
          tbody.appendChild(row);
        }
      } else {
        const debug = opportunity.debug_info || {};
        const reasons = [];
        
        if (!opportunity.is_profitable) {
          reasons.push(`成本过高(成本:${opportunity.total_cost.toFixed(4)}, 预期利润:${opportunity.expected_profit.toFixed(4)})`);
        }
        if (!opportunity.within_threshold) {
          const spreadPct = opportunity.spread_percentage;
          const minTh = CONFIG.SPREAD_CONFIG.min_spread_threshold;
          const maxTh = CONFIG.SPREAD_CONFIG.max_spread_threshold;
          if (spreadPct < minTh) {
            reasons.push(`价差过小(${(spreadPct * 100).toFixed(4)}% < ${(minTh * 100).toFixed(4)}%)`);
          } else {
            reasons.push(`价差过大(${(spreadPct * 100).toFixed(4)}% > ${(maxTh * 100).toFixed(4)}%)`);
          }
        }
        if (!opportunity.beyond_convergence && debug.has_convergence) {
          reasons.push(`未超出收敛区间(当前:${opportunity.spread.toFixed(4)}, 上界:${debug.convergence_upper?.toFixed(4) || 0})`);
        }
        
        if (reasons.length === 0) {
          if (debug.has_convergence) {
            reasons.push('价差在正常范围内');
          } else {
            reasons.push('等待历史数据积累');
          }
        }
        
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${dex1} vs ${dex2}</td>
          <td>${symbol}</td>
          <td class="signal-none">无信号</td>
          <td class="signal-none">${reasons.slice(0, 2).join('; ')}</td>
          <td>${(opportunity.spread_percentage * 100).toFixed(4)}%</td>
        `;
        tbody.appendChild(row);
      }
    }
  }
}

// 清理
window.addEventListener('beforeunload', () => {
  if (updateInterval) {
    clearInterval(updateInterval);
  }
});
