# PerpDEX 套利监控 Chrome 插件

## 安装方法

1. 打开 Chrome 浏览器
2. 访问 `chrome://extensions/`
3. 开启"开发者模式"（右上角）
4. 点击"加载已解压的扩展程序"
5. 选择 `chrome-extension` 文件夹

## 使用方法

1. 点击浏览器工具栏中的插件图标
2. 查看实时价格、价差分析和交易信号
3. 点击"刷新"按钮手动更新数据
4. 点击"设置"按钮配置参数

## 功能

- ✅ 实时监控三个DEX（01.xyz、nado、variational）的价格
- ✅ 计算两两DEX之间的价差
- ✅ 基于历史数据计算收敛区间
- ✅ 生成套利交易信号
- ✅ 显示预期利润和交易成本

## 注意事项

1. **图标文件**：需要创建 `assets/icons/` 文件夹，并添加以下图标文件：
   - `icon16.png` (16x16)
   - `icon48.png` (48x48)
   - `icon128.png` (128x128)

2. **首次使用**：插件需要一些时间来积累历史数据，才能准确计算收敛区间

3. **数据存储**：历史价差数据存储在浏览器本地，不会上传到服务器

## 开发说明

### 文件结构

```
chrome-extension/
├── manifest.json          # 插件配置
├── popup.html            # 弹窗界面
├── popup.js              # 弹窗逻辑
├── popup.css             # 弹窗样式
├── background.js         # 后台脚本
├── options.html          # 设置页面
├── options.js           # 设置页面逻辑
└── lib/
    ├── config.js         # 配置文件
    ├── data-collector.js # 数据采集模块
    └── spread-analyzer.js # 价差分析模块
```

### 待完成

- [ ] 添加图标文件
- [ ] 实现通知功能
- [ ] 优化UI样式
- [ ] 添加数据导出功能
