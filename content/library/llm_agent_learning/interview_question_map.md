# 高频面试问题地图

这份文档不是题库答案，而是题目框架。

用法：

- 学完一个阶段，就刷对应主题
- 答不出来的问题，回到 `official_references.md`
- 不要死背，尽量用自己的 demo 回答

## 一、LLM 应用总论

1. prompt、`RAG`、tool use、fine-tuning 的边界是什么？
2. 什么问题适合 workflow，什么问题适合 Agent？
3. 为什么多智能体不是默认最优解？
4. 一个 LLM 应用的核心指标通常有哪些？
5. 成本、时延、效果三者怎么 tradeoff？

## 二、LangChain

6. `LangChain` 相比直接调模型 API 的价值是什么？
7. 什么是 chain / runnable？
8. 什么是 structured output？为什么它重要？
9. tool schema 设计为什么会直接影响结果？
10. 什么情况下 `LangChain` 反而会让系统变复杂？

## 三、RAG 基础

11. 什么是 `RAG`？
12. `RAG` 为什么能缓解知识过期问题？
13. 文档切块为什么是高频问题？
14. chunk size 和 overlap 怎么选？
15. embedding model 在 `RAG` 里扮演什么角色？
16. vector DB 在做什么？
17. top-k 为什么不是越大越好？
18. 为什么 `RAG` 不等于把文档喂给模型？

## 四、RAG 优化与排障

19. 如何判断问题发生在 retrieval 还是 generation？
20. hybrid search 什么时候更合适？
21. reranker 和 retriever 的区别是什么？
22. metadata filtering 适合解决什么问题？
23. query rewrite / multi-query 的作用是什么？
24. citation 为什么重要？
25. `RAG` 的 eval 应该怎么做？
26. bad case 一般分哪几类？

## 五、ReAct 与 Tool Use

27. `ReAct` 是什么？
28. `ReAct` 和普通 chain 的区别是什么？
29. function calling / tool calling 是什么？
30. tool schema 为什么是工程关键点？
31. 为什么工具不是越多越好？
32. observation 在 Agent loop 里的作用是什么？
33. Agent 死循环一般怎么排查？
34. 怎么设计 stop condition？

## 六、LangGraph 与状态编排

35. 什么时候应该从 `LangChain` 切到 `LangGraph`？
36. state graph 的核心价值是什么？
37. checkpoint 为什么重要？
38. 什么是 human-in-the-loop？
39. graph 相比黑盒 agent loop 更强在哪里？
40. retry / fallback 应该放在哪一层考虑？

## 七、多智能体

41. 什么情况下你不会用多智能体？
42. supervisor 和 handoff 的区别是什么？
43. router 适合解决什么问题？
44. shared memory 和 message passing 各有什么问题？
45. 多智能体最容易出现哪些失败模式？
46. 如何避免上下文爆炸和重复劳动？
47. 多 Agent 的最终裁决应该怎么设计？

## 八、评测、观测、守护

48. 为什么没有 eval 的 LLM 应用很难迭代？
49. offline eval 和 online eval 的区别是什么？
50. golden set 应该怎么构建？
51. tracing 能帮助你定位什么问题？
52. hallucination 如何度量和缓解？
53. tool safety / guardrails 为什么关键？
54. 如何做成本与时延优化？
55. 线上 bad case 如何回流到评测集？

## 九、微调与后训练

56. 什么问题更适合微调，什么问题更适合 `RAG`？
57. `SFT` 解决什么问题？
58. `LoRA` 为什么便宜？
59. `QLoRA` 相比 `LoRA` 多了什么？
60. preference data 是什么？
61. `DPO` 与 `RLHF` 的主要差异是什么？
62. 为什么说微调更像行为塑形，而不是知识注入？
63. 做微调项目时，数据质量为什么比先调超参更重要？

## 十、系统设计题

64. 设计一个企业知识库问答系统，你会怎么做？
65. 设计一个会查库、会算数、会写报告的分析助手，你会怎么做？
66. 如果工具调用风险很高，你会加哪些保护？
67. 如果用户说系统很慢，你会优先查哪些地方？
68. 如果用户说系统不准，你会如何分层排查？
69. 如果老板说要上多智能体，你会先问哪些问题？
70. 如果模型效果不稳定，你会如何设计最小实验来定位问题？

## 刷题方式建议

一轮不要刷太多。

推荐节奏：

1. 每学完一个阶段，刷 5 到 10 题
2. 每题先口答，再写答题框架
3. 最后拿自己的 demo 举例

如果你答题时总是空泛，通常说明你还没有真正做过对应 demo。
