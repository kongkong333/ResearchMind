# ResearchMind

ResearchMind 是一个面向科研选题与论文调研的 AI 研究助手。它可以围绕指定主题抓取论文信息，结合大模型生成论文解读、研究趋势、研究空白与推荐阅读，并通过本地 Web 页面查看运行进度和报告结果。

当前项目基于 Python、FastAPI 和原生前端实现，默认报告输出到 `reports/` 目录。

## 主要功能

- 按研究主题创建调研任务
- 从 arXiv、OpenReview、PubMed、Crossref、ACL Anthology、AAAI、COLM、COLING、ICME 等来源收集论文信息
- 使用 OpenAI 兼容接口生成论文分析与研究报告
- 在浏览器中查看任务进度、报告路径与历史结果
- 支持命令行离线诊断模式，便于验证抓取与报告链路

## 环境要求

- Python 3.10 或更高版本
- Windows、macOS 或 Linux
- 可用的 OpenAI API Key，或兼容 OpenAI API 的服务

Windows 用户可以直接使用仓库内的 `start_researchmind.bat` 和 `stop_researchmind.bat`。其他系统可使用 `uvicorn` 命令启动。

## 从 GitHub 拉取后使用

### 1. 克隆项目

```bash
git clone <your-repository-url>
cd ResearchMind
```

### 2. 创建虚拟环境

Windows PowerShell:

```powershell
py -m venv researchmind
.\researchmind\Scripts\python.exe -m pip install --upgrade pip
.\researchmind\Scripts\python.exe -m pip install -e ".[dev]"
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 3. 配置环境变量

项目提供了 `.env.example` 作为参考：

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/researchmind
OPENAI_API_KEY=your-openai-api-key
```

当前 Web 应用主要依赖 OpenAI 配置。可以按下面方式设置环境变量。

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="gpt-4.1-mini"
```

macOS / Linux:

```bash
export OPENAI_API_KEY="你的 API Key"
export OPENAI_MODEL="gpt-4.1-mini"
```

如果使用兼容 OpenAI API 的第三方服务，还可以设置：

```bash
export OPENAI_BASE_URL="https://your-api-base-url/v1"
```

Windows PowerShell 对应为：

```powershell
$env:OPENAI_BASE_URL="https://your-api-base-url/v1"
```

## 启动 Web 应用

### Windows 一键启动

确认已按上面的 Windows 步骤创建名为 `researchmind` 的虚拟环境后，双击或运行：

```powershell
.\start_researchmind.bat
```

脚本会启动本地服务并打开浏览器：

```text
http://127.0.0.1:8000
```

停止服务：

```powershell
.\stop_researchmind.bat
```

### 通用启动方式

Windows PowerShell:

```powershell
.\researchmind\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS / Linux:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

然后在浏览器访问：

```text
http://127.0.0.1:8000
```

## 命令行运行调研

可以通过脚本直接生成报告：

```bash
python scripts/run_research.py --topic "AI agents for scientific discovery" --openai-api-key "$OPENAI_API_KEY" --openai-model "gpt-4.1-mini"
```

Windows PowerShell 示例：

```powershell
.\researchmind\Scripts\python.exe scripts\run_research.py --topic "AI agents for scientific discovery" --openai-api-key $env:OPENAI_API_KEY --openai-model "gpt-4.1-mini"
```

如果不传入 `--openai-api-key` 和 `--openai-model`，脚本会进入离线诊断模式，用占位分析验证流程是否能跑通。

报告默认写入：

```text
reports/weekly_report.md
```

每次运行还会生成带任务 ID 的归档报告文件。

## 常用开发命令

运行测试：

```bash
pytest
```

或在 Windows 虚拟环境中运行：

```powershell
.\researchmind\Scripts\python.exe -m pytest
```

检查收集链路：

```bash
python scripts/check_collection_chain.py
```

## 项目结构

```text
app/
  api/                 API 路由
  core/                配置
  schemas/             请求与响应模型
  services/            论文收集、分析、翻译、报告生成等服务
  static/              前端页面、样式和脚本
  workflows/           调研流程节点与状态
scripts/               启动、停止、命令行调研和诊断脚本
reports/               默认报告输出目录
tests/                 单元测试和集成测试
```

## 运行日志与本地状态

Windows 一键启动脚本会在项目根目录生成本地运行文件：

- `.researchmind-web.pid`
- `.researchmind-start.log`
- `.researchmind-web.out.log`
- `.researchmind-web.err.log`

这些文件只用于本机调试和进程管理，不需要提交到 GitHub。

Web 页面中的设置会保存到 `.researchmind-settings.json`，其中可能包含 API Key。请勿将真实密钥提交到仓库。
