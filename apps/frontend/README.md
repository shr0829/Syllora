# Syllora Frontend

这是 Syllora 的 React 前端，负责承载三个主要区域：

- 首页对话框：输入想学的主题，与学习系统对话
- 左侧历史栏：查看并切换历史学习项目
- 项目详情页：展示研究结果、学习计划和知识点教学页

## 启动

```bash
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:4173
```

## 构建

```bash
npm run build
```

## 接口约定

前端通过 `/api/*` 调后端，主要包括：

- `GET /api/projects`
- `GET /api/projects/:id`
- `POST /api/projects`
- `POST /api/projects/:id/messages`
- `POST /api/projects/:id/research`
- `POST /api/projects/:id/plan`
- `POST /api/projects/:id/goals/:goalId/lesson`

## 内容生成

仓库内置学习资料位于：

- `../../content/library/learning_tracks/pytorch_to_transformer`
- `../../content/library/llm_agent_learning`

如果资料库文档更新，可以重新生成前端静态内容：

```bash
node scripts/generate-content.mjs
```
