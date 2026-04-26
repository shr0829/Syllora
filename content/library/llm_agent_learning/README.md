# 从 LangChain 开始的大模型应用与 Agent 开发学习路线

这条路线是对当前仓库里“Transformer 手写学习路线”的补充，不替代原路线。

原路线解决的是：

- 张量、训练循环、注意力、Transformer block、mini GPT

这条新路线解决的是：

- 如何基于现成大模型做应用开发
- 如何做 `RAG`
- 如何做 `ReAct` / tool use
- 如何做 `LangGraph` / stateful agent
- 如何做多智能体协作
- 如何做评测、观测、守护与上线
- 如何理解微调、`LoRA` / `QLoRA`、`DPO` / `RLHF`

目标不是“会调 API”，而是最终能自己设计、实现、评估并迭代一个可运行的 Agent 应用。

## 总目标

完成阶段 0 到阶段 9 后，你应当能够：

- 用 `LangChain` / `LangGraph` 搭建最小可用 LLM 应用
- 独立实现一个可评估的 `RAG` 系统
- 独立实现一个带工具调用的 `ReAct` Agent
- 理解单 Agent 与多 Agent 的边界、适用场景和代价
- 能区分 prompt、`RAG`、微调、后训练分别解决什么问题
- 能对 Agent 系统做 tracing、eval、guardrails、成本与延迟分析
- 能做一个完整 capstone：检索 + 工具 + 状态图 + 评测 + 上线策略

## 学习原则

每一阶段都遵循同一套动作：

1. 先理解模块解决什么问题
2. 再做一个最小可运行 demo
3. 再补评测、日志、失败分析
4. 最后脱离教程重写一次

这条路线强调：

- 不把“会接 API”误当成“会做系统”
- 不把“能跑通 demo”误当成“能上线”
- 不把“Agent”当成默认答案，优先比较 workflow、RAG、tool use、微调的边界

## 文档地图

按用途拆成下面几份文档：

- `README.md`：总览、阶段索引、学习顺序
- `learning_path_detailed.md`：每个阶段学什么、做什么、怎么验收
- `real_interview_learning_path.md`：只基于已核验真实面经反推的学习主线
- `project_roadmap.md`：建议做的 demo、capstone、交付标准
- `weekly_plan.md`：按周推进的执行计划
- `study_plan_real_interviews.md`：按真实面经高频主题生成的执行计划文档
- `official_references.md`：优先看的官方文档与关键论文
- `interview_question_map.md`：按主题整理的高频面试问题
- `interview_sources.md`：55 个外部面经 / 题单来源索引

建议阅读顺序：

1. 先看本文件，确认整条路线的范围
2. 再看 `official_references.md`，知道该信什么材料
3. 接着看 `learning_path_detailed.md`，按阶段推进
4. 如果你要更贴近真实招聘问题，接着看 `real_interview_learning_path.md`
5. 学习过程中配合 `project_roadmap.md`、`weekly_plan.md` 和 `study_plan_real_interviews.md`
6. 准备面试时再刷 `interview_question_map.md`

## 先修要求

开始前最好已经具备：

- Python 基础
- HTTP / JSON / async 基础
- 基本 prompt engineering 概念
- 当前仓库前 0-3 阶段水平

如果你现在还不稳，先确保自己至少能：

- 看懂训练和推理流程
- 看懂 `embedding`、attention、context window 这些基本词
- 能独立写简单 Python 工程

## 阶段 0：应用开发视角的心智切换

### 目标

从“训练模型”切换到“设计 LLM 系统”。

### 需要掌握

- base model、chat model、embedding model 的区别
- prompt、tool use、`RAG`、fine-tuning 的边界
- context window、latency、cost、hallucination 的约束
- 为什么应用开发首先是“系统设计问题”，其次才是“模型调用问题”

### 必须理解

- 什么问题适合 `RAG`
- 什么问题适合 function calling / tool use
- 什么问题适合 workflow，而不是 Agent
- 什么问题必须考虑微调或后训练

### 查验问题

- 你会如何判断一个需求该做 prompt、`RAG` 还是微调？
- 为什么很多 Agent 问题本质上是检索、路由或工作流问题？
- 为什么“效果不好”不能只怪模型？

### 通过标准

- 能画出一个 LLM 应用的最小系统图
- 能说清 prompt、`RAG`、tool、微调分别负责什么

## 阶段 1：LangChain 基础

### 目标

掌握基于 `LangChain` 搭建 LLM 应用的基本组件。

### 需要掌握

- model / prompt / parser
- chain / runnable 思维
- tool 定义
- memory 的边界
- structured output

### 项目任务

1. 做一个最小问答链
2. 做一个结构化输出 demo
3. 做一个带 1-2 个工具的最小 Agent

### 必须理解

- `LangChain` 是“编排层”，不是模型本身
- 为什么结构化输出比纯文本后处理更稳
- 为什么 tool schema 设计会直接影响效果

### 查验问题

- `LangChain` 和直接调模型 API 的差别是什么？
- 什么时候该用 chain，什么时候该上 graph？
- 结构化输出为什么能降低解析错误？

### 通过标准

- 能独立写一个最小 `LangChain` 应用
- 能解释 prompt、model、parser、tool 在系统里的作用

## 阶段 2：RAG 基础版

### 目标

实现一个从文档到回答的最小 `RAG` 系统。

### 需要掌握

- 文档清洗
- chunking 策略
- embedding
- vector store
- top-k retrieval
- answer synthesis

### 项目任务

1. 选一个小语料库
2. 建索引
3. 实现检索问答
4. 输出引用片段

### 必须理解

- `RAG` 解决的是“知识注入与外部事实访问”
- `RAG` 不等于“把文档塞给模型”
- chunk 太大、太小都会坏
- embedding 召回和生成质量不是一回事

### 查验问题

- 为什么 `RAG` 能缓解知识过期问题？
- chunking 为什么是高频面试点？
- 向量召回错了，后面的生成为什么通常也会错？

### 通过标准

- 能跑通最小 `RAG`
- 能解释索引、召回、生成三段流

## 阶段 3：RAG 进阶与评测

### 目标

把“能跑”提升到“可分析、可优化、可解释”。

### 需要掌握

- chunk overlap 的权衡
- hybrid search
- reranking
- query rewrite / multi-query
- metadata filtering
- citation / provenance
- retrieval eval 与 answer eval

### 项目任务

1. 对同一语料做 2-3 套 chunking 对比
2. 加一个 reranker
3. 做一个最小评测集
4. 对 bad case 做误差分析

### 必须理解

- 召回差不等于生成差，反之也成立
- `RAG` 的优化重点通常在 retrieval，不在提示词花活
- 评测必须分 retrieval 和 generation 两层

### 查验问题

- 你如何判断问题出在召回还是出在生成？
- hybrid search 什么时候优于纯向量检索？
- reranker 放在系统里的位置是什么？

### 通过标准

- 能独立做一轮 `RAG` 误差分析
- 能说清 chunk、embedding、retriever、reranker 各自的优化点

## 阶段 4：ReAct 与 Tool Use

### 目标

掌握“思考 + 调工具 + 继续推理”的基础 Agent 模式。

### 需要掌握

- tool calling / function calling
- `ReAct` 思路
- tool observation
- tool error handling
- iteration limit
- stop condition

### 项目任务

1. 做一个会查天气 / 搜索 / 计算器的 Agent
2. 限制最大迭代次数
3. 记录每一步工具调用轨迹

### 必须理解

- `ReAct` 的价值在于把“外部行动”纳入推理回路
- 不是所有任务都需要 Agent loop
- 工具越多不一定越好，选择空间会带来额外错误

### 查验问题

- `ReAct` 和普通 chain 的差异是什么？
- tool schema 为什么常被问？
- Agent 无限循环时通常先查哪里？

### 通过标准

- 能实现一个可观测的最小 `ReAct` Agent
- 能解释每一步 observation 如何影响下一步决策

## 阶段 5：LangGraph 与 Stateful Agent

### 目标

从“线性链”升级到“显式状态机 / 图式编排”。

### 需要掌握

- state graph
- node / edge
- checkpoint
- persistence
- interrupt / human-in-the-loop
- retry / fallback

### 项目任务

1. 把前一阶段 Agent 改写成 `LangGraph`
2. 为 graph 增加 checkpoint
3. 增加人工审批节点

### 必须理解

- graph 的核心价值是状态显式化与流程可控
- 复杂 Agent 系统最终都要回到“状态、转移、恢复、观察”
- 一旦需要中断恢复、审批、分支，graph 通常比纯 chain 更稳

### 查验问题

- 什么时候你会从 `LangChain` chain 切到 `LangGraph`？
- checkpoint 为什么是生产系统关键点？
- graph 编排相比黑盒 agent loop 的优势是什么？

### 通过标准

- 能独立写一个 stateful graph
- 能处理失败重试和人工接入

## 阶段 6：多智能体

### 目标

理解多智能体不是“越多越高级”，而是一种带成本的分工设计。

### 需要掌握

- router / supervisor / handoff
- shared memory vs message passing
- task decomposition
- context slicing
- role design
- conflict / deadlock / duplication 风险

### 项目任务

1. 设计一个 research agent + writer agent + reviewer agent
2. 控制每个 agent 的上下文和职责边界
3. 加一套最终裁决机制

### 必须理解

- 多 Agent 首先解决“任务分解和上下文隔离”
- 很多看似多 Agent 的问题，单 Agent + workflow 更简单
- 多 Agent 的核心成本是协调、验证、合并，而不是编码本身

### 查验问题

- 什么情况下你不会用多智能体？
- handoff 和 supervisor 两种模式各适合什么？
- 多 Agent 系统最容易出现哪些失败模式？

### 通过标准

- 能画出一个多 Agent 协作图
- 能说明为什么选多 Agent，而不是单 Agent

## 阶段 7：评测、观测、守护与上线

### 目标

建立生产级 Agent 应用意识。

### 需要掌握

- tracing
- offline eval / online eval
- golden set
- hallucination 与 citation 检查
- prompt / model / retriever A/B
- latency / cost / cache
- policy / guardrails / HITL

### 项目任务

1. 为你的 `RAG` 或 Agent 应用加 tracing
2. 建一个 30-50 条的小评测集
3. 输出成本、延迟、成功率
4. 对危险工具调用加审批或白名单

### 必须理解

- 没有 eval 的 Agent 应用基本不可迭代
- 没有 tracing 就很难做失败定位
- 上线系统关注的不只是“答对没”，还有“成本、速度、稳定性、安全性”

### 查验问题

- 你如何定义一个 Agent 系统的成功指标？
- 线上 bad case 该如何回流到评测集？
- 为什么面试经常问 hallucination、guardrails、tool safety？

### 通过标准

- 能对自己的系统给出最小 eval 报告
- 能说清至少 3 类线上风险和缓解方式

## 阶段 8：微调、LoRA、QLoRA、偏好优化

### 目标

建立“什么时候该微调、怎么微调、微调解决不了什么”的判断力。

### 需要掌握

- `SFT`
- `LoRA` / `QLoRA`
- instruction tuning
- preference data
- `DPO`
- `RLHF` / `RFT` 的基本思想

### 必须理解

- 微调更像“行为塑形”，不是实时知识更新
- 很多知识型问题优先考虑 `RAG`
- 微调项目的关键是数据质量，而不是先调超参
- `DPO` 和传统 `RLHF` 的差别至少要能说出训练链路上的差异

### 查验问题

- 什么问题适合微调，什么问题更适合 `RAG`？
- `LoRA` 为什么能降低训练成本？
- `QLoRA` 和 `LoRA` 的差异是什么？
- `DPO` 和 `RLHF` 的主要区别是什么？

### 通过标准

- 能说清 prompt、`RAG`、微调、偏好优化四者边界
- 能读懂常见微调 / 对齐面试题

## 阶段 9：Capstone

### 目标

把前面的知识拼成一个完整可展示项目。

### 推荐题目

选一个即可：

- 企业知识库问答：`RAG + citation + eval`
- 数据分析助理：`ReAct + SQL / Python tool + approval`
- 研究助理：`search + retrieve + write + review` 多 Agent
- 文档处理代理：`LangGraph + human approval + checkpoint`

### 交付要求

- 明确系统图
- 明确失败模式
- 明确评测集
- 明确成本和延迟
- 明确为什么选 `RAG` / Agent / 微调，而不是别的方案

### 通过标准

- 能在没有教程的情况下独立完成一个端到端项目
- 能回答设计取舍与失败分析问题

## 建议代码里程碑

建议在这个文件夹下逐步产出：

- `01_langchain_basics.py`
- `02_rag_ingest.py`
- `03_rag_query.py`
- `04_rag_eval.py`
- `05_react_agent.py`
- `06_langgraph_agent.py`
- `07_multi_agent_demo.py`
- `08_eval_and_guardrails.py`
- `09_lora_or_dpo_notes.md`
- `10_capstone.md`

## 高频面试主题地图

基于 `interview_sources.md` 里收集的 50+ 篇面经 / 题单，重复出现最多的主题大致是：

1. `RAG` 基础链路：chunking、embedding、vector DB、召回失败分析
2. `RAG` 进阶优化：hybrid search、reranker、query rewrite、citation、eval
3. Agent 基础：tool use、function calling、`ReAct`、memory、stop condition
4. 框架问题：`LangChain`、`LangGraph`、状态管理、checkpoint、workflow vs agent
5. 系统设计：多智能体分工、上下文隔离、路由、失败恢复
6. 工程与上线：tracing、guardrails、cost、latency、hallucination
7. 后训练：`SFT`、`LoRA`、`QLoRA`、`DPO`、`RLHF`

注意：上面这份“高频”是基于社区题单与面经的归纳，不是某一家公司的官方题库。

## 学习顺序建议

不要一开始就冲多智能体。

推荐顺序：

1. `LangChain` 基础
2. 最小 `RAG`
3. `RAG` 评测与优化
4. 单 Agent / `ReAct`
5. `LangGraph`
6. 多智能体
7. 评测、守护、上线
8. 微调与后训练

这是因为：

- 绝大多数面试先问 `RAG`
- 大多数项目失败在 retrieval、eval、tool safety，不是在“Agent 不够高级”
- 多智能体如果没有单 Agent、graph、eval 基础，很容易只剩概念堆砌

## 和当前 Transformer 路线的关系

推荐并行方式：

- 周内主线：继续当前 README 的 Transformer / PyTorch 基础
- 周末副线：做这里的应用项目

如果你当前还在前 0-3 阶段，可以先采用这个节奏：

- 70% 时间：张量、训练循环、`nn.Module`、attention 基础
- 30% 时间：`LangChain`、最小 `RAG`

等你把当前仓库里的注意力和 block 写顺后，再把应用线提高到 50%。

## 直接执行建议

如果你现在就开始学，不要从多智能体开始。

推荐第一轮执行顺序：

1. 看 `official_references.md` 里的入门官方材料
2. 完成 `learning_path_detailed.md` 的阶段 0 和阶段 1
3. 在 `project_roadmap.md` 里先做 `P1 LangChain 最小链`
4. 然后进入阶段 2，完成 `P2 最小 RAG`
5. 再开始刷 `interview_question_map.md` 里的 `RAG` 与 Agent 基础题

如果你想直接按真实面经来推进，而不是按通用教材推进：

1. 先看 `interview_sources.md` 的“已核验真实面经”分区
2. 再看 `real_interview_learning_path.md`
3. 然后按 `study_plan_real_interviews.md` 执行
