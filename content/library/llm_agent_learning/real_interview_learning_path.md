# 基于真实面经反推的系统学习路径

这份文档只基于 [interview_sources.md](./interview_sources.md) 里“已核验真实面经”分区来反推学习顺序。

目标不是覆盖所有可能知识点，而是优先覆盖真实招聘里最常出现、最容易追问、最能区分水平的部分。

## 方法

当前可用的真实面经样本有：

- 牛客网真实面经 `20` 条
- 知乎真实面经 `2` 条

这些面经覆盖的岗位形态主要有：

- 大模型应用开发
- Agent 应用开发
- 大模型算法岗
- 大模型实习 / 校招 / 社招

从这些真实面经里，可以反推出一个非常稳定的事实：

1. `RAG` 是最高频主线
2. Agent / tool use / workflow 是第二主线
3. 基础 LLM 概念、prompt、embedding、向量检索是默认前置
4. `LangChain` / `LangGraph` 是实现框架问题，不是第一层问题
5. 多智能体会被问，但通常建立在单 Agent 和 workflow 之后
6. 微调 / `LoRA` / `DPO` / `RLHF` 更多出现在算法岗或偏模型岗
7. eval、guardrails、成本、时延在应用岗里越来越常见

## 从真实面经看，最该先学什么

如果只按真实面经高频来排，不按教材逻辑来排，顺序应该是：

1. LLM 应用基本盘
2. `RAG`
3. 单 Agent / tool use / `ReAct`
4. workflow 与 `LangGraph`
5. eval / guardrails / cost / latency
6. 多智能体
7. 微调与后训练

这个顺序和“从框架开始学”不同。

真实面经不会因为你会背 API 就放过你，反而更常问：

- 为什么这里要 `RAG`
- 检索错了怎么排查
- Agent 为什么会死循环
- 多智能体为什么真的有必要
- 为什么不用微调
- 成本、延迟、稳定性怎么做

## 学习路径

## 阶段 A：LLM 应用基本盘

### 为什么先学这个

真实面经里很少一上来就让你写复杂框架，通常先问：

- prompt、`RAG`、tool、微调分别做什么
- embedding 是什么
- vector DB 是什么
- 为什么模型会幻觉

### 必学内容

- chat model / embedding model
- context window
- prompt 设计基本原则
- structured output
- function calling 基础概念
- 向量检索最小链路

### 验收标准

- 能口述一个最小 LLM 应用架构
- 能说清 prompt、tool、`RAG`、微调四者边界

## 阶段 B：RAG 主线

### 为什么优先级最高

真实面经里，应用岗和 Agent 岗最稳定的高频主题就是 `RAG`。

### 必学内容

- 文档清洗与切块
- embedding
- vector store
- top-k retrieval
- citation
- retrieval vs generation 排障
- reranker / hybrid search

### 高频追问

- chunk size / overlap 怎么选
- 为什么召回错了生成通常也会错
- hybrid search 和 reranker 分别解决什么问题
- 怎么做 `RAG` eval

### 验收标准

- 你能独立做一个最小 `RAG`
- 你能拿 bad case 解释系统为什么错

## 阶段 C：单 Agent / Tool Use

### 为什么在 `RAG` 后面

真实面经里，Agent 问题通常不是孤立问的，而是问：

- 为什么不能直接 `RAG`
- 为什么这里要调工具
- 如何控制 Agent 步数和错误

### 必学内容

- function calling
- tool schema
- `ReAct`
- observation loop
- stop condition
- retry / fallback

### 高频追问

- 普通 chain 和 Agent 的区别
- Agent 为什么会死循环
- 工具是不是越多越好

### 验收标准

- 你能做一个最小多步 Agent
- 你能解释工具设计如何影响结果

## 阶段 D：Workflow / LangGraph

### 为什么这时候再上框架

真实面经更看重系统设计，不太在意你先背没背 `LangGraph` API。

先理解为什么需要状态、恢复、审批，再学 graph 更稳。

### 必学内容

- state graph
- node / edge
- checkpoint
- interrupt
- human-in-the-loop
- failure recovery

### 高频追问

- 为什么用 `LangGraph` 而不是简单 chain
- checkpoint 为什么重要
- graph 怎样避免黑盒 Agent 失控

### 验收标准

- 你能把 Agent 改造成有状态流程
- 你能画出状态转移图

## 阶段 E：工程化能力

### 为什么必须补

真实面经中，越来越多问题不是问“会不会用”，而是问：

- 怎么评测
- 怎么看日志
- 怎么降成本
- 怎么做安全控制

### 必学内容

- tracing
- eval set
- hallucination checks
- citation checks
- latency / cost profiling
- tool safety / approval

### 高频追问

- 没有 eval 怎么定位系统问题
- 线上 bad case 如何回流
- 成本和时延怎么优化

### 验收标准

- 你能拿一份自己的 eval 报告说话
- 你能指出至少 3 类线上风险

## 阶段 F：多智能体

### 为什么不是更前面

真实面经会问多智能体，但通常建立在你已经会单 Agent、workflow、评测之后。

### 必学内容

- supervisor
- router
- handoff
- role scope
- context isolation
- merge / arbitration

### 高频追问

- 为什么这里真的需要多 Agent
- 单 Agent + workflow 为什么不够
- 多 Agent 的主要失败模式是什么

### 验收标准

- 你能说明多 Agent 的收益和代价
- 你能设计一个可解释的多角色流程

## 阶段 G：微调与后训练

### 为什么放最后

真实面经里这块更偏算法岗，不是所有应用岗都会深挖。

但它依然重要，因为很常被拿来和 `RAG` 对比。

### 必学内容

- `SFT`
- `LoRA`
- `QLoRA`
- preference data
- `DPO`
- `RLHF`

### 高频追问

- `RAG` 和微调怎么选
- `LoRA` 和 `QLoRA` 的成本差别
- `DPO` 和 `RLHF` 的主要差别

### 验收标准

- 你能说清知识注入和行为塑形的差别
- 你能解释为什么很多场景先选 `RAG`

## 一条更贴近真实招聘的结论

如果你的目标是尽快达到“能答应用岗 / Agent 岗真实面经”的程度，那就不要平均用力。

推荐投入比例：

- `35%`：`RAG`
- `20%`：单 Agent / tool use
- `15%`：workflow / `LangGraph`
- `15%`：工程化与 eval
- `10%`：多智能体
- `5%`：微调与后训练

这不是理论最完整路径，但很接近真实面经的收益排序。

## 最终目标

走完这条路径后，你至少应该能做到：

1. 回答大部分应用岗 / Agent 岗真实面经中的高频问题
2. 独立做出一个 `RAG + tool use + eval` 的项目
3. 清楚说明什么时候要用 `LangGraph`、多智能体、微调，什么时候不要用
