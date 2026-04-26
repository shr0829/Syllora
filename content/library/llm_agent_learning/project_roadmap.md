# 项目路线与里程碑

这份文档只关心“做什么项目”，不讲大段概念。

## 项目 P1：LangChain 最小链

### 目标

学会最基本的应用编排。

### 功能范围

- 一个 prompt template
- 一个模型调用
- 一个结构化输出
- 一个最小工具

### 交付物

- `01_langchain_basics.py`
- `README` 说明如何运行
- 3 个测试输入与输出样例

### 验收

- 输出能稳定解析
- 工具调用能跑通

## 项目 P2：最小 RAG

### 目标

做出第一套“能问文档”的系统。

### 功能范围

- ingest 文档
- chunk
- embed
- retrieve
- answer with citations

### 交付物

- `02_rag_ingest.py`
- `03_rag_query.py`
- 一份小语料
- 一个示例问答脚本

### 验收

- 至少 10 个问题里，大部分答案能回到正确片段
- 答案里带引用，不是纯裸答

## 项目 P3：RAG 评测与优化

### 目标

第一次建立误差分析习惯。

### 功能范围

- 两套 chunking
- 一个 reranker 或 hybrid search
- 一个小型 eval 集
- 一份 bad case 分析

### 交付物

- `04_rag_eval.py`
- `eval_dataset.jsonl`
- `rag_eval_report.md`

### 验收

- 不是只报一个总分
- 至少能指出 3 类失败模式

## 项目 P4：ReAct Agent

### 目标

学会把工具调用纳入推理流程。

### 功能范围

- 至少 2 个工具
- 至少 1 个多步任务
- 步骤日志
- 失败保护

### 交付物

- `05_react_agent.py`
- `agent_trace_example.md`

### 验收

- 能处理一次真实多步任务
- 出错时不会无限循环

## 项目 P5：LangGraph Stateful Agent

### 目标

把 Agent 从 demo 升级成可控工作流。

### 功能范围

- state graph
- checkpoint
- retry
- human approval

### 交付物

- `06_langgraph_agent.py`
- `langgraph_state_diagram.md`

### 验收

- 支持中断恢复
- 支持至少一个审批节点

## 项目 P6：多智能体协作

### 目标

验证你是否真的理解多角色分工。

### 功能范围

- researcher
- writer
- reviewer
- aggregator

### 交付物

- `07_multi_agent_demo.py`
- `multi_agent_design.md`

### 验收

- 每个角色职责清晰
- 最终输出不是简单拼接

## 项目 P7：评测与守护

### 目标

补齐上线前必须考虑的工程面。

### 功能范围

- tracing
- dataset-based eval
- cost logging
- latency logging
- guardrails
- approval / whitelist

### 交付物

- `08_eval_and_guardrails.py`
- `system_eval_report.md`

### 验收

- 能跑一轮最小评测
- 能输出成本与延迟
- 能说明风险控制点

## Capstone 候选

### C1 企业知识库问答

核心组合：

- `RAG`
- citation
- eval
- access control

### C2 数据分析助理

核心组合：

- `ReAct`
- SQL tool
- Python tool
- approval

### C3 研究助理

核心组合：

- search
- retrieve
- summarize
- write
- review
- multi-agent optional

### C4 审批型文档代理

核心组合：

- `LangGraph`
- state
- checkpoint
- human approval
- audit trail

## 交付检查表

每个项目至少回答这些问题：

1. 用户输入是什么
2. 模型调用发生在哪里
3. 外部工具或检索发生在哪里
4. 失败时怎么发现
5. 失败时怎么恢复
6. 成本和时延大头在哪
7. 为什么这个设计比更简单的替代方案更值得
