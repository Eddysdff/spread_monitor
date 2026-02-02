"""
持仓管理模块
负责管理开仓和平仓状态
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)


class Position:
    """持仓信息"""
    
    def __init__(
        self,
        position_id: str,
        dex1: str,
        dex2: str,
        symbol: str,
        high_dex: str,
        high_side: str,
        high_price: float,
        low_dex: str,
        low_side: str,
        low_price: float,
        amount: float,
        open_spread: float,
        open_spread_pct: float,
        total_cost: float,
        convergence_mean: Optional[float] = None
    ):
        self.position_id = position_id
        self.dex1 = dex1
        self.dex2 = dex2
        self.symbol = symbol
        self.high_dex = high_dex
        self.high_side = high_side
        self.high_price = high_price
        self.low_dex = low_dex
        self.low_side = low_side
        self.low_price = low_price
        self.amount = amount
        self.open_spread = open_spread
        self.open_spread_pct = open_spread_pct
        self.total_cost = total_cost
        self.convergence_mean = convergence_mean
        self.open_time = datetime.now()
        self.close_time: Optional[datetime] = None
        self.status = 'OPEN'  # OPEN, CLOSED
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'position_id': self.position_id,
            'dex1': self.dex1,
            'dex2': self.dex2,
            'symbol': self.symbol,
            'high_dex': self.high_dex,
            'high_side': self.high_side,
            'high_price': self.high_price,
            'low_dex': self.low_dex,
            'low_side': self.low_side,
            'low_price': self.low_price,
            'amount': self.amount,
            'open_spread': self.open_spread,
            'open_spread_pct': self.open_spread_pct,
            'total_cost': self.total_cost,
            'convergence_mean': self.convergence_mean,
            'open_time': self.open_time.isoformat(),
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'status': self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        """从字典创建"""
        position = cls(
            position_id=data['position_id'],
            dex1=data['dex1'],
            dex2=data['dex2'],
            symbol=data['symbol'],
            high_dex=data['high_dex'],
            high_side=data['high_side'],
            high_price=data['high_price'],
            low_dex=data['low_dex'],
            low_side=data['low_side'],
            low_price=data['low_price'],
            amount=data['amount'],
            open_spread=data['open_spread'],
            open_spread_pct=data['open_spread_pct'],
            total_cost=data['total_cost'],
            convergence_mean=data.get('convergence_mean'),
        )
        position.open_time = datetime.fromisoformat(data['open_time'])
        if data.get('close_time'):
            position.close_time = datetime.fromisoformat(data['close_time'])
        position.status = data.get('status', 'OPEN')
        return position


class PositionManager:
    """持仓管理器"""
    
    def __init__(self):
        # 持仓字典: {position_id: Position}
        self.positions: Dict[str, Position] = {}
    
    def generate_position_id(self, dex1: str, dex2: str, symbol: str) -> str:
        """生成持仓ID"""
        return f"{dex1}_{dex2}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def open_position(
        self,
        dex1: str,
        dex2: str,
        symbol: str,
        high_dex: str,
        high_price: float,
        low_dex: str,
        low_price: float,
        amount: float,
        open_spread: float,
        open_spread_pct: float,
        total_cost: float,
        convergence_mean: Optional[float] = None
    ) -> Position:
        """
        开仓
        
        Returns:
            持仓对象
        """
        position_id = self.generate_position_id(dex1, dex2, symbol)
        
        position = Position(
            position_id=position_id,
            dex1=dex1,
            dex2=dex2,
            symbol=symbol,
            high_dex=high_dex,
            high_side='SHORT',
            high_price=high_price,
            low_dex=low_dex,
            low_side='LONG',
            low_price=low_price,
            amount=amount,
            open_spread=open_spread,
            open_spread_pct=open_spread_pct,
            total_cost=total_cost,
            convergence_mean=convergence_mean,
        )
        
        self.positions[position_id] = position
        logger.info(f"开仓: {position_id} - {symbol} {dex1} vs {dex2}")
        
        return position
    
    def get_open_position(self, dex1: str, dex2: str, symbol: str) -> Optional[Position]:
        """
        获取当前持仓
        
        Returns:
            持仓对象或None
        """
        # 查找匹配的持仓（按交易对和币种）
        for position in self.positions.values():
            if position.status == 'OPEN':
                # 检查是否匹配（考虑顺序）
                if ((position.dex1 == dex1 and position.dex2 == dex2) or
                    (position.dex1 == dex2 and position.dex2 == dex1)) and \
                   position.symbol == symbol:
                    return position
        return None
    
    def close_position(self, position_id: str) -> Optional[Position]:
        """
        平仓
        
        Returns:
            持仓对象或None
        """
        position = self.positions.get(position_id)
        if position and position.status == 'OPEN':
            position.status = 'CLOSED'
            position.close_time = datetime.now()
            logger.info(f"平仓: {position_id}")
            return position
        return None
    
    def check_close_signal(
        self,
        position: Position,
        current_price1: float,
        current_price2: float,
        current_spread: float,
        current_spread_pct: float,
        convergence_mean: Optional[float] = None
    ) -> Optional[Dict]:
        """
        检查平仓信号
        
        Args:
            position: 持仓对象
            current_price1: 当前DEX1价格
            current_price2: 当前DEX2价格
            current_spread: 当前价差
            current_spread_pct: 当前价差百分比
            convergence_mean: 当前收敛区间均值
            
        Returns:
            平仓信号或None
        """
        # 计算持仓时间
        hold_time = (datetime.now() - position.open_time).total_seconds()
        max_hold_time = config.SIGNAL_CONFIG['max_hold_time']
        
        # 条件1: 最大持仓时间
        if hold_time > max_hold_time:
            return {
                'action': 'CLOSE',
                'reason': 'MAX_HOLD_TIME',
                'position_id': position.position_id,
                'hold_time': hold_time,
                'high_dex': position.high_dex,
                'high_side': 'LONG',  # 平仓时反向操作
                'low_dex': position.low_dex,
                'low_side': 'SHORT',  # 平仓时反向操作
                'current_spread': current_spread,
                'open_spread': position.open_spread,
            }
        
        # 条件2: 止损 - 价差扩大超过阈值
        stop_loss_ratio = config.SIGNAL_CONFIG['stop_loss_ratio']
        if current_spread > position.open_spread * stop_loss_ratio:
            return {
                'action': 'CLOSE',
                'reason': 'STOP_LOSS',
                'position_id': position.position_id,
                'hold_time': hold_time,
                'high_dex': position.high_dex,
                'high_side': 'LONG',
                'low_dex': position.low_dex,
                'low_side': 'SHORT',
                'current_spread': current_spread,
                'open_spread': position.open_spread,
            }
        
        # 条件3: 强制平仓 - 价差过小
        force_close_spread = config.SIGNAL_CONFIG['force_close_spread']
        if current_spread_pct < force_close_spread:
            return {
                'action': 'CLOSE',
                'reason': 'FORCE_CLOSE',
                'position_id': position.position_id,
                'hold_time': hold_time,
                'high_dex': position.high_dex,
                'high_side': 'LONG',
                'low_dex': position.low_dex,
                'low_side': 'SHORT',
                'current_spread': current_spread,
                'open_spread': position.open_spread,
            }
        
        # 条件4: 价差收敛到正常区间
        # 使用开仓时的收敛均值或当前的收敛均值
        target_mean = convergence_mean or position.convergence_mean
        if target_mean is not None:
            # 如果当前价差接近或小于收敛均值，可以平仓
            if current_spread <= target_mean * 1.1:  # 允许10%的误差
                # 计算未实现利润
                spread_profit = position.open_spread - current_spread
                spread_profit_pct = spread_profit / position.amount if position.amount > 0 else 0
                
                # 条件5: 达到目标利润
                target_profit_ratio = config.SIGNAL_CONFIG['target_profit_ratio']
                if spread_profit_pct >= position.total_cost * target_profit_ratio:
                    return {
                        'action': 'CLOSE',
                        'reason': 'TARGET_PROFIT',
                        'position_id': position.position_id,
                        'hold_time': hold_time,
                        'high_dex': position.high_dex,
                        'high_side': 'LONG',
                        'low_dex': position.low_dex,
                        'low_side': 'SHORT',
                        'current_spread': current_spread,
                        'open_spread': position.open_spread,
                        'unrealized_profit': spread_profit,
                    }
                
                # 如果价差收敛到均值附近，也可以平仓（保本或小亏）
                if current_spread <= target_mean * 1.05:
                    return {
                        'action': 'CLOSE',
                        'reason': 'CONVERGENCE',
                        'position_id': position.position_id,
                        'hold_time': hold_time,
                        'high_dex': position.high_dex,
                        'high_side': 'LONG',
                        'low_dex': position.low_dex,
                        'low_side': 'SHORT',
                        'current_spread': current_spread,
                        'open_spread': position.open_spread,
                    }
        
        return None
    
    def get_all_open_positions(self) -> List[Position]:
        """获取所有持仓"""
        return [p for p in self.positions.values() if p.status == 'OPEN']
    
    def get_all_positions(self) -> List[Position]:
        """获取所有持仓（包括已平仓）"""
        return list(self.positions.values())
