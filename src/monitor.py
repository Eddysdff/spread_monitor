"""
主监控程序
实时监控价格和价差，生成交易信号
"""
import asyncio
import logging
from typing import Dict
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
import config
from src.data_collector import DataCollector
from src.spread_analyzer import SpreadAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


class Monitor:
    """价格监控器"""
    
    def __init__(self):
        self.collector = DataCollector()
        self.analyzer = SpreadAnalyzer()
        self.running = False
    
    async def start(self):
        """启动监控"""
        self.running = True
        console.print("[bold green]启动价格监控系统...[/bold green]")
        
        async with self.collector:
            # 创建实时显示界面
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="prices", size=10),
                Layout(name="spreads", size=15),
                Layout(name="signals", size=8),
                Layout(name="footer", size=3),
            )
            
            with Live(layout, refresh_per_second=1, screen=True) as live:
                while self.running:
                    try:
                        # 获取所有价格
                        prices = await self.collector.fetch_all_prices()
                        
                        # 更新界面
                        self._update_display(live, layout, prices)
                        
                        # 等待下一次更新
                        await asyncio.sleep(config.MONITOR_CONFIG['update_interval'])
                    except KeyboardInterrupt:
                        console.print("\n[bold yellow]停止监控...[/bold yellow]")
                        self.running = False
                        break
                    except Exception as e:
                        logger.error(f"监控异常: {str(e)}")
                        await asyncio.sleep(1)
    
    def _update_display(self, live, layout: Layout, prices: Dict):
        """更新显示界面"""
        # 更新头部
        layout["header"].update(self._create_header())
        
        # 更新价格表格
        layout["prices"].update(self._create_price_table(prices))
        
        # 更新价差表格
        layout["spreads"].update(self._create_spread_table(prices))
        
        # 更新信号表格
        layout["signals"].update(self._create_signal_table(prices))
        
        # 更新底部
        layout["footer"].update(self._create_footer())
    
    def _create_header(self) -> Panel:
        """创建头部面板"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"[bold cyan]PerpDEX 多空对冲套利监控系统[/bold cyan] | 时间: {now}"
        return Panel(content, border_style="cyan")
    
    def _create_price_table(self, prices: Dict) -> Table:
        """创建价格表格"""
        table = Table(title="实时价格", show_header=True, header_style="bold magenta")
        table.add_column("币种", style="cyan")
        
        for dex in config.MONITOR_CONFIG['dexes']:
            table.add_column(dex, justify="right", style="yellow")
        
        for symbol in config.MONITOR_CONFIG['symbols']:
            row = [symbol]
            
            # 各DEX价格
            for dex in config.MONITOR_CONFIG['dexes']:
                dex_data = prices.get(symbol, {}).get(dex)
                if dex_data:
                    price = dex_data['price']
                    row.append(f"{price:.2f}")
                else:
                    row.append("N/A")
            
            table.add_row(*row)
        
        return table
    
    def _create_spread_table(self, prices: Dict) -> Table:
        """创建价差表格"""
        table = Table(title="价差分析", show_header=True, header_style="bold magenta")
        table.add_column("交易对", style="cyan")
        table.add_column("币种", style="cyan")
        table.add_column("价差", justify="right", style="yellow")
        table.add_column("价差%", justify="right", style="yellow")
        table.add_column("收敛区间", justify="right", style="green")
        table.add_column("状态", style="bold")
        
        # 计算所有DEX对的价差
        dex_pairs = [
            ('01.xyz', 'nado'),
            ('01.xyz', 'variational'),
            ('nado', 'variational'),
        ]
        
        for dex1, dex2 in dex_pairs:
            for symbol in config.MONITOR_CONFIG['symbols']:
                price1_data = prices.get(symbol, {}).get(dex1)
                price2_data = prices.get(symbol, {}).get(dex2)
                
                if not price1_data or not price2_data:
                    continue
                
                price1 = price1_data['price']
                price2 = price2_data['price']
                
                # 分析价差
                analysis = self.analyzer.analyze_spread_opportunity(
                    dex1, dex2, symbol, price1, price2
                )
                
                spread = analysis['spread']
                spread_pct = analysis['spread_percentage'] * 100
                
                # 收敛区间
                convergence = analysis['convergence']
                if convergence:
                    conv_str = f"{convergence['lower']:.4f} ~ {convergence['upper']:.4f}"
                    status = "超出区间" if spread > convergence['upper'] else "正常"
                else:
                    conv_str = "计算中..."
                    status = "数据不足"
                
                table.add_row(
                    f"{dex1} vs {dex2}",
                    symbol,
                    f"{spread:.4f}",
                    f"{spread_pct:.4f}%",
                    conv_str,
                    status,
                )
        
        return table
    
    def _create_signal_table(self, prices: Dict) -> Table:
        """创建交易信号表格"""
        table = Table(title="交易信号", show_header=True, header_style="bold magenta")
        table.add_column("交易对", style="cyan")
        table.add_column("币种", style="cyan")
        table.add_column("信号", style="bold")
        table.add_column("操作", style="yellow")
        table.add_column("预期利润", justify="right", style="green")
        
        # 计算所有DEX对的套利机会
        dex_pairs = [
            ('01.xyz', 'nado'),
            ('01.xyz', 'variational'),
            ('nado', 'variational'),
        ]
        
        for dex1, dex2 in dex_pairs:
            for symbol in config.MONITOR_CONFIG['symbols']:
                price1_data = prices.get(symbol, {}).get(dex1)
                price2_data = prices.get(symbol, {}).get(dex2)
                
                # 如果价格数据缺失，显示数据缺失信息
                if not price1_data or not price2_data:
                    missing_dex = []
                    if not price1_data:
                        missing_dex.append(dex1)
                    if not price2_data:
                        missing_dex.append(dex2)
                    table.add_row(
                        f"{dex1} vs {dex2}",
                        symbol,
                        "[dim]无信号[/dim]",
                        f"[dim]数据缺失: {', '.join(missing_dex)}[/dim]",
                        "[dim]-[/dim]",
                    )
                    continue
                
                price1 = price1_data['price']
                price2 = price2_data['price']
                
                # 检查套利机会（假设交易金额1000 USDT）
                opportunity = self.analyzer.check_arbitrage_opportunity(
                    dex1, dex2, symbol, price1, price2, amount=1000, use_maker=True
                )
                
                signal = opportunity['signal']
                if signal:
                    action = signal['action']
                    if action == 'OPEN':
                        op_str = f"{signal['high_dex']} 做空 @ {signal['high_price']:.2f}\n"
                        op_str += f"{signal['low_dex']} 做多 @ {signal['low_price']:.2f}"
                        profit = opportunity['net_profit']
                        table.add_row(
                            f"{dex1} vs {dex2}",
                            symbol,
                            "[bold green]开仓[/bold green]",
                            op_str,
                            f"{profit:.4f}",
                        )
                    elif action == 'CLOSE':
                        # 平仓信号
                        op_str = f"{signal['high_dex']} 平多 @ {price1_data['price']:.2f}\n"
                        op_str += f"{signal['low_dex']} 平空 @ {price2_data['price']:.2f}"
                        if 'close_threshold' in signal:
                            reason = f"价差已收敛 (当前:{signal['current_spread']:.4f} <= 阈值:{signal['close_threshold']:.4f})"
                        else:
                            reason = signal.get('reason', '价差收敛')
                        table.add_row(
                            f"{dex1} vs {dex2}",
                            symbol,
                            "[bold yellow]平仓[/bold yellow]",
                            f"{op_str}\n原因: {reason}",
                            f"{signal['current_spread']:.4f}",
                        )
                else:
                    # 添加调试信息：显示为什么没有信号
                    debug = opportunity.get('debug_info', {})
                    reason = []
                    if not opportunity['is_profitable']:
                        reason.append(f"成本过高(成本:{opportunity['total_cost']:.4f}, 预期利润:{opportunity['expected_profit']:.4f})")
                    if not opportunity['within_threshold']:
                        spread_pct = opportunity['spread_percentage']
                        min_th = config.SPREAD_CONFIG['min_spread_threshold']
                        max_th = config.SPREAD_CONFIG['max_spread_threshold']
                        if spread_pct < min_th:
                            reason.append(f"价差过小({spread_pct*100:.4f}% < {min_th*100:.4f}%)")
                        else:
                            reason.append(f"价差过大({spread_pct*100:.4f}% > {max_th*100:.4f}%)")
                    if not opportunity['beyond_convergence'] and debug.get('has_convergence'):
                        reason.append(f"未超出收敛区间(当前:{opportunity['spread']:.4f}, 上界:{debug.get('convergence_upper', 0):.4f})")
                    
                    # 如果没有原因，显示默认信息
                    if not reason:
                        # 检查是否有收敛区间数据
                        if debug.get('has_convergence'):
                            reason.append("价差在正常范围内")
                        else:
                            reason.append("等待历史数据积累")
                    
                    table.add_row(
                        f"{dex1} vs {dex2}",
                        symbol,
                        "[dim]无信号[/dim]",
                        "[dim]" + "; ".join(reason[:2]) + "[/dim]",  # 最多显示2个原因
                        f"[dim]{opportunity['spread_percentage']*100:.4f}%[/dim]",
                    )
        
        if len(table.rows) == 0:
            table.add_row("暂无", "交易信号", "-", "-", "-")
        
        return table
    
    def _create_footer(self) -> Panel:
        """创建底部面板"""
        content = "[dim]按 Ctrl+C 停止监控[/dim]"
        return Panel(content, border_style="dim")


async def main():
    """主函数"""
    monitor = Monitor()
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())
