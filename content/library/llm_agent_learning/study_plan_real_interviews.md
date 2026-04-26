# 基于真实面经的执行计划文档

这是一份按真实面经高频主题倒推的执行计划。

适用目标：

- 你想优先满足真实招聘中的高频考点
- 你不想平均学习所有主题
- 你希望每一周都有明确产出

建议周期：

- 标准版：`8` 周
- 时间紧张版：`6` 周
- 时间充裕版：把每周拉成 `2` 周

## 总体策略

这份计划的核心思想只有一句：

先把真实面经最常问、最能落地、最容易追问的部分打穿。

优先级排序：

1. `RAG`
2. tool use / Agent
3. workflow / `LangGraph`
4. eval / guardrails
5. 多智能体
6. 微调 / 后训练

## 第 1 周：应用开发基本盘

### 目标

补齐应用岗默认前置概念。

### 学习内容

- prompt、tool、`RAG`、fine-tuning 的边界
- chat model / embedding model
- structured output
- 向量检索最小链路

### 本周产出

- 一页系统图
- 一页边界总结
- 一个最小 `LangChain` demo

### 必答问题

- 为什么不是所有问题都该做 Agent
- `RAG` 和微调分别解决什么问题

## 第 2 周：最小 RAG

### 目标

先把最核心主线跑通。

### 学习内容

- 文档 ingest
- chunking
- embedding
- retrieval
- answer with citations

### 本周产出

- `02_rag_ingest.py`
- `03_rag_query.py`
- 一份最小语料

### 必答问题

- chunk size / overlap 怎么选
- 为什么召回错了生成通常也会错

## 第 3 周：RAG 优化与排障

### 目标

把“能跑”升级到“会调”。

### 学习内容

- retrieval vs generation 定位
- reranker
- hybrid search
- metadata filter
- bad case 分类

### 本周产出

- `04_rag_eval.py`
- 一份 `RAG` bad case 报告

### 必答问题

- 你怎么判断问题在召回还是在生成
- reranker 和 retriever 的区别是什么

## 第 4 周：单 Agent 与 Tool Use

### 目标

补齐真实面经中的第二大主线。

### 学习内容

- function calling
- tool schema
- `ReAct`
- stop condition
- retry / fallback

### 本周产出

- `05_react_agent.py`
- 一份工具调用 trace

### 必答问题

- 普通 chain 和 Agent 的区别是什么
- Agent 为什么会死循环

## 第 5 周：Workflow 与 LangGraph

### 目标

从“会调工具”提升到“会设计有状态流程”。

### 学习内容

- state graph
- checkpoint
- interrupt
- human approval
- recovery path

### 本周产出

- `06_langgraph_agent.py`
- 一张状态图

### 必答问题

- 为什么这里需要 `LangGraph`
- checkpoint 为什么重要

## 第 6 周：评测、守护、成本

### 目标

补齐工程闭环。

### 学习内容

- tracing
- eval set
- hallucination / citation checks
- latency / cost
- tool safety

### 本周产出

- `08_eval_and_guardrails.py`
- 一份最小 eval 报告

### 必答问题

- 没有 eval 怎么定位系统问题
- 工具调用风险怎么控制

## 第 7 周：多智能体

### 目标

只在你已经会单 Agent 和 workflow 以后再学分工系统。

### 学习内容

- supervisor
- router
- handoff
- role scope
- merge / arbitration

### 本周产出

- `07_multi_agent_demo.py`
- 一份多角色设计说明

### 必答问题

- 为什么这里真的需要多 Agent
- 多 Agent 比单 Agent 多了什么成本

## 第 8 周：微调与后训练

### 目标

补齐算法岗常见追问和方案比较能力。

### 学习内容

- `SFT`
- `LoRA`
- `QLoRA`
- `DPO`
- `RLHF`
- `RFT`

### 本周产出

- `09_lora_or_dpo_notes.md`
- 一页方案对比表：prompt / `RAG` / `SFT` / `DPO`

### 必答问题

- 为什么很多知识问题优先选 `RAG`
- `DPO` 和 `RLHF` 的主要区别是什么

## 每周固定动作

每周都做这 6 件事：

1. 跑通一个最小 demo
2. 写一页总结
3. 记录至少 `3` 个 bad case
4. 回答至少 `5` 个真实面经高频问题
5. 用 `official_references.md` 校正理解
6. 把本周产出整理到仓库里

## 每周自检清单

每周结束前，检查这 5 条：

1. 我能不用照抄教程把本周 demo 重新写一遍吗
2. 我能解释本周系统为什么这样设计吗
3. 我知道本周系统最常见的失败模式吗
4. 我知道如何评估本周系统是否真的变好了吗
5. 我能拿自己的 demo 回答本周高频题吗

## 最终交付目标

8 周结束后，至少要有这些东西：

- 一个可运行的 `RAG` 系统
- 一个可运行的 tool-use Agent
- 一个有状态的 `LangGraph` demo
- 一份最小 eval 报告
- 一份多智能体设计样例
- 一份微调 / 后训练对比笔记

## 最后建议

如果你当前时间有限，宁可把 `RAG + Agent + Eval` 做深，也不要急着把多智能体和后训练都浅尝一遍。

因为从真实面经看，前者的收益远高于后者。
