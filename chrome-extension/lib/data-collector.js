class DataCollector {
  constructor() {
    this.priceCache = {};
  }

  /**
   * 获取所有DEX的所有币种价格
   * @returns {Object} {symbol: {dex: {price, orderbook}}}
   */
  async fetchAllPrices() {
    const results = {};
    const symbols = CONFIG.MONITOR_CONFIG.symbols;
    const dexes = CONFIG.MONITOR_CONFIG.dexes;

    for (const symbol of symbols) {
      results[symbol] = {};

      // 并行获取各DEX价格
      const promises = dexes.map(async (dex) => {
        try {
          const orderbook = await this.fetchOrderbook(dex, symbol);
          if (orderbook) {
            const midPrice = this.calculateMidPrice(orderbook);
            if (midPrice) {
              results[symbol][dex] = {
                price: midPrice,
                orderbook: orderbook,
              };
            }
          }
        } catch (error) {
          console.error(`获取价格失败: ${dex} - ${symbol}`, error);
        }
      });

      await Promise.all(promises);
    }

    return results;
  }

  /**
   * 获取订单簿数据
   * @param {string} dex 
   * @param {string} symbol 
   * @returns {Object|null} 
   */
  async fetchOrderbook(dex, symbol) {
    try {
      const dexConfig = CONFIG.DEX_CONFIG[dex];
      if (!dexConfig) {
        console.error(`DEX配置不存在: ${dex}`);
        return null;
      }

      if (dex === 'variational') {
        return await this._fetchVariationalOrderbook(symbol);
      }

      if (dex === 'nado') {
        return await this._fetchNadoOrderbook(symbol);
      }

      // 01.xyz
      const marketPath = dexConfig.markets[symbol];
      if (!marketPath) {
        console.error(`市场路径不存在: ${dex} - ${symbol}`);
        return null;
      }

      const url = dexConfig.base_url + marketPath;

      const response = await fetch(url, {
        method: 'GET',
        signal: AbortSignal.timeout(10000),
      });

      if (!response.ok) {
        console.error(`获取订单簿失败: ${dex} - ${symbol}, status=${response.status}`);
        return null;
      }

      const data = await response.json();
      return this._parseOrderbook(dex, symbol, data);
    } catch (error) {
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        console.warn(`请求超时: ${dex} - ${symbol}`);
      } else {
        console.error(`获取订单簿异常: ${dex} - ${symbol}`, error);
      }
      return null;
    }
  }

  /**
   * 获取Variational订单簿数据
   * 使用 quotes/simple API 端点
   * @param {string} symbol - 币种符号
   * @returns {Object|null} 标准化的订单簿数据
   */
  async _fetchVariationalOrderbook(symbol) {
    try {
      const dexConfig = CONFIG.DEX_CONFIG['variational'];
      const underlying = dexConfig.markets[symbol];
      if (!underlying) {
        console.error(`Variational市场映射不存在: ${symbol}`);
        return null;
      }

      const url = dexConfig.base_url + dexConfig.quotes_endpoint;
      const apiConfig = dexConfig.api_config;

      const payload = {
        instrument: {
          underlying: underlying,
          instrument_type: apiConfig.instrument_type || 'perpetual_future',
          settlement_asset: apiConfig.settlement_asset || 'USDC',
          funding_interval_s: apiConfig.funding_interval_s || 3600,
        },
        qty: apiConfig.quote_qty || '0.001',
      };

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': 'https://omni.variational.io',
          'Referer': 'https://omni.variational.io/markets',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10000),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`获取Variational数据失败: ${symbol}, status=${response.status}, error=${errorText.substring(0, 200)}`);
        return null;
      }

      let data = await response.json();

      // 处理返回数据
      if (Array.isArray(data) && data.length > 0) {
        data = data[0];
      }

      const bidPrice = parseFloat(data.bid || 0);
      const askPrice = parseFloat(data.ask || 0);

      if (bidPrice === 0 || askPrice === 0) {
        console.warn(`Variational报价无效: ${symbol}, bid=${bidPrice}, ask=${askPrice}`);
        return null;
      }

      const midPrice = (bidPrice + askPrice) / 2;

      return {
        dex: 'variational',
        symbol: symbol,
        bids: [[bidPrice, 1.0]],
        asks: [[askPrice, 1.0]],
        timestamp: new Date().toISOString(),
        mark_price: midPrice,
        quote_qty: apiConfig.quote_qty || '0.001',
      };
    } catch (error) {
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        console.warn(`Variational请求超时: ${symbol}`);
      } else {
        console.error(`获取Variational订单簿异常: ${symbol}`, error);
      }
      return null;
    }
  }

  /**
   * 获取Nado订单簿数据
   * REST API: GET /v2/orderbook?ticker_id={ticker_id}&depth={depth}
   * @param {string} symbol - 币种符号
   * @returns {Object|null} 标准化的订单簿数据
   */
  async _fetchNadoOrderbook(symbol) {
    try {
      const dexConfig = CONFIG.DEX_CONFIG['nado'];
      if (!dexConfig) {
        console.error('Nado配置不存在');
        return null;
      }

      const tickerId = dexConfig.markets[symbol];
      if (!tickerId) {
        console.error(`Nado市场映射不存在: ${symbol}`);
        return null;
      }

      const baseUrl = dexConfig.base_url;
      const endpoint = dexConfig.gateway_v2_endpoint;
      const depth = (dexConfig.api_config && dexConfig.api_config.params && dexConfig.api_config.params.depth) || 20;

      const url = `${baseUrl}${endpoint}?ticker_id=${encodeURIComponent(tickerId)}&depth=${depth}`;

      const response = await fetch(url, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`获取Nado订单簿失败: ${symbol}, status=${response.status}, error=${errorText.substring(0, 200)}`);
        return null;
      }

      const data = await response.json();
      return this._parseNadoOrderbook(symbol, data);
    } catch (error) {
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        console.warn(`Nado请求超时: ${symbol}`);
      } else {
        console.error(`获取Nado订单簿异常: ${symbol}`, error);
      }
      return null;
    }
  }

  /**
   * 解析Nado订单簿数据
   * @param {string} symbol - 币种符号
   * @param {Object} data - API返回的原始数据
   * @returns {Object|null} 标准化的订单簿数据
   */
  _parseNadoOrderbook(symbol, data) {
    try {
      if (!data.bids || !data.asks) {
        console.warn(`Nado订单簿格式异常: ${symbol}, keys: ${Object.keys(data).join(', ')}`);
        return null;
      }

      const bids = data.bids
        .filter(bid => bid.length >= 2)
        .map(bid => [parseFloat(bid[0]), parseFloat(bid[1])]);
      const asks = data.asks
        .filter(ask => ask.length >= 2)
        .map(ask => [parseFloat(ask[0]), parseFloat(ask[1])]);

      if (bids.length === 0 || asks.length === 0) {
        console.warn(`Nado订单簿为空: ${symbol}`);
        return null;
      }

      return {
        dex: 'nado',
        symbol: symbol,
        bids: bids,
        asks: asks,
        timestamp: new Date().toISOString(),
        product_id: data.product_id,
        ticker_id: data.ticker_id,
        api_timestamp: data.timestamp,
      };
    } catch (error) {
      console.error(`解析Nado订单簿失败: ${symbol}`, error);
      return null;
    }
  }

  /**
   * 解析订单簿数据（通用，主要用于01.xyz）
   * @param {string} dex - DEX名称
   * @param {string} symbol - 币种符号
   * @param {Object} data - API返回的原始数据
   * @returns {Object|null} 标准化的订单簿数据
   */
  _parseOrderbook(dex, symbol, data) {
    try {
      let bids = null;
      let asks = null;

      if (dex === '01.xyz') {
        if (data.bids && data.asks) {
          bids = data.bids;
          asks = data.asks;
        }
      } else {
        if (data.bids && data.asks) {
          bids = data.bids;
          asks = data.asks;
        }
      }

      if (bids === null || asks === null) {
        console.warn(`无法解析订单簿: ${dex} - ${symbol}`);
        return null;
      }

      // 标准化订单数据
      const normalizeOrder = (order) => {
        if (Array.isArray(order) && order.length >= 2) {
          return [parseFloat(order[0]), parseFloat(order[1])];
        } else if (typeof order === 'object' && order !== null) {
          const price = order.price || 0;
          const size = order.size || order.amount || order.quantity || 0;
          return [parseFloat(price), parseFloat(size)];
        }
        return null;
      };

      bids = bids.map(normalizeOrder).filter(b => b !== null);
      asks = asks.map(normalizeOrder).filter(a => a !== null);

      if (bids.length === 0 || asks.length === 0) {
        console.warn(`订单簿为空: ${dex} - ${symbol}`);
        return null;
      }

      return {
        dex: dex,
        symbol: symbol,
        bids: bids,
        asks: asks,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error(`解析订单簿失败: ${dex} - ${symbol}`, error);
      return null;
    }
  }

  /**
   * 计算中间价
   * @param {Object} orderbook - 订单簿数据
   * @returns {number|null} 中间价
   */
  calculateMidPrice(orderbook) {
    if (!orderbook || !orderbook.bids || !orderbook.asks ||
        orderbook.bids.length === 0 || orderbook.asks.length === 0) {
      return null;
    }

    const bestBid = orderbook.bids[0][0];
    const bestAsk = orderbook.asks[0][0];
    return (bestBid + bestAsk) / 2;
  }

  /**
   * 计算加权平均价（考虑深度）
   * @param {Object} orderbook - 订单簿数据
   * @param {number} depth - 考虑的价格深度
   * @returns {number|null} 加权平均价
   */
  calculateWeightedPrice(orderbook, depth = 5) {
    if (!orderbook || !orderbook.bids || !orderbook.asks ||
        orderbook.bids.length === 0 || orderbook.asks.length === 0) {
      return null;
    }

    const bids = orderbook.bids.slice(0, depth);
    const asks = orderbook.asks.slice(0, depth);

    // 买盘加权平均价
    const bidTotalValue = bids.reduce((sum, [price, size]) => sum + price * size, 0);
    const bidTotalSize = bids.reduce((sum, [, size]) => sum + size, 0);
    const bidWeighted = bidTotalSize > 0 ? bidTotalValue / bidTotalSize : 0;

    // 卖盘加权平均价
    const askTotalValue = asks.reduce((sum, [price, size]) => sum + price * size, 0);
    const askTotalSize = asks.reduce((sum, [, size]) => sum + size, 0);
    const askWeighted = askTotalSize > 0 ? askTotalValue / askTotalSize : 0;

    return (bidWeighted + askWeighted) / 2;
  }
}
