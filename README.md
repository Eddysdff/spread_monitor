# PerpDEX 多空对冲套利监控系统

## 项目简介

这是一个用于监控多个 PerpDEX（01.xyz、nado、variational）的 BTC、ETH、SOL 实时订单簿价格，通过价差分析和多空对冲策略，实现最低磨损获取交易积分的监控系统。并已完成chrome插件开发，在插件中实现全功能。

## 核心功能

1. **实时价格监控**
   - 监控 3 个 DEX 的 BTC、ETH、SOL 订单簿价格
   - 获取币安 Oracle 价格作为基准

2. **价差分析**
   - 计算两两 DEX 之间的价差
   - 计算价差收敛区间（基于历史统计）
   - 识别价差异常机会

3. **交易信号生成**
   - 当价差超出收敛区间时，生成开仓信号
   - 计算预期利润和交易成本
   - 推荐最优平台组合（优先使用 variational 无手续费优势）

4. **多空对冲策略**
   - 在价格高的平台开空
   - 在价格低的平台开多
   - 价差收敛时平仓，用价差利润抵消手续费


## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行监控程序

```bash
python -m src.monitor
```

## 插件使用
chrome插件开发者模式下，直接加载 chrome-extension 文件夹即可使用。

## 配置说明

### 监控配置

- `update_interval`: 价格更新间隔（秒）
- `symbols`: 监控的币种列表
- `dexes`: 监控的 DEX 列表

### 价差分析配置

- `convergence_window_hours`: 收敛区间计算窗口（小时）
- `min_spread_threshold`: 最小价差阈值
- `max_spread_threshold`: 最大价差阈值

### 交易信号配置

- `min_expected_profit_ratio`: 最小预期利润倍数
- `target_profit_ratio`: 目标利润倍数
- `stop_loss_ratio`: 止损倍数
- `max_hold_time`: 最大持仓时间（秒）

## 手续费信息

| DEX | Taker费率 | Maker费率 |
|-----|----------|-----------|
| 01.xyz | 0.035% | 0.01% |
| nado | 0.035% | 0.01% |
| variational | 0% | 0% |

**最优组合：** variational (0%) + 01.xyz/nado (maker 0.01%) = 总费率 0.01%

## 使用说明

1. **启动监控**
   - 运行 `python -m src.monitor` 启动实时监控
   - 界面会显示实时价格、价差分析和交易信号

2. **查看交易信号**
   - 当检测到套利机会时，会显示开仓信号
   - 信号包含：交易对、操作方向、预期利润等信息

3. **手动执行交易**
   - 系统只生成信号，不自动执行交易
   - 根据信号手动在相应平台执行交易


