"""
配置文件
"""
import os
from typing import Dict

# DEX配置
DEX_CONFIG = {
    '01.xyz': {
        'base_url': 'https://zo-mainnet.n1.xyz',
        'markets': {
            'BTC': '/market/0/orderbook',
            'ETH': '/market/1/orderbook',
            'SOL': '/market/2/orderbook',
        },
        'fees': {
            'taker': 0.00035,  # 0.035%
            'maker': 0.0001,   # 0.01%
        }
    },
    'nado': {
        # 根据官方文档：https://docs.nado.xyz/developer-resources/api/v2/orderbook
        # Gateway V2 API
        # REST API: GET [GATEWAY_V2_ENDPOINT]/orderbook?ticker_id={ticker_id}&depth={depth}
        'base_url': 'https://gateway.prod.nado.xyz',
        'gateway_v2_endpoint': '/v2/orderbook',  # V2 订单簿端点
        # WebSocket 订阅端点（实时订单簿）
        # wss://gateway.prod.nado.xyz/v1/subscribe/orderbook?ticker_id={ticker_id}&depth={depth}
        'websocket_base_url': 'wss://gateway.prod.nado.xyz',
        'websocket_subscribe_endpoint': '/v1/subscribe/orderbook',
        # 市场映射：ticker_id 格式（需要确认实际格式）
        # 根据文档示例：ticker_id 格式为 "BTC-PERP_USDT0"
        # 需要确认 BTC、ETH、SOL 的实际 ticker_id
        'markets': {
            'BTC': 'BTC-PERP_USDT0',  # 待确认实际 ticker_id
            'ETH': 'ETH-PERP_USDT0',  # 待确认实际 ticker_id
            'SOL': 'SOL-PERP_USDT0',  # 待确认实际 ticker_id
        },
        'fees': {
            'taker': 0.00035,  # 0.035%
            'maker': 0.0001,   # 0.01%
        },
        # API特定配置
        'api_config': {
            'method': 'GET',
            'headers': {},
            'params': {
                'depth': 20,  # 默认获取20档深度
            },
            # Rate limits: 2400 requests/min or 40 requests/sec per IP
            'rate_limit': {
                'requests_per_min': 2400,
                'requests_per_sec': 40,
            },
            # 是否使用 WebSocket（可选，实时性更好）
            'use_websocket': False,  # 默认使用 REST API
        }
    },
    'variational': {
        # 根据官方文档：https://docs.variational.io/technical-documentation/api
        # Read-Only API Base URL
        'base_url': 'https://omni-client-api.prod.ap-northeast-1.variational.io',
        # Variational使用单一端点获取所有市场数据
        'stats_endpoint': '/metadata/stats',
        # 市场映射（用于从listings中查找对应的ticker）
        'markets': {
            'BTC': 'BTC',
            'ETH': 'ETH',
            'SOL': 'SOL',
        },
        'fees': {
            'taker': 0,  # 0%
            'maker': 0,   # 0%
        },
        # API特定配置
        'api_config': {
            'method': 'GET',
            'headers': {},
            'params': {},
            # Variational API返回quotes，可以选择不同size的报价
            # size_1k, size_100k, size_1m (majors only)
            'quote_size': 'size_100k',  # 使用100k的报价作为参考
        }
    }
}

# 币安Oracle配置
BINANCE_CONFIG = {
    'base_url': 'https://api.binance.com',
    'ticker_endpoint': '/api/v3/ticker/price',
    'symbols': {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT',
        'SOL': 'SOLUSDT',
    }
}

# 监控配置
MONITOR_CONFIG = {
    'update_interval': 1,  # 秒
    'symbols': ['BTC', 'ETH', 'SOL'],
    'dexes': ['01.xyz', 'nado', 'variational'],
}

# 价差分析配置
SPREAD_CONFIG = {
    'convergence_window_hours': 24,  # 收敛区间计算窗口（小时）
    'min_spread_threshold': 0.0005,  # 最小价差阈值（0.05%）
    'max_spread_threshold': 0.01,    # 最大价差阈值（1%），超过则不开仓
    # 开仓/平仓阈值（基于收敛区间）
    'open_spread_multiplier': 1.5,   # 开仓阈值：收敛区间上界 × 1.5
    'close_spread_multiplier': 0.8,  # 平仓阈值：收敛区间均值 × 0.8
}

# 交易信号配置
SIGNAL_CONFIG = {
    'min_expected_profit_ratio': 1.2,  # 最小预期利润倍数（相对于成本）
    'target_profit_ratio': 1.2,        # 目标利润倍数
    'stop_loss_ratio': 1.5,            # 止损倍数（价差扩大50%）
    'max_hold_time': 3600,              # 最大持仓时间（秒，1小时）
    'force_close_spread': 0.0001,      # 强制平仓价差（0.01%）
}

# 数据存储配置
STORAGE_CONFIG = {
    'db_path': 'data/arbitrage.db',
    'history_table': 'price_history',
    'spread_table': 'spread_history',
}
