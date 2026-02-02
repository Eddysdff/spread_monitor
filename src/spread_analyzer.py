"""
价差分析模块
负责计算价差、收敛区间和生成交易信号
"""
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import config

logger = logging.getLogger(__name__)


class SpreadAnalyzer:
    """价差分析器"""
    
    def __init__(self):
        # 存储历史价差数据: {(dex1, dex2, symbol): [spread1, spread2, ...]}
        self.spread_history: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
        # 存储历史价格数据: {(dex, symbol): [(timestamp, price), ...]}
        self.price_history: Dict[Tuple[str, str], List[Tuple[datetime, float]]] = defaultdict(list)
    
    def calculate_spread(self, price1: float, price2: float) -> float:
        """
        计算价差（绝对值）
        
        Args:
            price1: 价格1
            price2: 价格2
            
        Returns:
            价差
        """
        return abs(price1 - price2)
    
    def calculate_spread_percentage(self, price1: float, price2: float) -> float:
        """
        计算价差百分比
        
        Args:
            price1: 价格1
            price2: 价格2
            
        Returns:
            价差百分比
        """
        min_price = min(price1, price2)
        if min_price == 0:
            return 0
        return abs(price1 - price2) / min_price
    
    def update_spread_history(self, dex1: str, dex2: str, symbol: str, spread: float):
        """
        更新价差历史数据
        
        Args:
            dex1: DEX1名称
            dex2: DEX2名称
            symbol: 币种符号
            spread: 价差
        """
        key = (dex1, dex2, symbol)
        self.spread_history[key].append(spread)
        
        # 只保留最近24小时的数据（假设每秒更新一次，约86400条）
        max_history = config.SPREAD_CONFIG['convergence_window_hours'] * 3600
        if len(self.spread_history[key]) > max_history:
            self.spread_history[key] = self.spread_history[key][-max_history:]
    
    def calculate_convergence_range(self, dex1: str, dex2: str, symbol: str) -> Optional[Dict]:
        """
        计算价差收敛区间
        
        Args:
            dex1: DEX1名称
            dex2: DEX2名称
            symbol: 币种符号
            
        Returns:
            收敛区间信息: {mean, std, lower, upper}
        """
        key = (dex1, dex2, symbol)
        history = self.spread_history.get(key, [])
        
        if len(history) < 10:  # 至少需要10个数据点
            return None
        
        mean = np.mean(history)
        std = np.std(history)
        
        # 使用2倍标准差作为收敛区间
        return {
            'mean': mean,
            'std': std,
            'lower': mean - 2 * std,
            'upper': mean + 2 * std,
            'count': len(history),
        }
    
    def analyze_spread_opportunity(
        self, 
        dex1: str, 
        dex2: str, 
        symbol: str, 
        price1: float, 
        price2: float,
        binance_price: Optional[float] = None
    ) -> Dict:
        """
        分析价差套利机会
        
        Args:
            dex1: DEX1名称
            dex2: DEX2名称
            symbol: 币种符号
            price1: DEX1价格
            price2: DEX2价格
            binance_price: 币安价格（可选）
            
        Returns:
            分析结果
        """
        # 计算价差
        spread = self.calculate_spread(price1, price2)
        spread_pct = self.calculate_spread_percentage(price1, price2)
        
        # 更新历史数据
        self.update_spread_history(dex1, dex2, symbol, spread)
        
        # 计算收敛区间
        convergence = self.calculate_convergence_range(dex1, dex2, symbol)
        
        # 判断价差方向
        if price1 > price2:
            high_dex = dex1
            low_dex = dex2
            high_price = price1
            low_price = price2
        else:
            high_dex = dex2
            low_dex = dex1
            high_price = price2
            low_price = price1
        
        result = {
            'dex1': dex1,
            'dex2': dex2,
            'symbol': symbol,
            'price1': price1,
            'price2': price2,
            'spread': spread,
            'spread_percentage': spread_pct,
            'high_dex': high_dex,
            'low_dex': low_dex,
            'high_price': high_price,
            'low_price': low_price,
            'convergence': convergence,
        }
        
        return result
    
    def calculate_trading_cost(
        self, 
        dex1: str, 
        dex2: str, 
        amount: float, 
        use_maker: bool = True
    ) -> float:
        """
        计算交易成本
        
        Args:
            dex1: DEX1名称
            dex2: DEX2名称
            amount: 交易金额
            use_maker: 是否使用maker订单
            
        Returns:
            总手续费（开仓+平仓）
        """
        fee_type = 'maker' if use_maker else 'taker'
        
        fee1 = config.DEX_CONFIG[dex1]['fees'][fee_type] * amount
        fee2 = config.DEX_CONFIG[dex2]['fees'][fee_type] * amount
        
        # 开仓和平仓都需要手续费
        total_cost = (fee1 + fee2) * 2
        
        return total_cost
    
    def check_arbitrage_opportunity(
        self,
        dex1: str,
        dex2: str,
        symbol: str,
        price1: float,
        price2: float,
        amount: float = 1000,
        use_maker: bool = True
    ) -> Dict:
        """
        检查套利机会
        
        Args:
            dex1: DEX1名称
            dex2: DEX2名称
            symbol: 币种符号
            price1: DEX1价格
            price2: DEX2价格
            amount: 交易金额
            use_maker: 是否使用maker订单
            
        Returns:
            套利机会分析结果
        """
        # 分析价差
        spread_analysis = self.analyze_spread_opportunity(dex1, dex2, symbol, price1, price2)
        
        # 计算交易成本（基于交易金额）
        total_cost = self.calculate_trading_cost(dex1, dex2, amount, use_maker)
        
        # 计算预期价差利润（基于交易金额）
        # 价差利润 = (当前价差 - 预期收敛价差) / 价格 × 交易金额
        convergence = spread_analysis['convergence']
        spread_pct = spread_analysis['spread_percentage']
        min_price = min(price1, price2)
        
        if convergence:
            # 预期价差收敛到均值，利润 = (当前价差百分比 - 均值价差百分比) × 交易金额
            mean_spread_pct = convergence['mean'] / min_price if min_price > 0 else 0
            expected_spread_pct = spread_pct - mean_spread_pct
            expected_profit = expected_spread_pct * amount
        else:
            # 没有历史数据，保守估计：假设价差收敛50%
            expected_profit = spread_pct * amount * 0.5
        
        # 判断是否有利可图（预期利润需要覆盖成本）
        net_profit = expected_profit - total_cost
        is_profitable = net_profit > 0
        
        # 判断是否超出阈值
        min_threshold = config.SPREAD_CONFIG['min_spread_threshold']
        max_threshold = config.SPREAD_CONFIG['max_spread_threshold']
        
        within_threshold = min_threshold <= spread_pct <= max_threshold
        
        # 判断是否超出收敛区间（如果没有历史数据，使用价差百分比阈值）
        beyond_convergence = False
        if convergence:
            # 有历史数据：判断是否超出收敛区间上界
            beyond_convergence = spread_analysis['spread'] > convergence['upper']
        else:
            # 没有历史数据：使用价差百分比阈值判断
            # 如果价差超过最小阈值，认为可能存在机会
            beyond_convergence = spread_pct >= min_threshold
        
        result = {
            **spread_analysis,
            'amount': amount,
            'total_cost': total_cost,
            'expected_profit': expected_profit,
            'net_profit': net_profit,
            'is_profitable': is_profitable,
            'within_threshold': within_threshold,
            'beyond_convergence': beyond_convergence,
            'signal': self._generate_signal(
                spread_analysis, 
                is_profitable, 
                within_threshold, 
                beyond_convergence,
                convergence is not None
            ),
            'debug_info': {
                'has_convergence': convergence is not None,
                'convergence_mean': convergence['mean'] if convergence else None,
                'convergence_upper': convergence['upper'] if convergence else None,
                'current_spread': spread_analysis['spread'],
                'spread_pct': spread_pct,
            }
        }
        
        return result
    
    def _generate_signal(
        self,
        spread_analysis: Dict,
        is_profitable: bool,
        within_threshold: bool,
        beyond_convergence: bool,
        has_convergence_data: bool = False
    ) -> Optional[Dict]:
        """
        生成交易信号
        
        Args:
            spread_analysis: 价差分析结果
            is_profitable: 是否有利可图
            within_threshold: 是否在阈值范围内
            beyond_convergence: 是否超出收敛区间
            has_convergence_data: 是否有收敛区间数据
            
        Returns:
            交易信号或None
        """
        # 放宽信号生成条件：
        # 1. 如果有收敛区间数据：需要超出收敛区间且有利可图
        # 2. 如果没有收敛区间数据：只要价差在阈值范围内且有利可图即可
        
        if has_convergence_data:
            # 有历史数据：需要超出收敛区间
            condition = beyond_convergence and is_profitable and within_threshold
        else:
            # 没有历史数据：只要价差在阈值范围内且有利可图
            condition = is_profitable and within_threshold
        
        if condition:
            return {
                'action': 'OPEN',
                'high_dex': spread_analysis['high_dex'],
                'high_side': 'SHORT',
                'high_price': spread_analysis['high_price'],
                'low_dex': spread_analysis['low_dex'],
                'low_side': 'LONG',
                'low_price': spread_analysis['low_price'],
                'spread': spread_analysis['spread'],
                'spread_percentage': spread_analysis['spread_percentage'],
            }
        
        # 平仓信号：价差收敛到正常区间（如果有持仓的话）
        # 这里需要结合持仓状态判断，暂时返回None
        # 实际使用时需要传入持仓信息
        
        return None
