class SpreadAnalyzer {
  constructor() {
    this.spreadHistory = {};
    this.priceHistory = {};
  }


  async loadHistory() {
    try {
      const result = await chrome.storage.local.get(['spreadHistory', 'priceHistory']);
      if (result.spreadHistory) {
        this.spreadHistory = result.spreadHistory;
      }
      if (result.priceHistory) {
        this.priceHistory = result.priceHistory;
      }
      console.log('历史数据已加载');
    } catch (error) {
      console.error('加载历史数据失败:', error);
    }
  }

 
  async saveHistory() {
    try {
      await chrome.storage.local.set({
        spreadHistory: this.spreadHistory,
        priceHistory: this.priceHistory,
      });
    } catch (error) {
      console.error('保存历史数据失败:', error);
    }
  }

  /**
   * 计算价差（绝对值）
   * @param {number} price1
   * @param {number} price2
   * @returns {number}
   */
  calculateSpread(price1, price2) {
    return Math.abs(price1 - price2);
  }

  /**
   * 计算价差百分比
   * @param {number} price1
   * @param {number} price2
   * @returns {number}
   */
  calculateSpreadPercentage(price1, price2) {
    const minPrice = Math.min(price1, price2);
    if (minPrice === 0) return 0;
    return Math.abs(price1 - price2) / minPrice;
  }

  /**
   * 更新价差历史数据
   * @param {string} dex1
   * @param {string} dex2
   * @param {string} symbol
   * @param {number} spread
   */
  updateSpreadHistory(dex1, dex2, symbol, spread) {
    const key = `${dex1}|${dex2}|${symbol}`;
    if (!this.spreadHistory[key]) {
      this.spreadHistory[key] = [];
    }
    this.spreadHistory[key].push(spread);

    // 只保留最近24小时的数据
    const maxHistory = CONFIG.SPREAD_CONFIG.convergence_window_hours * 3600;
    if (this.spreadHistory[key].length > maxHistory) {
      this.spreadHistory[key] = this.spreadHistory[key].slice(-maxHistory);
    }
  }

  /**
   * 计算价差收敛区间
   * @param {string} dex1
   * @param {string} dex2
   * @param {string} symbol
   * @returns {Object|null} {mean, std, lower, upper, count}
   */
  calculateConvergenceRange(dex1, dex2, symbol) {
    const key = `${dex1}|${dex2}|${symbol}`;
    const history = this.spreadHistory[key] || [];

    if (history.length < 10) {
      return null;
    }

    const mean = history.reduce((sum, val) => sum + val, 0) / history.length;
    const variance = history.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / history.length;
    const std = Math.sqrt(variance);

    return {
      mean: mean,
      std: std,
      lower: mean - 2 * std,
      upper: mean + 2 * std,
      count: history.length,
    };
  }

  /**
   * 分析价差套利机会
   * @param {string} dex1
   * @param {string} dex2
   * @param {string} symbol
   * @param {number} price1 - DEX1价格
   * @param {number} price2 - DEX2价格
   * @returns {Object} 分析结果
   */
  analyzeSpreadOpportunity(dex1, dex2, symbol, price1, price2) {
    // 计算价差
    const spread = this.calculateSpread(price1, price2);
    const spreadPct = this.calculateSpreadPercentage(price1, price2);

    // 更新历史数据
    this.updateSpreadHistory(dex1, dex2, symbol, spread);

    // 计算收敛区间
    const convergence = this.calculateConvergenceRange(dex1, dex2, symbol);

    // 判断价差方向
    let highDex, lowDex, highPrice, lowPrice;
    if (price1 > price2) {
      highDex = dex1;
      lowDex = dex2;
      highPrice = price1;
      lowPrice = price2;
    } else {
      highDex = dex2;
      lowDex = dex1;
      highPrice = price2;
      lowPrice = price1;
    }

    return {
      dex1,
      dex2,
      symbol,
      price1,
      price2,
      spread,
      spread_percentage: spreadPct,
      high_dex: highDex,
      low_dex: lowDex,
      high_price: highPrice,
      low_price: lowPrice,
      convergence,
    };
  }

  /**
   * 计算交易成本
   * @param {string} dex1
   * @param {string} dex2
   * @param {number} amount - 交易金额
   * @param {boolean} useMaker - 是否使用maker订单
   * @returns {number} 总手续费（开仓+平仓）
   */
  calculateTradingCost(dex1, dex2, amount, useMaker = true) {
    const feeType = useMaker ? 'maker' : 'taker';

    const fee1 = CONFIG.DEX_CONFIG[dex1].fees[feeType] * amount;
    const fee2 = CONFIG.DEX_CONFIG[dex2].fees[feeType] * amount;

    // 开仓和平仓都需要手续费
    return (fee1 + fee2) * 2;
  }

  /**
   * 检查套利机会
   * @param {string} dex1
   * @param {string} dex2
   * @param {string} symbol
   * @param {number} price1
   * @param {number} price2
   * @param {number} amount - 交易金额
   * @param {boolean} useMaker
   * @returns {Object} 套利机会分析结果
   */
  checkArbitrageOpportunity(dex1, dex2, symbol, price1, price2, amount = 1000, useMaker = true) {
    // 分析价差
    const spreadAnalysis = this.analyzeSpreadOpportunity(dex1, dex2, symbol, price1, price2);

    // 计算交易成本
    const totalCost = this.calculateTradingCost(dex1, dex2, amount, useMaker);

    // 计算预期价差利润
    const convergence = spreadAnalysis.convergence;
    const spreadPct = spreadAnalysis.spread_percentage;
    const minPrice = Math.min(price1, price2);

    let expectedProfit;
    if (convergence) {
      const meanSpreadPct = minPrice > 0 ? convergence.mean / minPrice : 0;
      const expectedSpreadPct = spreadPct - meanSpreadPct;
      expectedProfit = expectedSpreadPct * amount;
    } else {
      // 没有历史数据，保守估计
      expectedProfit = spreadPct * amount * 0.5;
    }

    // 判断是否有利可图
    const netProfit = expectedProfit - totalCost;
    const isProfitable = netProfit > 0;

    // 判断是否在阈值范围内
    const minThreshold = CONFIG.SPREAD_CONFIG.min_spread_threshold;
    const maxThreshold = CONFIG.SPREAD_CONFIG.max_spread_threshold;
    const withinThreshold = minThreshold <= spreadPct && spreadPct <= maxThreshold;

    // 判断是否超出收敛区间
    let beyondConvergence = false;
    if (convergence) {
      beyondConvergence = spreadAnalysis.spread > convergence.upper;
    } else {
      beyondConvergence = spreadPct >= minThreshold;
    }

    const result = {
      ...spreadAnalysis,
      amount,
      total_cost: totalCost,
      expected_profit: expectedProfit,
      net_profit: netProfit,
      is_profitable: isProfitable,
      within_threshold: withinThreshold,
      beyond_convergence: beyondConvergence,
      signal: this._generateSignal(
        spreadAnalysis,
        isProfitable,
        withinThreshold,
        beyondConvergence,
        convergence !== null
      ),
      debug_info: {
        has_convergence: convergence !== null,
        convergence_mean: convergence ? convergence.mean : null,
        convergence_upper: convergence ? convergence.upper : null,
        current_spread: spreadAnalysis.spread,
        spread_pct: spreadPct,
      },
    };

    return result;
  }

  /**
   * 生成交易信号
   * @param {Object} spreadAnalysis - 价差分析结果
   * @param {boolean} isProfitable
   * @param {boolean} withinThreshold
   * @param {boolean} beyondConvergence
   * @param {boolean} hasConvergenceData
   * @returns {Object|null} 交易信号
   */
  _generateSignal(spreadAnalysis, isProfitable, withinThreshold, beyondConvergence, hasConvergenceData = false) {
    const convergence = spreadAnalysis.convergence;
    const currentSpread = spreadAnalysis.spread;

    if (convergence) {
      const meanSpread = convergence.mean;
      const upperSpread = convergence.upper;

      // 开仓阈值
      const openThreshold = upperSpread * CONFIG.SPREAD_CONFIG.open_spread_multiplier;

      // 平仓阈值
      const closeThreshold = meanSpread * CONFIG.SPREAD_CONFIG.close_spread_multiplier;

      // 平仓信号
      if (currentSpread <= closeThreshold) {
        return {
          action: 'CLOSE',
          high_dex: spreadAnalysis.high_dex,
          high_side: 'LONG',
          low_dex: spreadAnalysis.low_dex,
          low_side: 'SHORT',
          current_spread: currentSpread,
          close_threshold: closeThreshold,
          convergence_mean: meanSpread,
        };
      }

      // 开仓信号
      if (currentSpread >= openThreshold && isProfitable && withinThreshold) {
        return {
          action: 'OPEN',
          high_dex: spreadAnalysis.high_dex,
          high_side: 'SHORT',
          high_price: spreadAnalysis.high_price,
          low_dex: spreadAnalysis.low_dex,
          low_side: 'LONG',
          low_price: spreadAnalysis.low_price,
          spread: currentSpread,
          spread_percentage: spreadAnalysis.spread_percentage,
          open_threshold: openThreshold,
        };
      }
    } else {
      // 没有收敛区间数据
      const spreadPct = spreadAnalysis.spread_percentage;
      const minThreshold = CONFIG.SPREAD_CONFIG.min_spread_threshold;
      const maxThreshold = CONFIG.SPREAD_CONFIG.max_spread_threshold;

      // 平仓信号
      if (spreadPct < minThreshold) {
        return {
          action: 'CLOSE',
          high_dex: spreadAnalysis.high_dex,
          high_side: 'LONG',
          low_dex: spreadAnalysis.low_dex,
          low_side: 'SHORT',
          current_spread: currentSpread,
          reason: '价差过小',
        };
      }

      // 开仓信号
      if (minThreshold <= spreadPct && spreadPct <= maxThreshold && isProfitable) {
        return {
          action: 'OPEN',
          high_dex: spreadAnalysis.high_dex,
          high_side: 'SHORT',
          high_price: spreadAnalysis.high_price,
          low_dex: spreadAnalysis.low_dex,
          low_side: 'LONG',
          low_price: spreadAnalysis.low_price,
          spread: currentSpread,
          spread_percentage: spreadPct,
        };
      }
    }

    return null;
  }
}
