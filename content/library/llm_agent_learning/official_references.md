# 官方资料与关键论文

这份文档只收两类材料：

- 真正应该优先看的官方文档
- 构成主干概念的关键论文

使用规则：

- 做实现时，优先看官方文档
- 做概念溯源时，再看关键论文
- 准备面试时，用社区题单找高频题，用这份文档校正答案

## 一、官方文档

### 框架与 Agent 编排

1. LangChain Overview  
https://docs.langchain.com/oss/python/langchain/overview

2. LangGraph Overview  
https://docs.langchain.com/oss/python/langgraph/overview

3. OpenAI Agents SDK Guide  
https://developers.openai.com/api/docs/guides/agents

4. OpenAI Agents SDK Python / JS Docs  
https://openai.github.io/openai-agents-python/  
https://openai.github.io/openai-agents-js/

5. Anthropic Tool Use Overview  
https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

6. Model Context Protocol Introduction  
https://modelcontextprotocol.io/docs/getting-started/intro

7. Model Context Protocol Specification Overview  
https://modelcontextprotocol.io/specification/2025-06-18/basic

### RAG、检索、评测

8. OpenAI File Search Guide  
https://developers.openai.com/api/docs/guides/tools-file-search

9. OpenAI File Search Cookbook Example  
https://cookbook.openai.com/examples/file_search_responses

10. OpenAI Evals Guide  
https://developers.openai.com/api/docs/guides/evals

### Prompt、成本、生产化

11. OpenAI Prompt Engineering Best Practices  
https://help.openai.com/en/articles/6654000-comprehensive-cdot-prompt-engineering-guide-for-developers

12. OpenAI Prompt Caching Guide  
https://developers.openai.com/api/docs/guides/prompt-caching

### 微调与后训练

13. OpenAI Fine-Tuning Guide  
https://developers.openai.com/api/docs/guides/model-optimization

14. OpenAI Fine-Tuning API Reference  
https://platform.openai.com/docs/api-reference/fine-tuning

15. OpenAI Reinforcement Fine-Tuning Guide  
https://developers.openai.com/api/docs/guides/reinforcement-fine-tuning

16. Hugging Face TRL Docs  
https://huggingface.co/docs/trl/index

## 二、关键论文

### Agent / ReAct

1. ReAct: Synergizing Reasoning and Acting in Language Models  
https://arxiv.org/abs/2210.03629

### RAG

2. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks  
https://arxiv.org/abs/2005.11401

### 对齐 / RLHF

3. Training Language Models to Follow Instructions with Human Feedback  
https://arxiv.org/abs/2203.02155

### 参数高效微调

4. LoRA: Low-Rank Adaptation of Large Language Models  
https://arxiv.org/abs/2106.09685

5. QLoRA: Efficient Finetuning of Quantized LLMs  
https://arxiv.org/abs/2305.14314

### 偏好优化

6. Direct Preference Optimization: Your Language Model is Secretly a Reward Model  
https://arxiv.org/abs/2305.18290

## 三、怎么用这些资料

### 入门顺序

1. 先看 LangChain 和 LangGraph Overview
2. 再看 OpenAI File Search / Evals / Agents SDK
3. 再看 Anthropic Tool Use 和 MCP
4. 最后再补 LoRA、DPO、RLHF 相关官方与论文

### 实践顺序

1. 用官方文档先跑最小 demo
2. 对照论文理解为什么这样设计
3. 再回到你的项目里做裁剪和替换

### 纠偏原则

- 社区博客适合找题，不适合做最终依据
- 论文适合理解方法来源，不适合作为生产实现说明书
- 官方文档最适合回答“现在应该怎么做”

## 四、阅读重点

读官方文档时，不要只盯 API 名称，要重点看：

1. 框架在解决什么问题
2. 官方推荐什么场景用它
3. 官方明确不建议拿它做什么
4. 状态、工具、评测、恢复这些工程问题怎么处理
