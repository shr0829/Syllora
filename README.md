# LearningPackage

[中文](#中文说明) | [English](#english)

---

## 中文说明

### 项目简介

LearningPackage 是一个面向 **辅助学习 / AI 课程生成** 的 Web 系统原型。

用户只需要在首页输入“想学什么”，系统就会围绕该主题自动完成：

1. 主题分析与研究资料整理
2. 联网检索与结构化研究文档生成
3. 阶段化学习路径规划
4. 每个阶段的详细知识讲解生成
5. 每个阶段的多图讲解生成
6. 结果以可稳定解析的 Markdown / JSON / 图片资产形式落盘

它适合做成“一个学习主题 = 一个本地知识仓库”的 AI 学习工作台。

---

### 当前版本亮点（v0.1.0）

- **对话式主题输入**：用户从 Web 首页直接输入学习目标
- **真实 API 接入**：支持真实文本模型与图片模型配置
- **结构化研究生成**：自动生成研究文档、来源列表、解析结果
- **阶段式学习路径**：将学习主题拆成多个可浏览阶段
- **阶段详情生成**：点击阶段即可生成细粒度知识讲解
- **多图生成**：每个阶段默认生成多张教学图示
- **并发生成**：
  - 多个阶段可并发生成
  - 单阶段内部的图片也可并发生成
- **流式更新**：
  - 生成过程显式进度展示
  - 文本按段流式刷新
  - 首页与阶段页统一进度体验
- **公式支持**：
  - 行内公式：`$...$`
  - 块级公式：`$$...$$`
  - 前端使用 MathJax 渲染
- **稳定可解析输出**：
  - prompt 收束
  - markdown 解析
  - canonical 结构化落盘
- **SSE 实时刷新**：前端通过项目事件流实时更新生成状态

---

### 项目结构

```text
LearningPackage/
├─ apps/
│  ├─ backend/
│  │  ├─ learningpackage/
│  │  │  ├─ config.py
│  │  │  ├─ llm_client.py
│  │  │  ├─ markdown_tools.py
│  │  │  ├─ project_store.py
│  │  │  └─ server.py
│  │  ├─ main.py
│  │  ├─ pyproject.toml
│  │  └─ uv.lock
│  └─ frontend/
│     ├─ src/
│     ├─ package.json
│     └─ verification/
├─ config/
│  ├─ ai.config.template.toml
│  └─ ai.config.toml        # 本地使用，已被 git ignore
├─ content/
│  └─ library/
├─ data/
│  └─ plans/                # 运行时生成，已被 git ignore
└─ README.md
```

---

### 单个学习主题仓库结构

```text
data/plans/<topic-id>/
├─ project.json
├─ research.md
├─ research.parsed.json
├─ sources.json
├─ learning_plan.md
├─ learning_plan.parsed.json
├─ stage_index.json
├─ meta/
│  ├─ research.generation.json
│  └─ plan.generation.json
└─ stages/
   └─ goal-001/
      ├─ lesson.md
      ├─ lesson.parsed.json
      ├─ stage_detail.json
      ├─ generation.json
      └─ assets/
         ├─ diagram-01.png
         ├─ diagram-02.png
         └─ *.meta.json
```

---

### 技术栈

- **Backend**: Python 3.13, 标准库 HTTP Server, uv
- **Frontend**: React 19, Vite
- **Streaming**: Server-Sent Events (SSE)
- **Math Rendering**: MathJax
- **LLM**:
  - 文本模型：OpenAI-compatible Responses / Chat Completions
  - 图片模型：gpt-image-2（多渠道回退）

---

### 启动方式

#### 1) 后端

在 `apps/backend/` 目录执行：

```bash
uv run python main.py serve --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

#### 2) 前端

在 `apps/frontend/` 目录执行：

```bash
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

生产构建：

```bash
npm run build
```

---

### 配置说明

项目优先读取：

1. `config/ai.config.toml`
2. 环境变量
3. 内置默认值

请先复制模板：

```bash
cp config/ai.config.template.toml config/ai.config.toml
```

模板核心结构：

```toml
[text]
model_provider = "OpenAI"
model = "gpt-5.4"
review_model = "gpt-5.4"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
model_context_window = 1000000
model_auto_compact_token_limit = 900000

[text.provider]
name = "OpenAI"
base_url = "https://api.asxs.top/v1"
wire_api = "responses"
requires_openai_auth = true
api_key = "YOUR_OPENAI_API_KEY"

[image]
model_id = "gpt-image-2"

[image.connection]
_type = "newapi_channel_conn"
key = "YOUR_IMAGE_API_KEY"
url = "https://4sapi.com"

[[image.channels]]
_type = "newapi_channel_conn"
key = "YOUR_SECONDARY_IMAGE_API_KEY"
url = "https://xcode.best"
```

> 注意：`config/ai.config.toml` 含真实密钥，不会提交到 GitHub。

---

### 主要接口

#### 健康与资料库

- `GET /api/health`
- `GET /api/library`
- `GET /api/library/{libraryId}`

#### 项目

- `GET /api/projects`
- `GET /api/projects/{projectId}`
- `POST /api/projects`
- `POST /api/projects/{projectId}/messages`
- `GET /api/projects/{projectId}/events`

#### 生成流程

- `POST /api/projects/{projectId}/research`
- `POST /api/projects/{projectId}/plan`
- `POST /api/projects/{projectId}/goals/{goalId}/lesson`
- `POST /api/projects/{projectId}/lessons/batch`

#### 阶段图示

- `GET /api/projects/{projectId}/goals/{goalId}/image`
- `GET /api/projects/{projectId}/goals/{goalId}/images/{index}`

---

### 当前版本的生成流程

1. 用户在首页输入学习主题
2. 系统创建项目并记录对话上下文
3. 后端调用文本模型生成研究文档
4. 后端把研究文档整理为阶段化学习计划
5. 用户可以：
   - 单独生成某个阶段
   - 或批量并发生成全部阶段
6. 每个阶段先流式生成正文，再并发生成多张讲解图
7. 前端通过 SSE 订阅实时刷新进度、草稿、阶段状态
8. 最终结果以 Markdown / JSON / 图片文件写入本地主题仓库

---

### 输出稳定性设计

为了让前端展示更稳定、后续二次处理更可靠，本项目采用：

- prompt 收束
- markdown 结构约束
- 生成后解析
- canonical 结构重建
- 文件化落盘

核心原则是：

> generate → parse → normalize → persist

而不是直接信任模型原始文本。

---

### 版本记录

详见：[CHANGELOG.md](./CHANGELOG.md)

---

## English

### Overview

LearningPackage is a prototype **AI-assisted learning system**.

A user enters a topic on the web homepage, and the system automatically:

1. analyzes the learning topic,
2. gathers and organizes research materials,
3. creates a staged learning plan,
4. generates detailed lesson content for each stage,
5. generates multiple instructional images per stage,
6. persists all results as stable, machine-parseable Markdown / JSON / image assets.

The product idea is:

> one learning topic = one local AI-generated learning repository.

---

### Highlights in v0.1.0

- Conversational topic input from the homepage
- Real text-model and image-model integration
- Structured research generation with source indexing
- Staged learning-path planning
- On-demand lesson generation per stage
- Multi-image generation per stage
- Parallel generation across stages
- Parallel image generation inside each stage
- Streaming progress and partial content updates
- Formula support with inline/block math
- SSE-based real-time UI refresh
- Stable parseable output via prompt constraints + parsing + normalization

---

### Tech Stack

- **Backend**: Python 3.13, standard-library HTTP server, uv
- **Frontend**: React 19, Vite
- **Realtime updates**: Server-Sent Events (SSE)
- **Math rendering**: MathJax
- **LLM integration**:
  - OpenAI-compatible text gateway
  - `gpt-image-2` image generation with multi-channel fallback

---

### Quick Start

#### Backend

From `apps/backend/`:

```bash
uv run python main.py serve --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
http://127.0.0.1:8000/api/health
```

#### Frontend

From `apps/frontend/`:

```bash
npm install
npm run dev
```

Dev URL:

```text
http://127.0.0.1:5173
```

Production build:

```bash
npm run build
```

---

### Configuration

The runtime loads configuration in this order:

1. `config/ai.config.toml`
2. environment variables
3. built-in defaults

Use `config/ai.config.template.toml` as your starting template.

> `config/ai.config.toml` contains real credentials and is intentionally excluded from Git.

---

### Main API Endpoints

- `GET /api/health`
- `GET /api/projects`
- `GET /api/projects/{projectId}`
- `POST /api/projects`
- `POST /api/projects/{projectId}/messages`
- `GET /api/projects/{projectId}/events`
- `POST /api/projects/{projectId}/research`
- `POST /api/projects/{projectId}/plan`
- `POST /api/projects/{projectId}/goals/{goalId}/lesson`
- `POST /api/projects/{projectId}/lessons/batch`
- `GET /api/projects/{projectId}/goals/{goalId}/image`
- `GET /api/projects/{projectId}/goals/{goalId}/images/{index}`

---

### Generation Pipeline

1. The user enters a topic on the homepage.
2. The system creates a project and conversation context.
3. The backend generates structured research.
4. The backend turns research into a staged learning plan.
5. The user can generate one stage or batch-generate all stages.
6. Each stage streams lesson text first, then generates multiple diagrams in parallel.
7. The frontend listens to SSE events and refreshes progress/content live.
8. Final artifacts are persisted as Markdown, JSON, and image assets.

---

### Stability Strategy

To keep outputs reliably parseable for UI rendering and downstream automation, the system uses:

- constrained prompts,
- markdown structure rules,
- post-generation parsing,
- canonical normalization,
- file-based persistence.

Core principle:

> generate → parse → normalize → persist

---

### Changelog

See: [CHANGELOG.md](./CHANGELOG.md)
