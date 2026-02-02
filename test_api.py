"""
测试API连接
用于验证各DEX的API是否可以正常访问
"""
import asyncio
import aiohttp
import json
from config import DEX_CONFIG, BINANCE_CONFIG


async def test_01xyz():
    """测试01.xyz API"""
    print("\n=== 测试 01.xyz API ===")
    async with aiohttp.ClientSession() as session:
        for symbol, path in DEX_CONFIG['01.xyz']['markets'].items():
            url = DEX_CONFIG['01.xyz']['base_url'] + path
            print(f"\n测试 {symbol}: {url}")
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ 成功获取数据")
                        print(f"  数据格式: {type(data)}")
                        if isinstance(data, dict):
                            print(f"  键: {list(data.keys())[:5]}...")  # 只显示前5个键
                        elif isinstance(data, list):
                            print(f"  列表长度: {len(data)}")
                        # 打印部分数据（限制长度）
                        data_str = json.dumps(data, indent=2)[:500]
                        print(f"  数据预览:\n{data_str}...")
                    else:
                        print(f"✗ 请求失败: status={response.status}")
            except Exception as e:
                print(f"✗ 异常: {str(e)}")


async def test_binance():
    """测试币安API"""
    print("\n=== 测试币安 API ===")
    
    # 币安API：不带参数获取所有交易对价格
    url = BINANCE_CONFIG['base_url'] + BINANCE_CONFIG['ticker_endpoint']
    
    print(f"\n获取所有交易对价格: {url}")
    print("  (不带参数，返回所有交易对的数组)")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ 成功获取数据")
                    print(f"  数据格式: {type(data)}")
                    
                    if isinstance(data, list):
                        print(f"  返回格式: 数组（包含 {len(data)} 个交易对）")
                        
                        # 查找我们需要的交易对
                        prices = {}
                        for item in data:
                            symbol = item.get('symbol')
                            price_str = item.get('price')
                            if symbol and price_str:
                                try:
                                    prices[symbol] = float(price_str)
                                except ValueError:
                                    continue
                        
                        # 测试每个币种
                        for symbol in ['BTC', 'ETH', 'SOL']:
                            binance_symbol = BINANCE_CONFIG['symbols'].get(symbol)
                            if not binance_symbol:
                                print(f"\n  {symbol}: ✗ 配置中无对应交易对")
                                continue
                            
                            price = prices.get(binance_symbol)
                            if price:
                                print(f"\n  {symbol} ({binance_symbol}): ✓ 价格 = {price}")
                            else:
                                print(f"\n  {symbol} ({binance_symbol}): ✗ 未找到")
                        
                        # 显示前几个交易对示例
                        print(f"\n  前5个交易对示例:")
                        for i, item in enumerate(data[:5]):
                            print(f"    {i+1}. {item.get('symbol')}: {item.get('price')}")
                    else:
                        print(f"  ✗ 返回格式异常: 期望数组，得到 {type(data)}")
                        print(f"  数据: {data[:200] if isinstance(data, str) else data}")
                else:
                    print(f"✗ HTTP错误: {response.status}")
                    error_text = await response.text()
                    print(f"  错误信息: {error_text[:200]}")
        except Exception as e:
            print(f"✗ 异常: {str(e)}")
            import traceback
            print(f"  详细错误: {traceback.format_exc()[:500]}")
    async with aiohttp.ClientSession() as session:
        for symbol, binance_symbol in BINANCE_CONFIG['symbols'].items():
            url = BINANCE_CONFIG['base_url'] + BINANCE_CONFIG['ticker_endpoint']
            params = {'symbol': binance_symbol}
            print(f"\n测试 {symbol} ({binance_symbol}): {url}")
            print(f"  参数: {params}")
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ 成功获取价格: {data.get('price')}")
                    else:
                        error_text = await response.text()
                        print(f"✗ 请求失败: status={response.status}")
                        print(f"  错误信息: {error_text[:200]}")
            except Exception as e:
                print(f"✗ 异常: {str(e)}")
                import traceback
                print(f"  详细错误: {traceback.format_exc()[:300]}")


async def test_nado():
    """测试nado API"""
    print("\n=== 测试 nado API ===")
    nado_config = DEX_CONFIG['nado']
    if not nado_config.get('base_url'):
        print("⚠ nado API 未配置，跳过测试")
        return
    
    async with aiohttp.ClientSession() as session:
        for symbol, ticker_id in nado_config['markets'].items():
            if not ticker_id:
                print(f"⚠ {symbol} 的ticker_id未配置")
                continue
            
            # 构建 URL: https://gateway.prod.nado.xyz/v2/orderbook
            base_url = nado_config['base_url']
            endpoint = nado_config['gateway_v2_endpoint']
            url = f"{base_url}{endpoint}"
            
            # 构建查询参数
            params = {
                'ticker_id': ticker_id,
                'depth': nado_config['api_config'].get('params', {}).get('depth', 20)
            }
            
            print(f"\n测试 {symbol} (ticker_id: {ticker_id})")
            print(f"  URL: {url}")
            print(f"  参数: {params}")
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ 成功获取数据")
                        print(f"  数据格式: {type(data)}")
                        if isinstance(data, dict):
                            print(f"  键: {list(data.keys())}")
                            if 'bids' in data and 'asks' in data:
                                print(f"  bids数量: {len(data['bids'])}")
                                print(f"  asks数量: {len(data['asks'])}")
                                if data['bids']:
                                    print(f"  最佳买价: {data['bids'][0]}")
                                if data['asks']:
                                    print(f"  最佳卖价: {data['asks'][0]}")
                        data_str = json.dumps(data, indent=2)[:500]
                        print(f"  数据预览:\n{data_str}...")
                    else:
                        error_text = await response.text()
                        print(f"✗ 请求失败: status={response.status}")
                        print(f"  错误信息: {error_text[:200]}")
            except Exception as e:
                print(f"✗ 异常: {str(e)}")


async def test_variational():
    """测试variational API"""
    print("\n=== 测试 variational API ===")
    var_config = DEX_CONFIG['variational']
    if not var_config.get('base_url'):
        print("⚠ variational API 未配置，跳过测试")
        return
    
    async with aiohttp.ClientSession() as session:
        # Variational使用单一端点获取所有市场数据
        base_url = var_config['base_url']
        endpoint = var_config['stats_endpoint']
        url = f"{base_url}{endpoint}"
        
        print(f"\n获取所有市场数据: {url}")
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ 成功获取数据")
                    print(f"  数据格式: {type(data)}")
                    
                    if isinstance(data, dict) and 'listings' in data:
                        listings = data['listings']
                        print(f"  市场数量: {len(listings)}")
                        
                        # 检查每个币种
                        for symbol, ticker in var_config['markets'].items():
                            listing = None
                            for item in listings:
                                if item.get('ticker') == ticker:
                                    listing = item
                                    break
                            
                            if listing:
                                print(f"\n  {symbol} (ticker: {ticker}):")
                                print(f"    标记价格: {listing.get('mark_price')}")
                                quotes = listing.get('quotes', {})
                                if quotes:
                                    quote_size = var_config['api_config'].get('quote_size', 'size_100k')
                                    quote = quotes.get(quote_size)
                                    if quote:
                                        print(f"    {quote_size} bid: {quote.get('bid')}")
                                        print(f"    {quote_size} ask: {quote.get('ask')}")
                            else:
                                print(f"  {symbol} (ticker: {ticker}): ✗ 未找到")
                    
                    data_str = json.dumps(data, indent=2)[:800]
                    print(f"\n  数据预览:\n{data_str}...")
                else:
                    error_text = await response.text()
                    print(f"✗ 请求失败: status={response.status}")
                    print(f"  错误信息: {error_text[:200]}")
        except Exception as e:
            print(f"✗ 异常: {str(e)}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("API 连接测试")
    print("=" * 60)
    
    await test_01xyz()
    await test_binance()
    await test_nado()
    await test_variational()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
