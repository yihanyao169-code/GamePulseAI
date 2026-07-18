# GamePulse AI
Google Play 游戏评论智能分析平台

GamePulse AI 是一款面向游戏发行与运营人员的 Google Play 评论智能分析工具。支持自动抓取评论、AI 分类、玩家情绪分析、多市场对比、跨游戏分析、运营洞察生成及 PPT 报告导出，帮助快速完成竞品分析、版本复盘和市场差异判断。

## 功能

- 输入 Google Play 游戏链接或包名
- 按国家、语言和时间范围抓取评论
- 评论清洗、去重和长度过滤
- 使用 Anthropic Claude API 进行评论分类
- 正负面情绪与问题分析
- 自动生成玩家优点、痛点和运营洞察
- 类别统计与可视化
- 单市场分析
- 跨市场对比
- 跨游戏对比
- 分析历史记录
- Evaluation Score
- PPT 报告导出
- Evaluation Framework PDF 下载

## 项目结构

```text
.
├── app.py                 # Streamlit 应用入口
├── docs/                  # 项目文档与评估框架
├── scripts/               # 辅助检查脚本
├── src/                   # 抓取、分析、评估、会话与报告导出模块
├── tests/                 # 自动化测试
├── .env.example           # 环境变量示例
├── requirements.txt       # Python 依赖
├── README.md              # 项目交付说明
└── render.yaml            # 云平台部署配置
```

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置 Claude API Key

项目使用 Anthropic Claude API 进行评论分析。请在项目根目录配置 `.env` 文件：

```text
ANTHROPIC_API_KEY=你的 Anthropic API Key
```

## AI 工作流

1. Google Play 评论采集
2. 评论清洗与语言过滤
3. Claude API 评论分析
4. 玩家反馈总结生成
5. 运营洞察与评分生成
6. PPT 报告导出

## 运行

完成依赖安装和 Claude API Key 配置后即可运行，无需修改代码文件。

```bash
python -m streamlit run app.py
```

启动后，在浏览器中打开终端显示的本地地址。

## 快速使用流程

1. 输入 Google Play 游戏链接或包名
2. 选择市场、语言、时间范围和样本数量
3. 开始抓取与 AI 分析
4. 查看单市场报告
5. 查看跨市场或跨游戏对比
6. 导出 PPT 报告；如需查看评分方法，可下载 Evaluation Framework PDF

## 评审运行说明

- 推荐使用 Python 3.10 或以上版本
- 首次运行需安装 `requirements.txt` 中的依赖
- 项目需要网络访问 Google Play 和 Anthropic API
- Claude API 调用会产生少量费用，但测试 Key 已设置费用上限
- 如果端口 8501 被占用，可使用：

```bash
python -m streamlit run app.py --server.port 8502
```

## 注意事项

- Google Play 页面、国家、语言和时间范围会影响可抓取评论数量
- 某些市场的评论量可能较少
- Claude API 调用耗时受评论数量和网络状况影响
- PPT 中文字体效果取决于本机字体环境
- 分析结果用于辅助游戏运营判断，不替代人工判断

## 部署

项目已提供 `render.yaml` 部署配置，可用于云平台部署。
