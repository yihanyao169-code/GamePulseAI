# GamePulse AI

移动游戏市场决策辅助工具 —— 从 Google Play 玩家评论中提取反馈，辅助竞品发现、市场评价比较与发行/优先级判断。

GamePulse AI 面向游戏发行与运营人员，围绕单个游戏在指定市场的玩家评论，完成抓取、清洗、AI 分类与情绪分析，并支持跨市场对比与项目内多次分析的横向比较，最终可导出 PPT 报告。

## 页面与功能导航

- **开机页**：进入应用后的欢迎页，可直接进入首页
- **首页**：三个核心入口（单市场分析 / 跨市场比较 / 打开工作台）与功能概览
- **单市场分析**：搜索并确认目标游戏，抓取指定市场的评论并生成 AI 分析报告
- **跨市场比较**：对同一款游戏在 2-5 个国家/地区的评价进行横向对比
- **AI 研究工作台**：记录研究目标，管理研究项目，将已完成的单市场分析保存进项目并做项目内对比
- **分析记录**：保存当前浏览器会话中最近生成的单市场分析报告
- **分析方法说明**：单市场/跨市场分析页面顶部可随时打开的方法论说明弹窗

## 核心能力

- Google Play 游戏名称搜索，返回候选列表供人工核对包名后确认
- 搜索结果中标注 Google Play 官方"最佳匹配"候选，并修复了 `google-play-scraper` 库在解析最佳匹配 `appId` 时的已知问题（见 `src/gp_search_compat.py`）
- 选定候选后同步展示游戏名称、开发商、评分与包名，供人工核对
- 按国家、语言和时间范围抓取 Google Play 评论，并进行清洗、去重与语言过滤
- 调用 Anthropic Claude API 对评论进行分类、情感分析，并生成结构化的玩家优点/痛点与运营洞察
- 单市场分析报告：类别统计、图表可视化、Evaluation Score
- 跨市场对比：雷达图 + 表格形式呈现多个市场的横向差异
- 工作台内的项目内对比：对同一研究项目中已保存的 2-4 条单市场分析结果生成雷达图与表格对比
- PPT 报告导出
- Evaluation Framework 说明文档（PDF）下载

## 工作台与数据保存范围说明

工作台（AI 研究工作台）目前的实际能力：

- **现在就能做**：创建/管理研究项目，把已完成的单市场分析保存进项目，对比项目内 2-4 条单市场分析结果（雷达图 + 表格）。
- **需要手动操作**：实际抓取评论、选择国家/语言/时间范围仍需前往「单市场分析」/「跨市场比较」页面手动设置并运行——工作台本身只负责记录研究目标和保存/对比已完成的分析结果，不会自动执行抓取或分析。
- **尚未开发**：根据自然语言研究任务自动拆解并串联执行"竞品发现 → 评论分析 → 市场选择"的全自动流程。

**数据保存限制（重要）**：

- 工作台的项目数据、分析记录页的历史报告，均只保存在 `st.session_state`（当前浏览器会话）中，**不写入服务器数据库，也没有任何持久化存储**。
- 关闭标签页、刷新页面或服务重启后，这些数据都会清空。
- 如需长期保存某次分析结果，请使用 PPT 导出功能另外存档，不要依赖工作台或分析记录页的"保存"。

## 本地运行

环境要求：

- Python 3.10 及以上版本
- 可正常访问 Google Play 与 Anthropic API 的网络环境

安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate   # Windows 下使用 .venv\Scripts\activate
pip install -r requirements.txt
```

配置环境变量：在项目根目录复制 `.env.example` 为 `.env`，并至少填写 `ANTHROPIC_API_KEY`（见下方环境变量说明）。

启动应用：

```bash
streamlit run app.py
```

启动后默认访问地址为终端输出的本地地址，通常是 `http://localhost:8501`。如果 8501 端口被占用，可指定其他端口：

```bash
streamlit run app.py --server.port 8502
```

## 环境变量说明

以 `.env.example` 为模板，在本地 `.env` 或部署平台的环境变量中配置：

| 变量名 | 是否必需 | 说明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | **必需** | Claude API 认证密钥，未配置时分析功能不可用 |
| `ANTHROPIC_BASE_URL` | 可选 | 自定义 Anthropic 兼容网关地址，留空则使用官方 API 端点 |
| `CLAUDE_MODEL` | 可选 | 默认使用的 Claude 模型，未设置时使用代码内置默认值 |
| `CLAUDE_CLASSIFY_MODEL` | 可选 | 评论分类任务使用的模型，未设置时回退到 `CLAUDE_MODEL` |
| `CLAUDE_SUMMARY_MODEL` | 可选 | 总结生成任务使用的模型，未设置时回退到 `CLAUDE_MODEL` |
| `CLAUDE_MAX_WORKERS` | 可选 | 分析并发数，未设置时使用代码内置默认值 |
| `DEBUG_MODE` | 可选 | 调试模式开关，生产环境建议保持 `false` |

请勿在 `.env`、代码或本文档中填写真实密钥；`.env` 已在 `.gitignore` 中排除，不应提交到仓库。

## 云端部署（Render）

项目已提供 `render.yaml`，可连接到 [Render](https://render.com) 完成部署：

- `runtime` 为 `python`
- 启动命令通过 Streamlit 以 `--server.address 0.0.0.0` 和 `--server.port $PORT` 监听 Render 分配的端口
- `healthCheckPath` 为 `/_stcore/health`

**部署前需注意**：

- `render.yaml` 中只声明了环境变量的名称（`sync: false`），不包含任何实际密钥值；`ANTHROPIC_API_KEY` 等敏感变量必须在 Render 控制台的 Environment 页面手动填写，不要写入 `render.yaml` 或提交到 GitHub。
- Render 免费套餐（Free plan）实例在长时间无请求后会休眠，休眠后的首次访问可能需要额外等待启动时间。

## 测试

```bash
python -m py_compile app.py src/*.py
python -m pytest -q
```

当前版本（`feature/agent-upgrade` 分支）已通过本地 `pytest` 全量用例（本次验证结果为 112 passed）以及浏览器端的功能验证，具体数字会随代码变化而更新，不代表对未来版本的固定承诺。

## 注意事项

- Google Play 页面、国家、语言和时间范围会影响可抓取的评论数量，某些市场的评论量可能较少
- Claude API 调用耗时受评论数量和网络状况影响
- PPT 中文字体效果取决于部署环境的字体支持（云端部署可安装 `fonts-noto-cjk` 等 CJK 字体包）
- Overall Score / Evaluation Score 基于 GamePulse AI Evaluation Framework 生成，**不等同于 Google Play 官方星级或商业表现**
- 分析结果用于辅助游戏运营判断，不替代人工判断

## 项目结构

```text
.
├── app.py                 # Streamlit 应用入口
├── .streamlit/             # Streamlit 主题等本地配置
├── docs/                   # 项目文档与评估框架
├── scripts/                 # 辅助检查脚本
├── src/                     # 抓取、分析、评估、工作台与报告导出模块
├── tests/                   # 自动化测试
├── .env.example             # 环境变量示例（不含真实密钥）
├── requirements.txt         # Python 依赖
├── README.md                # 项目说明
└── render.yaml               # 云平台部署配置（不含真实密钥）
```
