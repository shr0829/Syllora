# Syllora 体验版部署说明

## 目标

用 **最轻量** 的方式把 Syllora 部署到公网，方便别人直接打开体验。

当前项目最适合的体验版方案：

- **平台**：Railway
- **形态**：**单服务部署**
- **域名**：一个公网域名
- **数据存储**：Railway Volume 挂载到 `/app/data`

这样做的优点：

1. 前端和后端同域名，**不需要额外处理跨域**
2. SSE 流式更新可以直接工作
3. 后端写入的 `data/plans` 能持久保存
4. 操作比 “前后端两平台分开部署” 更轻

---

## 本仓库已补好的部署能力

我已经在仓库里补好了这些内容：

- `Dockerfile`
  - 自动构建 Vite 前端
  - 自动打包 Python 后端
  - 运行时由后端直接提供前端静态页面
- `.dockerignore`
  - 避免把本地缓存、日志、真实配置上传到镜像构建上下文
- `.env.example`
  - 提供 Railway 环境变量模板
- `apps/backend/learningpackage/server.py`
  - 现在支持直接托管 `apps/frontend/dist`
- `apps/frontend/src/lib/api.js`
  - 现在支持 `VITE_API_BASE_URL`
  - 以后如果改成前后端分离部署，也可以继续用

---

## 部署架构

浏览器访问：

```text
https://your-syllora.up.railway.app
```

请求流向：

```text
Browser
  └─> Railway / Syllora
       ├─> GET /           -> 前端静态页面
       ├─> GET /assets/*   -> 前端构建资源
       ├─> GET /api/health -> 后端健康检查
       ├─> POST /api/*     -> 生成研究 / 计划 / 阶段内容
       └─> GET /api/.../events -> SSE 实时流式更新
```

---

## 第 1 步：推送当前代码到 GitHub

如果你的本地修改还没推送：

```bash
git add .
git commit -m "为体验版上线准备最轻量单服务部署配置"
git push
```

---

## 第 2 步：在 Railway 创建项目

1. 打开 Railway
2. 选择 **New Project**
3. 选择 **Deploy from GitHub repo**
4. 选择仓库：`shr0829/Syllora`

Railway 会自动识别根目录里的 `Dockerfile`。

---

## 第 3 步：添加 Volume

这个步骤必须做，否则生成出来的学习内容会在重启/重新部署后丢失。

在 Railway 项目里：

1. 打开当前服务
2. 进入 **Volumes**
3. 新建一个 Volume
4. 挂载路径填写：

```text
/app/data
```

因为项目运行时会把内容写到：

```text
data/plans/
```

在容器里它对应：

```text
/app/data/plans/
```

---

## 第 4 步：配置环境变量

在 Railway 服务的 **Variables** 中填这些值。

### 文本模型

```text
LEARNING_MODEL_PROVIDER=OpenAI
LEARNING_BASE_URL=https://api.asxs.top/v1
LEARNING_WIRE_API=responses
LEARNING_API_KEY=你的文本模型 key
LEARNING_MODEL=gpt-5.4
LEARNING_REVIEW_MODEL=gpt-5.4
LEARNING_MODEL_REASONING_EFFORT=xhigh
LEARNING_DISABLE_RESPONSE_STORAGE=true
LEARNING_NETWORK_ACCESS=enabled
LEARNING_WINDOWS_WSL_SETUP_ACKNOWLEDGED=true
LEARNING_MODEL_CONTEXT_WINDOW=1000000
LEARNING_MODEL_AUTO_COMPACT_TOKEN_LIMIT=900000
LEARNING_REQUIRES_OPENAI_AUTH=true
```

### 生图模型

```text
LEARNING_IMAGE_MODEL=gpt-image-2
LEARNING_IMAGE_BASE_URL=https://4sapi.com
LEARNING_IMAGE_API_KEY=你的 image key
```

### 运行时

通常 Railway 会自动注入 `PORT`，你不用手动填。

---

## 第 5 步：部署完成后检查

部署成功后，优先检查：

### 1. 健康检查

打开：

```text
https://你的域名/api/health
```

如果成功，应该返回 JSON，包含：

- `ok: true`
- `llm`

### 2. 首页能否打开

打开：

```text
https://你的域名/
```

应该能直接看到 Syllora 首页。

### 3. 实际生成链路

手动测试一轮：

1. 输入一个学习主题
2. 创建项目
3. 生成研究
4. 生成计划
5. 点击阶段生成内容
6. 检查流式更新和图片是否正常

---

## 体验版建议限制

为了避免 API 被别人无限刷，体验版建议至少加一个简单限制：

### 推荐做法（简单）

- 只把链接发给少量体验用户
- 先不公开大范围传播

### 下一步可加

- 一个简单访问码
- IP 限流
- 每日任务上限

---

## 常见问题

### 1. 为什么不建议直接上纯静态站？

因为当前项目包含：

- Python 常驻服务
- SSE
- 本地文件持久化写入

所以纯静态托管不够。

### 2. 为什么不建议直接上纯 serverless？

因为：

- SSE 长连接不适合纯函数式短请求
- 本地文件写入在 serverless 中通常不可持久保存

### 3. 如果以后要拆成前后端分离，可以吗？

可以。

我已经把前端 API 地址能力改成支持：

```text
VITE_API_BASE_URL
```

以后你可以：

- 前端：Vercel
- 后端：Railway

---

## 我已经替你做完的部分

我已经把仓库改成了**可直接做 Railway 单服务体验版部署**的形态。

你现在需要自己完成的，主要是平台侧操作：

1. 登录 Railway
2. 选 GitHub 仓库
3. 挂载 `/app/data`
4. 填环境变量
5. 点击部署

---

## 如果你下一步继续让我做

我还可以继续直接帮你补：

1. `railway.toml`
2. 一个简单的“体验码”访问保护
3. 部署后的自检脚本
4. README 里的正式部署章节
