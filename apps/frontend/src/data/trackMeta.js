export const trackMeta = {
  foundations: {
    id: "foundations",
    label: "模型基础线",
    title: "PyTorch 到手写 Transformer",
    strapline: "从张量、训练循环一路走到 attention、位置编码和 decoder-only Transformer。",
    level: "模型原理 / 训练直觉",
    path: "content/library/learning_tracks/pytorch_to_transformer",
    outcomes: [
      "建立 tensor、shape、广播和矩阵乘法的直觉",
      "理解 autograd、训练循环和参数更新",
      "手写 attention、位置编码、FFN 和 LayerNorm",
      "最终拼出可训练的最小 Transformer",
    ],
  },
  "llm-apps": {
    id: "llm-apps",
    label: "应用系统线",
    title: "AI 大模型接入与 Agent 系统",
    strapline: "从现成模型接入出发，走到 RAG、Tool Use、LangGraph、评测与守护。",
    level: "系统设计 / 工程闭环",
    path: "content/library/llm_agent_learning",
    outcomes: [
      "区分 prompt、tool、RAG 和微调的边界",
      "搭出可解释、可评测的最小 RAG",
      "设计有状态的 workflow 和 graph",
      "建立 tracing、eval、guardrails、成本与时延视角",
    ],
  },
};

export const decisionGuide = [
  {
    label: "Prompt",
    answer: "解决表达、约束和输出格式，不负责补足外部事实。",
  },
  {
    label: "Tool Use",
    answer: "解决搜索、计算、查库、调用外部系统这类动作能力。",
  },
  {
    label: "RAG",
    answer: "解决私有知识、动态知识、可引用知识和可追溯回答。",
  },
  {
    label: "Fine-Tuning",
    answer: "更像行为塑形，不是知识更新的默认第一选择。",
  },
];
