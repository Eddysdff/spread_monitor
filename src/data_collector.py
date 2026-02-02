"""
数据采集模块
负责从各个DEX和币安Oracle获取价格数据
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集器"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, Dict] = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_orderbook(self, dex: str, symbol: str) -> Optional[Dict]:
        """
        获取订单簿数据
        
        Args:
            dex: DEX名称
            symbol: 币种符号
            
        Returns:
            订单簿数据，包含bids和asks
        """
        try:
            dex_config = config.DEX_CONFIG.get(dex)
            if not dex_config:
                logger.error(f"DEX配置不存在: {dex}")
                return None
            
            # Variational使用特殊的方式：单一端点获取所有市场数据
            if dex == 'variational':
                return await self._fetch_variational_orderbook(symbol)
            
            # Nado 使用特殊的 API 格式：查询参数方式
            if dex == 'nado':
                return await self._fetch_nado_orderbook(symbol)
            
            market_path = dex_config['markets'].get(symbol)
            if not market_path:
                logger.error(f"市场路径不存在: {dex} - {symbol}")
                return None
            
            base_url = dex_config.get('base_url', '')
            if not base_url:
                logger.error(f"{dex} base_url 未配置")
                return None
            
            url = base_url + market_path
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_orderbook(dex, symbol, data)
                else:
                    logger.error(f"获取订单簿失败: {dex} - {symbol}, status={response.status}")
                    return None
        except Exception as e:
            logger.error(f"获取订单簿异常: {dex} - {symbol}, error={str(e)}")
            return None
    
    async def _fetch_variational_orderbook(self, symbol: str) -> Optional[Dict]:
        """
        获取Variational订单簿数据
        Variational使用单一端点 /metadata/stats 返回所有市场数据
        
        Args:
            symbol: 币种符号
            
        Returns:
            标准化的订单簿数据
        """
        try:
            dex_config = config.DEX_CONFIG.get('variational')
            url = dex_config['base_url'] + dex_config['stats_endpoint']
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    # 从listings数组中查找对应的ticker
                    ticker = dex_config['markets'].get(symbol)
                    if not ticker:
                        logger.error(f"Variational市场映射不存在: {symbol}")
                        return None
                    
                    listings = data.get('listings', [])
                    listing = None
                    for item in listings:
                        if item.get('ticker') == ticker:
                            listing = item
                            break
                    
                    if not listing:
                        logger.warning(f"Variational未找到市场: {symbol} (ticker: {ticker})")
                        return None
                    
                    # 从quotes中提取bid/ask价格
                    quotes = listing.get('quotes', {})
                    quote_size = dex_config['api_config'].get('quote_size', 'size_100k')
                    quote = quotes.get(quote_size)
                    
                    if not quote:
                        logger.warning(f"Variational未找到报价: {symbol}, size: {quote_size}")
                        return None
                    
                    bid_price = float(quote.get('bid', 0))
                    ask_price = float(quote.get('ask', 0))
                    
                    if bid_price == 0 or ask_price == 0:
                        logger.warning(f"Variational报价无效: {symbol}, bid={bid_price}, ask={ask_price}")
                        return None
                    
                    # 构造标准化的订单簿格式
                    # 使用单一价格点作为订单簿（因为Variational只提供特定size的报价）
                    return {
                        'dex': 'variational',
                        'symbol': symbol,
                        'bids': [[bid_price, 1.0]],  # 使用1.0作为默认size
                        'asks': [[ask_price, 1.0]],
                        'timestamp': datetime.now().isoformat(),
                        'mark_price': float(listing.get('mark_price', 0)),
                        'quote_size': quote_size,
                    }
                else:
                    logger.error(f"获取Variational数据失败: {symbol}, status={response.status}")
                    return None
        except Exception as e:
            logger.error(f"获取Variational订单簿异常: {symbol}, error={str(e)}")
            return None
    
    async def _fetch_nado_orderbook(self, symbol: str) -> Optional[Dict]:
        """
        获取Nado订单簿数据
        根据文档：https://docs.nado.xyz/developer-resources/api/v2/orderbook
        REST API: GET [GATEWAY_V2_ENDPOINT]/orderbook?ticker_id={ticker_id}&depth={depth}
        GATEWAY_V2_ENDPOINT = https://gateway.prod.nado.xyz/v2
        
        Args:
            symbol: 币种符号
            
        Returns:
            标准化的订单簿数据
        """
        try:
            dex_config = config.DEX_CONFIG.get('nado')
            if not dex_config:
                logger.error("Nado配置不存在")
                return None
            
            # 获取 ticker_id
            ticker_id = dex_config['markets'].get(symbol)
            if not ticker_id:
                logger.error(f"Nado市场映射不存在: {symbol}")
                return None
            
            # 构建 URL: https://gateway.prod.nado.xyz/v2/orderbook
            base_url = dex_config['base_url']
            endpoint = dex_config['gateway_v2_endpoint']
            url = f"{base_url}{endpoint}"
            
            # 构建查询参数
            params = {
                'ticker_id': ticker_id,
                'depth': dex_config['api_config'].get('params', {}).get('depth', 20)
            }
            
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_nado_orderbook(symbol, data)
                else:
                    error_text = await response.text()
                    logger.error(f"获取Nado订单簿失败: {symbol}, status={response.status}, error={error_text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"获取Nado订单簿异常: {symbol}, error={str(e)}")
            return None
    
    def _parse_nado_orderbook(self, symbol: str, data: Dict) -> Optional[Dict]:
        """
        解析Nado订单簿数据
        根据文档格式：
        {
            "product_id": 1,
            "ticker_id": "BTC-PERP_USDT0",
            "bids": [[price, size], ...],
            "asks": [[price, size], ...],
            "timestamp": 1757913317944
        }
        
        Args:
            symbol: 币种符号
            data: API返回的原始数据
            
        Returns:
            标准化的订单簿数据
        """
        try:
            if 'bids' not in data or 'asks' not in data:
                logger.warning(f"Nado订单簿格式异常: {symbol}, data keys: {list(data.keys())}")
                return None
            
            bids = data['bids']
            asks = data['asks']
            
            # 确保价格和数量是数字类型
            bids = [[float(bid[0]), float(bid[1])] for bid in bids if len(bid) >= 2]
            asks = [[float(ask[0]), float(ask[1])] for ask in asks if len(ask) >= 2]
            
            if not bids or not asks:
                logger.warning(f"Nado订单簿为空: {symbol}")
                return None
            
            return {
                'dex': 'nado',
                'symbol': symbol,
                'bids': bids,
                'asks': asks,
                'timestamp': datetime.now().isoformat(),
                'product_id': data.get('product_id'),
                'ticker_id': data.get('ticker_id'),
                'api_timestamp': data.get('timestamp'),
            }
        except Exception as e:
            logger.error(f"解析Nado订单簿失败: {symbol}, error={str(e)}")
            return None
    
    def _parse_orderbook(self, dex: str, symbol: str, data: Dict) -> Dict:
        """
        解析订单簿数据（根据各DEX的实际API格式调整）
        
        Args:
            dex: DEX名称
            symbol: 币种符号
            data: API返回的原始数据
            
        Returns:
            标准化的订单簿数据
        """
        try:
            bids = None
            asks = None
            
            # 根据不同DEX的API格式解析
            if dex == '01.xyz':
                # 01.xyz 格式: {"updateId": ..., "bids": [[price, size], ...], "asks": [[price, size], ...], ...}
                if 'bids' in data and 'asks' in data:
                    bids = data['bids']
                    asks = data['asks']
            
            elif dex == 'nado':
                # Nado已经在_fetch_nado_orderbook中处理
                # 这里不应该被调用，但如果被调用，说明数据已经是标准格式
                if 'bids' in data and 'asks' in data:
                    bids = data['bids']
                    asks = data['asks']
                else:
                    logger.warning(f"nado订单簿格式异常: {symbol}, data keys: {list(data.keys())}")
            
            elif dex == 'variational':
                # Variational已经在_fetch_variational_orderbook中处理
                # 这里不应该被调用，但如果被调用，说明数据已经是标准格式
                if 'bids' in data and 'asks' in data:
                    bids = data['bids']
                    asks = data['asks']
                else:
                    logger.warning(f"variational订单簿格式异常: {symbol}, data keys: {list(data.keys())}")
            
            else:
                logger.error(f"未知的DEX: {dex}")
                return None
            
            if bids is None or asks is None:
                logger.warning(f"无法解析订单簿: {dex} - {symbol}, data={data}")
                return None
            
            # 确保价格和数量是数字类型
            # 处理不同的数据格式：列表或字典
            def normalize_order(order):
                """标准化订单数据"""
                if isinstance(order, list) and len(order) >= 2:
                    return [float(order[0]), float(order[1])]
                elif isinstance(order, dict):
                    # 字典格式: {"price": ..., "size": ...} 或 {"price": ..., "amount": ...}
                    price = order.get('price') or order.get('price', 0)
                    size = order.get('size') or order.get('amount') or order.get('quantity', 0)
                    return [float(price), float(size)]
                return None
            
            bids = [normalize_order(bid) for bid in bids if normalize_order(bid)]
            asks = [normalize_order(ask) for ask in asks if normalize_order(ask)]
            
            if not bids or not asks:
                logger.warning(f"订单簿为空: {dex} - {symbol}")
                return None
            
            return {
                'dex': dex,
                'symbol': symbol,
                'bids': bids,
                'asks': asks,
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"解析订单簿失败: {dex} - {symbol}, error={str(e)}, data={str(data)[:200]}")
            return None
    
    def calculate_mid_price(self, orderbook: Dict) -> Optional[float]:
        """
        计算中间价
        
        Args:
            orderbook: 订单簿数据
            
        Returns:
            中间价
        """
        if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
            return None
        
        best_bid = orderbook['bids'][0][0]
        best_ask = orderbook['asks'][0][0]
        return (best_bid + best_ask) / 2
    
    def calculate_weighted_price(self, orderbook: Dict, depth: int = 5) -> Optional[float]:
        """
        计算加权平均价（考虑深度）
        
        Args:
            orderbook: 订单簿数据
            depth: 考虑的价格深度
            
        Returns:
            加权平均价
        """
        if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
            return None
        
        bids = orderbook['bids'][:depth]
        asks = orderbook['asks'][:depth]
        
        # 计算买盘加权平均价
        bid_total_value = sum(price * size for price, size in bids)
        bid_total_size = sum(size for _, size in bids)
        bid_weighted = bid_total_value / bid_total_size if bid_total_size > 0 else 0
        
        # 计算卖盘加权平均价
        ask_total_value = sum(price * size for price, size in asks)
        ask_total_size = sum(size for _, size in asks)
        ask_weighted = ask_total_value / ask_total_size if ask_total_size > 0 else 0
        
        # 返回买卖盘加权平均价的中间值
        return (bid_weighted + ask_weighted) / 2
    
    async def fetch_all_prices(self) -> Dict[str, Dict]:
        """
        获取所有DEX的价格
        
        Returns:
            价格数据字典: {symbol: {dex: {price, orderbook}}}
        """
        results = {}
        
        for symbol in config.MONITOR_CONFIG['symbols']:
            results[symbol] = {}
            
            # 获取各DEX价格
            for dex in config.MONITOR_CONFIG['dexes']:
                orderbook = await self.fetch_orderbook(dex, symbol)
                if orderbook:
                    mid_price = self.calculate_mid_price(orderbook)
                    if mid_price:
                        results[symbol][dex] = {
                            'price': mid_price,
                            'orderbook': orderbook,
                        }
            
            # 添加延迟避免请求过快
            await asyncio.sleep(0.1)
        
        return results
