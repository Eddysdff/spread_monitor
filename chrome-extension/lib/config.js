/**
 * 配置文件 - 从 config.py 移植
 */
const CONFIG = {
  // DEX配置
  DEX_CONFIG: {
    '01.xyz': {
      base_url: 'https://zo-mainnet.n1.xyz',
      markets: {
        'BTC': '/market/0/orderbook',
        'ETH': '/market/1/orderbook',
        'SOL': '/market/2/orderbook',
      },
      fees: {
        taker: 0.00035,  // 0.035%
        maker: 0.0001,   // 0.01%
      }
    },
    'nado': {
      base_url: 'https://gateway.prod.nado.xyz',
      gateway_v2_endpoint: '/v2/orderbook',
      markets: {
        'BTC': 'BTC-PERP_USDT0',
        'ETH': 'ETH-PERP_USDT0',
        'SOL': 'SOL-PERP_USDT0',
      },
      fees: {
        taker: 0.00035,  // 0.035%
        maker: 0.0001,   // 0.01%
      },
      api_config: {
        method: 'GET',
        headers: {},
        params: {
          depth: 20,
        },
      }
    },
    'variational': {
      base_url: 'https://omni.variational.io',
      quotes_endpoint: '/api/quotes/simple',
      markets: {
        'BTC': 'BTC',
        'ETH': 'ETH',
        'SOL': 'SOL',
      },
      fees: {
        taker: 0,  // 0%
        maker: 0,  // 0%
      },
      api_config: {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'origin': 'https://omni.variational.io',
          'referer': 'https://omni.variational.io/markets',
        },
        params: {},
        quote_qty: '0.001',
        settlement_asset: 'USDC',
        instrument_type: 'perpetual_future',
        funding_interval_s: 3600,
      }
    }
  },

  // 监控配置
  MONITOR_CONFIG: {
    update_interval: 1,  // 秒
    symbols: ['BTC', 'ETH', 'SOL'],
    dexes: ['01.xyz', 'nado', 'variational'],
  },

  // 价差分析配置
  SPREAD_CONFIG: {
    convergence_window_hours: 24,
    min_spread_threshold: 0.0005,  // 0.05%
    max_spread_threshold: 0.01,    // 1%
    open_spread_multiplier: 1.5,
    close_spread_multiplier: 0.8,
  },

  // 交易信号配置
  SIGNAL_CONFIG: {
    min_expected_profit_ratio: 1.2,
    target_profit_ratio: 1.2,
    stop_loss_ratio: 1.5,
    max_hold_time: 3600,
    force_close_spread: 0.0001,
  },
};
