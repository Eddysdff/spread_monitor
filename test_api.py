"""
测试API连接
用于验证各DEX的API是否可以正常访问
"""
import asyncio
import aiohttp
import json
import sys
import io
from config import DEX_CONFIG

# 尝试导入 curl_cffi（用于绕过 Cloudflare 保护）
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    print("⚠ curl_cffi 未安装，variational API 可能无法绕过 Cloudflare 保护。建议安装: pip install curl-cffi")

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


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
        # Variational使用quotes/simple API端点
        base_url = var_config['base_url']
        endpoint = var_config['quotes_endpoint']
        url = f"{base_url}{endpoint}"
        api_config = var_config['api_config']
        
        # 测试每个币种
        for symbol, underlying in var_config['markets'].items():
            print(f"\n测试 {symbol} (underlying: {underlying})")
            print(f"  URL: {url}")
            
            # 构建请求体
            payload = {
                'instrument': {
                    'underlying': underlying,
                    'instrument_type': api_config.get('instrument_type', 'perpetual_future'),
                    'settlement_asset': api_config.get('settlement_asset', 'USDC'),
                    'funding_interval_s': api_config.get('funding_interval_s', 3600),
                },
                'qty': api_config.get('quote_qty', '0.001'),
            }
            
            # 添加完整的浏览器headers以绕过Cloudflare保护
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Content-Type': 'application/json',
                'Origin': 'https://omni.variational.io',
                'Referer': 'https://omni.variational.io/markets',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            # 合并配置中的headers
            headers.update(api_config.get('headers', {}))
            
            try:
                async with session.post(
                    url, 
                    json=payload, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ 成功获取数据")
                        print(f"  数据格式: {type(data)}")
                        
                        # 处理返回数据：可能是数组或单个对象
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]
                        
                        if isinstance(data, dict):
                            bid = data.get('bid')
                            ask = data.get('ask')
                            if bid and ask:
                                print(f"  Bid: {bid}")
                                print(f"  Ask: {ask}")
                                mid = (float(bid) + float(ask)) / 2
                                spread = float(ask) - float(bid)
                                spread_pct = (spread / mid) * 100
                                print(f"  Mid: {mid:.2f}")
                                print(f"  Spread: {spread:.2f} ({spread_pct:.4f}%)")
                            else:
                                print(f"  ✗ 未找到bid/ask")
                                print(f"  数据键: {list(data.keys())}")
                        
                        data_str = json.dumps(data, indent=2, ensure_ascii=False)[:500]
                        print(f"\n  数据预览:\n{data_str}...")
                    else:
                        error_text = await response.text()
                        print(f"✗ 请求失败: status={response.status}")
                        print(f"  错误信息: {error_text[:200]}")
            except Exception as e:
                print(f"✗ 异常: {str(e)}")
                import traceback
                print(f"  详细错误: {traceback.format_exc()[:300]}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("API 连接测试")
    print("=" * 60)
    
    await test_01xyz()
    await test_nado()
    await test_variational()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
