# 周学习计划

这是按 10 周设计的标准节奏。

如果你每周时间少，就把每一周拉长成两周。

## 第 1 周：建立系统视角

### 学习内容

- LLM 应用分层
- prompt / tool / `RAG` / fine-tuning 边界
- `LangChain` 基本组件

### 本周产出

- 一页系统图
- 一页概念边界笔记

### 本周问题

- 为什么不是所有问题都该做 Agent
- 为什么应用开发先是系统设计

## 第 2 周：LangChain 最小链

### 学习内容

- prompt template
- structured output
- tool 定义

### 本周产出

- `01_langchain_basics.py`

### 本周问题

- 结构化输出为什么重要
- tool schema 为什么重要

## 第 3 周：最小 RAG

### 学习内容

- ingest
- chunking
- embedding
- retrieval

### 本周产出

- `02_rag_ingest.py`
- `03_rag_query.py`

### 本周问题

- chunk 太大和太小分别会坏在哪里
- 为什么检索质量不是单看 embedding model

## 第 4 周：RAG 评测与优化

### 学习内容

- retrieval eval
- answer eval
- rerank / hybrid search

### 本周产出

- `04_rag_eval.py`
- 一份 bad case 报告

### 本周问题

- 如何区分召回问题和生成问题
- 为什么 eval 不能只有一个总分

## 第 5 周：ReAct 与 Tool Use

### 学习内容

- function calling
- `ReAct`
- stop condition
- retry

### 本周产出

- `05_react_agent.py`

### 本周问题

- 普通 chain 和 `ReAct` 的区别是什么
- Agent 死循环先查哪里

## 第 6 周：LangGraph

### 学习内容

- state graph
- checkpoint
- interrupt
- approval

### 本周产出

- `06_langgraph_agent.py`
- 一张状态图

### 本周问题

- 为什么 graph 更适合长流程
- checkpoint 为什么关键

## 第 7 周：多智能体

### 学习内容

- role design
- router / supervisor
- handoff
- context isolation

### 本周产出

- `07_multi_agent_demo.py`

### 本周问题

- 为什么这里真的需要多 Agent
- 多 Agent 比单 Agent 多出的工程成本是什么

## 第 8 周：评测与守护

### 学习内容

- tracing
- eval set
- latency / cost
- guardrails

### 本周产出

- `08_eval_and_guardrails.py`
- 一份最小系统评测报告

### 本周问题

- 没有 tracing 为什么很难迭代
- tool safety 为什么是核心问题

## 第 9 周：微调与后训练

### 学习内容

- `SFT`
- `LoRA`
- `QLoRA`
- `DPO`
- `RLHF`
- `RFT`

### 本周产出

- `09_lora_or_dpo_notes.md`

### 本周问题

- 为什么知识更新优先看 `RAG`
- `DPO` 与 `RLHF` 的链路差别是什么

## 第 10 周：Capstone

### 学习内容

- 整体系统拼装
- 失败分析
- 指标定义
- 项目讲解

### 本周产出

- `10_capstone.md`
- 最终演示项目

### 本周问题

- 为什么你的设计合理
- 这个系统的主要风险是什么
- 如何继续迭代

## 每周固定动作

每周都做这 5 件事：

1. 至少跑通一个可执行 demo
2. 记录 3 个 bad case
3. 回答 5 个高频面试题
4. 写一页总结
5. 对照官方文档修正自己的理解
