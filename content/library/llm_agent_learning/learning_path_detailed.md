# 详细学习路径

这份文档是执行版，不是总览版。

原则：

- 每个阶段都必须产出可运行结果
- 每个阶段都必须能解释“为什么这样设计”
- 每个阶段都必须做最小失败分析

## 阶段 0：系统视角建立

### 你要解决的问题

从“我会调模型”切到“我会设计一个 LLM 系统”。

### 你要学会的判断

- 什么时候只靠 prompt 就够
- 什么时候该接工具
- 什么时候该上 `RAG`
- 什么时候该考虑微调
- 什么时候根本不该用 Agent

### 最小产出

- 一张图：`用户 -> 应用层 -> 模型 -> 检索/工具 -> 输出`
- 一页笔记：prompt、tool、`RAG`、fine-tuning 四者边界

### 验收标准

- 你能用自己的话解释为什么“Agent 不是默认答案”
- 你能举出至少 3 个更适合 workflow 而不是 Agent 的任务

### 常见误区

- 把“回答不准”全部归咎于模型能力
- 还没做 retrieval 和 eval 就急着谈微调
- 把多智能体当成能力升级，而不是工程 tradeoff

## 阶段 1：LangChain 基础

### 学习目标

先学编排层，不先学花哨架构。

### 必学点

- prompt template
- model binding
- output parser
- structured output
- tools
- runnable / chain

### 最小 demo

- `01_langchain_basics.py`
- 输入一个问题
- 输出结构化 JSON
- 加一个最小工具，比如计算器或 mock weather

### 你必须能回答

- `LangChain` 解决的到底是什么问题
- 为什么结构化输出通常比自由文本更适合工程集成
- 什么时候直接调模型 API 更简单

### 通过标准

- 你能脱离教程写出最小链
- 你能解释每一层组件的职责

## 阶段 2：RAG 基础

### 学习目标

完成一个最小但完整的 `RAG` 链路。

### 必学点

- 文档读取
- 文本切块
- embedding
- vector store
- retrieval
- generation with citations

### 最小 demo

- `02_rag_ingest.py`
- `03_rag_query.py`
- 一份小语料库
- 一个可问答接口
- 回答时返回引用片段

### 你必须能回答

- 为什么 chunking 是高频面试点
- 为什么 embedding 质量不等于最终回答质量
- retrieval 错了以后，生成阶段为什么常常救不回来

### 通过标准

- 你能把索引、召回、生成三段流讲清楚
- 你能指出至少 3 个 bad case

## 阶段 3：RAG 优化与评测

### 学习目标

把 `RAG` 从“能用”推进到“能调”。

### 必学点

- chunk size / overlap tradeoff
- hybrid search
- reranker
- metadata filter
- query rewrite
- retrieval eval
- answer eval

### 最小 demo

- `04_rag_eval.py`
- 同一语料做两套以上索引策略
- 输出每套策略的 bad case 对比

### 你必须能回答

- 怎么判断错误是在召回还是在生成
- hybrid search 什么时候更值
- reranker 为什么不等于 retriever

### 通过标准

- 你能做一轮最小误差分析
- 你能提出至少 2 个基于证据的优化方向

## 阶段 4：ReAct 与 Tool Use

### 学习目标

理解“模型不是只会回答，它还可以调用外部动作”。

### 必学点

- function calling / tool calling
- `ReAct`
- observation loop
- max iterations
- stop criteria
- tool error handling

### 最小 demo

- `05_react_agent.py`
- 至少 2 个工具
- 有日志输出每一步 thought / action / observation
- 有最大步数限制

### 你必须能回答

- 为什么 `ReAct` 不是普通问答链
- tool schema 为什么重要
- 什么情况下 Agent 会死循环

### 通过标准

- 你能写出最小 Agent loop
- 你能解释每一步工具调用对后续决策的影响

## 阶段 5：LangGraph 与状态编排

### 学习目标

从“能跑一圈”升级到“系统可控、可恢复、可中断”。

### 必学点

- state
- node
- edge
- branch
- checkpoint
- interrupt
- human approval
- retry / fallback

### 最小 demo

- `06_langgraph_agent.py`
- 至少 1 个中断点
- 至少 1 个恢复点
- 至少 1 个审批节点

### 你必须能回答

- 什么时候 graph 比 chain 更必要
- checkpoint 为什么是生产系统关键点
- graph 怎样降低黑盒 agent loop 的风险

### 通过标准

- 你能自己画出 state graph
- 你能复盘一条失败路径和恢复路径

## 阶段 6：多智能体

### 学习目标

学会在“需要分工”时才用多智能体。

### 必学点

- supervisor
- handoff
- router
- context isolation
- role scope
- merge strategy
- final arbitration

### 最小 demo

- `07_multi_agent_demo.py`
- researcher / writer / reviewer 三角色
- 每个角色有清晰输入输出
- 有最终整合节点

### 你必须能回答

- 为什么这里真的需要多 Agent
- 为什么单 Agent + workflow 不够
- 如何避免重复劳动和上下文膨胀

### 通过标准

- 你能清楚说明分工边界
- 你能指出多 Agent 至少 3 类失败模式

## 阶段 7：评测、观测、守护

### 学习目标

建立“没有 eval 和 tracing，就没有工程闭环”的意识。

### 必学点

- tracing
- dataset / golden set
- offline eval
- online feedback
- hallucination checks
- citation checks
- latency / cost
- tool safety
- human-in-the-loop

### 最小 demo

- `08_eval_and_guardrails.py`
- 对现有系统做最小 tracing
- 自建 30 条评测样本
- 输出成功率、成本、时延

### 你必须能回答

- 你如何定义系统 success metric
- 线上 bad case 如何进入下一轮 eval
- 为什么 tool safety 是核心面试点

### 通过标准

- 你能给系统写一页 eval 报告
- 你能说清至少 3 类风险和缓解方式

## 阶段 8：微调与后训练

### 学习目标

把“模型改造”看成有成本、有适用边界的最后手段之一。

### 必学点

- `SFT`
- `LoRA`
- `QLoRA`
- preference data
- `DPO`
- `RLHF`
- `RFT`

### 最小产出

- `09_lora_or_dpo_notes.md`
- 一页对比：prompt / `RAG` / `SFT` / `DPO` / `RLHF`
- 一页数据设计笔记：什么样的数据才配谈微调

### 你必须能回答

- 为什么知识更新通常先看 `RAG`
- `LoRA` / `QLoRA` 省的到底是什么成本
- `DPO` 与传统 `RLHF` 在训练链路上有什么区别

### 通过标准

- 你能清楚区分知识注入、行为塑形、偏好对齐
- 你能看懂基础后训练面试题

## 阶段 9：Capstone

### 学习目标

把前面所有东西拼成一个完整作品。

### 推荐项目

- 企业知识库问答
- SQL / Python 数据分析助理
- 研究助理
- 文档审批代理

### 交付要求

- 系统图
- 关键模块
- 失败模式
- 评测集
- 指标
- 成本与延迟
- 为什么采用当前方案

### 通过标准

- 你可以在 10 分钟内完整讲清项目
- 你可以回答“为什么不是别的方案”

## 整体验收

整条路线走完以后，你至少应该能独立回答：

1. 什么时候用 `RAG`，什么时候用工具，什么时候用微调
2. 为什么 workflow 经常比 Agent 更稳
3. 为什么多智能体不是默认高级解
4. 没有 eval 和 tracing 时，为什么系统无法稳定迭代
5. 一个大模型应用真正难的部分到底是不是 prompt
