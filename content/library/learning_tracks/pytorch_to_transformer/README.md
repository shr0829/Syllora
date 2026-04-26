# PyTorch 到手写 Transformer 学习轨

这个目录现在是 Syllora 的“基础模型实现线”。

如果你是从仓库根目录进入，请先看：

- 根项目定义：`../../README.md`
- 应用系统学习轨：`../../llm_agent_learning/README.md`

下面保留原始学习路线内容，用于集中学习 PyTorch、attention 和手写 Transformer。

# Transformer 手写学习路线

这份路线默认你已经有机器学习基础，能理解常见概念，也写过传统 ML 代码。目标不是“看懂 Transformer”，而是最终能够自己从零实现、训练并调试一个可运行的 mini Transformer。

## 总目标

完成阶段 0 到阶段 9 后，你应当能够：

- 熟练使用 PyTorch 写模型、训练、验证、保存、加载
- 理解张量维度流转，不再被 shape bug 卡住
- 理解 attention、self-attention、multi-head attention
- 自己写 Embedding、mask、位置编码、attention、FFN、残差、LayerNorm
- 自己拼出一个 Decoder-only Transformer
- 在小文本数据集上训练并生成文本
- 不依赖 `nn.Transformer`，手写核心模块

## 学习原则

每一阶段都遵循同一套动作：

1. 先理解模块作用
2. 再手写最小实现
3. 再打印 shape 跑通
4. 最后脱离教程重写

每个阶段都要有验收标准；不到标准，不跳下一阶段。

## 补充并行路线

如果你要并行学习“大模型应用开发 / Agent 开发”而不是只做底层 Transformer 手写，这个仓库现在新增了一条独立路线：

- `llm_agent_learning/README.md`：从 `LangChain` 开始，到 `RAG`、`ReAct`、`LangGraph`、多智能体、评测、微调与后训练
- `llm_agent_learning/learning_path_detailed.md`：逐阶段执行版学习路径
- `llm_agent_learning/project_roadmap.md`：demo / capstone 项目路线
- `llm_agent_learning/weekly_plan.md`：按周学习计划
- `llm_agent_learning/official_references.md`：官方文档与关键论文
- `llm_agent_learning/interview_question_map.md`：高频面试问题地图
- `llm_agent_learning/interview_sources.md`：大模型应用开发与 Agent 开发相关面经 / 题单 / 问题整理索引（50+ 来源）

建议把这条路线当成“并行应用线”：

- 当前 README 解决“模型与训练原理”
- 新路线解决“基于现成模型做应用、工具调用、检索增强与 Agent 系统”

## 阶段 0：准备与心智切换

### 目标

从“传统 ML 思维”切换到“深度学习 + 张量计算思维”。

### 重点认知

传统 ML 通常是：

- 特征工程
- 调 sklearn API
- `fit` / `predict`

深度学习更像是：

- 数据转成 tensor
- 自己定义计算图
- 前向传播
- 计算 loss
- 反向传播
- 参数更新
- 多轮迭代训练

### 需要掌握

- 样本、batch、feature、channel、sequence 的区别
- 参数矩阵的意义
- 前向传播和反向传播是什么
- epoch、iteration、step 的区别
- train、val、test 的区别
- 过拟合、欠拟合、学习率、batch size 的作用

### 练习

- 用自己的话写出什么是神经网络
- 用自己的话写出什么是梯度下降
- 用自己的话写出为什么深度学习训练要迭代很多轮
- 画出 `输入 -> 模型 -> loss -> backward -> optimizer.step` 流程图

### 查验问题

- 为什么深度学习不是一次 `fit` 就结束？
- loss 和 metric 有什么区别？
- 为什么要把数据分 batch？
- 模型参数是在哪里更新的？

### 通过标准

- 能口头解释完整训练流程
- 知道深度学习代码主循环长什么样

## 阶段 1：PyTorch 基础与 Tensor 操作

### 目标

建立 PyTorch 的基本操作能力。

### 需要掌握

- `torch.tensor`
- `dtype`
- `device`
- `shape`
- `reshape` / `view`
- `unsqueeze` / `squeeze`
- `transpose` / `permute`
- 广播机制
- `matmul`
- 索引和切片

### 关键维度

你必须非常熟悉以下形状：

- `[B, D]`
- `[B, T, C]`
- `[B, H, T, D]`

因为后续 Transformer 大量使用这些维度。

### 练习

1. 创建各种 tensor
2. 做切片、拼接、转置
3. 手写矩阵乘法例子并检查输出 shape
4. 对 `[2, 3, 4]` tensor 练习 `reshape` / `permute`

### 必做任务

- 手动构造一个 batch 输入
- 打印每一步的 shape
- 用 `torch.matmul` 模拟线性层计算

### 查验问题

- `x.shape = [32, 10, 64]` 表示什么？
- `transpose(1, 2)` 后 shape 是什么？
- `permute(0, 2, 1)` 和 `reshape` 的区别是什么？
- 为什么有些操作后需要 `contiguous()` 才能 `view()`？

### 通过标准

- 不查资料，能熟练写常见 tensor 变形
- 看到 shape 能大致推断含义

## 阶段 2：Autograd 与最小训练循环

### 目标

理解 PyTorch 如何自动求导，以及训练是怎么跑起来的。

### 需要掌握

- `requires_grad=True`
- `loss.backward()`
- 梯度存在哪里
- `optimizer.zero_grad()`
- `optimizer.step()`

### 核心理解

- `forward` 负责算预测值
- `loss` 负责算预测误差
- `backward` 自动计算每个参数的梯度
- `optimizer.step` 用梯度更新参数

### 练习

1. 手写线性回归
2. 手写 logistic regression / 二分类
3. 打印参数更新前后的值

### 推荐任务

- 用纯 PyTorch tensor，不继承 `nn.Module`，手写一次线性回归
- 再用 `nn.Linear` 写一次

### 查验问题

- 为什么每轮都要 `zero_grad()`？
- 梯度不清零会怎样？
- `backward` 后哪些对象发生了变化？
- 为什么 loss 能驱动参数往更优方向更新？

### 通过标准

- 能独立写一个最小训练循环
- 能看到 loss 下降
- 知道训练失败时优先查哪些问题

## 阶段 3：nn.Module、Dataset、DataLoader、完整训练工程

### 目标

掌握 PyTorch 标准工程化写法。

### 需要掌握

- `nn.Module`
- `DataLoader`
- `train` / `eval` 模式
- 保存与加载模型
- metric 统计

### 项目任务

1. MNIST 手写数字分类
2. 至少实现两个模型版本：

- MLP
- 简单 CNN

### 要练的能力

- 数据读取
- batch 训练
- 验证集评估
- accuracy 统计
- 模型 checkpoint 保存

### 目标产出

- 标准 PyTorch 项目目录
- `train.py`
- `model.py`
- `dataset.py`
- `utils.py` 或简单工具函数

### 查验问题

- `model.train()` 和 `model.eval()` 的区别是什么？
- `DataLoader(shuffle=True)` 为什么重要？
- 为什么训练集 loss 下降但验证集不一定变好？
- 如何保存“最佳模型”而不是“最后模型”？

### 通过标准

- 能独立训练一个可用分类器
- 代码结构不再全部堆在 notebook
- 会记录 loss / accuracy 曲线

## 阶段 4：深度学习基本模块与调参直觉

### 目标

补齐进入 Transformer 前必须具备的训练直觉。

### 需要掌握

- 激活函数：ReLU / GELU
- 初始化的基本概念
- 学习率、batch size、weight decay
- dropout 的作用
- normalization 的基本作用
- 为什么深层网络训练会不稳定

### 重点理解

Transformer 能训练稳定，不只靠 attention，还依赖：

- residual
- layer norm
- 合理学习率
- 合理初始化
- 合理 loss 设计

### 练习

- 同一模型尝试不同学习率，观察 loss 曲线
- 比较加 dropout / 不加 dropout 的差异
- 调整 batch size，观察训练稳定性

### 查验问题

- 学习率过大会发生什么？
- 学习率过小会发生什么？
- dropout 是训练时做什么？
- 深层网络为什么容易训练不稳？

### 通过标准

- 对训练曲线有基本诊断能力
- 遇到 loss 不下降，不会只会怀疑“代码坏了”

## 阶段 5：序列建模基础

### 目标

进入 NLP / Transformer 所需的输入表示与序列概念。

### 需要掌握

- token
- vocab
- id 映射
- embedding
- padding
- sequence length
- mask
- next token prediction
- teacher forcing

### 核心理解

Transformer 处理的是 token 序列，而不是表格特征。

### 必做练习

1. 自己实现一个最小 tokenizer
2. 建一个 vocab
3. 把文本转成 id
4. 用 `nn.Embedding` 把 id 转成向量

最简单的起点可以是字符级 tokenizer。

### 推荐项目

- 字符级文本分类
- `Embedding + 平均池化 + Linear` 做小文本分类
- `Embedding + LSTM` 做入门序列建模

### 必须理解

- 为什么 token id 不能直接喂给线性层
- embedding 本质上是什么
- 为什么序列要 padding
- mask 为什么必要

### 查验问题

- `Embedding(vocab_size, d_model)` 的输入输出 shape 是什么？
- padding token 为什么不能像正常 token 一样参与计算？
- 文本生成任务的监督信号怎么构造？

### 通过标准

- 能独立把原始文本变成训练样本
- 理解 `[B, T] -> [B, T, C]`

## 阶段 6：Attention 机制基础

### 目标

在上 Transformer 之前，彻底理解 attention 的本质。

### 需要掌握

- Query / Key / Value
- 相似度打分
- softmax 权重
- 加权求和
- attention 是“选择性聚合信息”

### 核心公式

`Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V`

重点不是背公式，而是理解每一步在做什么。

### 必做练习

1. 用一个很小的 3x3 或 4x4 示例手算 attention
2. 用 PyTorch 写单头 attention
3. 打印以下中间结果：

- score matrix
- softmax 权重
- attention 输出

### 必须理解

- `QK^T` 为什么表示相关性
- 为什么除以 `sqrt(d_k)`
- 为什么 softmax 后每一行和为 1
- 为什么最终是对 `V` 做加权汇总

### 查验问题

- Q、K、V 分别是什么角色？
- 为什么不是直接拿输入相加，而是做加权求和？
- attention 输出和输入长度为什么保持一致？

### 通过标准

- 不看资料，能写出单头 attention 的 `forward`
- 能解释每个 tensor 的 shape

## 阶段 7：Self-Attention 与 Multi-Head Attention

### 目标

进入 Transformer 核心模块实现。

### 需要掌握

- self-attention
- multi-head attention
- causal mask
- padding mask
- 头的拆分和拼接

### 典型维度流

- 输入：`[B, T, C]`
- 投影后：`Q, K, V = [B, T, C]`
- 分头后：`[B, H, T, D]`
- score：`[B, H, T, T]`
- 输出：`[B, T, C]`

其中 `C = H * D`

### 必做练习

1. 手写 `MultiHeadAttention`
2. 支持 mask
3. 支持 causal mask
4. 支持 batch 输入
5. 打印每一步 shape

### 必须理解

- 为什么要多头而不是一个头做大一点
- 为什么要 transpose
- 为什么 causal mask 能阻止偷看未来
- 为什么 decoder 做 next-token prediction 必须用 causal mask

### 查验问题

- 如果 `x.shape=[32,128,256]` 且 `num_heads=8`，每个 head 的维度是多少？
- attention score 为什么是 `[B, H, T, T]`？
- causal mask 应该加在 softmax 前还是后？

### 通过标准

- 能独立写出 `MultiHeadAttention`
- mask 逻辑正确
- 不再被 head 维度拆分卡住

## 阶段 8：Transformer Block 组件拼装

### 目标

补齐 Transformer Block 的剩余组件，并拼成完整 block。

### 需要掌握

- positional encoding / positional embedding
- feed-forward network
- residual connection
- layer normalization
- pre-norm / post-norm 基本区别

### 典型 Decoder-only Block

1. 输入 token embedding
2. 加位置编码
3. masked self-attention
4. residual + layer norm
5. feed-forward
6. residual + layer norm

### 必做练习

1. 写位置编码
2. 先写 learned positional embedding
3. 再写 sinusoidal positional encoding
4. 写 `FeedForward`
5. 写 `TransformerBlock`
6. 多个 block 堆叠

### 必须理解

- Transformer 没有卷积和循环，为什么还需要位置编码
- FFN 为什么对每个位置单独处理
- residual 为什么重要
- layer norm 为什么常见于 Transformer

### 查验问题

- 如果没有位置编码，Transformer 会出什么问题？
- FFN 为什么不是多余的线性层？
- residual 对梯度传播有什么帮助？

### 通过标准

- 能写出完整 block
- 能清楚说明 block 内每一步的作用

## 阶段 9：手写完整 Mini Transformer 并训练文本生成

### 目标

把前面所有模块串起来，训练一个真正能生成文本的小模型。

### 推荐路线

先做 Decoder-only Transformer，不要一开始做 encoder-decoder。

### 模型最小组成

- token embedding
- positional embedding / encoding
- N 个 Transformer block
- final layer norm
- lm head（输出到 vocab）

### 数据任务建议

从最简单开始：

1. 字符级文本生成
2. 小语料 next-token prediction
3. 古诗、英文短句、小说片段等小样本生成

### 完整链路

1. 原始文本读取
2. tokenizer / vocab 构建
3. 文本切片成训练样本
4. 构造输入 `x` 和标签 `y`
5. 训练循环
6. 验证 loss
7. 采样生成文本

### 必做练习

- 自己写 `generate()` 函数
- 支持 greedy 或 temperature sampling
- 用训练后的模型生成一段文本
- 对生成质量做简单评估

### 必须理解

- 训练时标签为什么是“右移一位”
- 推理时为什么是自回归生成
- 为什么训练和生成流程不完全一样
- 为什么序列长度会影响显存和计算量

### 查验问题

- 输入序列 `x` 和标签 `y` 的对应关系是什么？
- 为什么训练时能并行，生成时通常逐 token？
- vocab logits 的 shape 是什么？
- loss 是怎么从 `[B, T, V]` 和 `[B, T]` 算出来的？

### 通过标准

- 能训练一个 mini GPT 风格模型
- loss 能明显下降
- 能生成可读、带模式感的文本
- 不看教程能重写一次核心结构

## 每个阶段的统一验收表

每过一阶段，都用下面 5 条检查自己：

1. 我能不用复制教程，独立把这个阶段核心代码写出来吗？
2. 我能解释这一阶段所有主要 tensor 的 shape 吗？
3. 我知道这个模块解决什么问题吗？
4. 我知道训练失败时最可能查哪些点吗？
5. 我能把这个模块接到下一个阶段里吗？

如果有 2 条以上答不上来，不要往后跳。

## 建议项目路线

建议按这个顺序推进：

1. 线性回归
2. 二分类 MLP
3. MNIST MLP
4. MNIST CNN
5. 文本预处理 + `nn.Embedding`
6. 单头 attention
7. multi-head attention
8. 单个 transformer block
9. mini decoder-only transformer
10. 文本生成

## 建议代码里程碑

每一阶段至少产出一个可运行脚本。建议累计形成以下文件：

- `01_tensor_basics.py`
- `02_linear_regression.py`
- `03_mlp_mnist.py`
- `04_cnn_mnist.py`
- `05_text_dataset.py`
- `06_single_head_attention.py`
- `07_multi_head_attention.py`
- `08_transformer_block.py`
- `09_mini_gpt.py`
- `10_generate.py`

这样最后会留下完整的成长轨迹。

## 学习情况量化指标

### 阶段 1-3

- 能独立写 PyTorch 训练循环
- 能在分类任务上跑通训练
- 能解释模型输入输出 shape
- 连续 3 次不依赖教程写出 MLP / CNN 训练脚本

### 阶段 4-5

- 能自己做文本 id 化
- 能独立使用 Embedding
- 能解释 padding 和 mask 的作用
- 能构造 next-token prediction 数据

### 阶段 6-8

- 能独立写 attention
- 能解释 Q、K、V 和多头拆分
- 能实现 causal mask
- 能手写 Transformer block

### 阶段 9

- 模型 loss 稳定下降
- 能生成文本
- 能解释完整数据流和模型流
- 不看教程能重写 mini Transformer

## 常见卡点与排查

### 1. loss 不下降

优先检查：

- 学习率
- 标签是否对齐
- mask 是否写错
- logits / target shape 是否正确
- 是否调用 `model.train()`
- 是否漏掉 `optimizer.zero_grad()`

### 2. shape 总报错

优先检查：

- batch 维是不是在第 0 维
- sequence 维是不是在第 1 维
- head 拆分后的 transpose 是否正确
- flatten 前后顺序是否正确

### 3. attention 跑通但结果不对

优先检查：

- softmax 维度
- mask 是否在 softmax 前加入
- 是否做了 `sqrt(d_k)` 缩放
- `QK^T` 维度是否正确

### 4. 能训练但不会生成

优先检查：

- 是否实现了自回归循环
- 是否每次只取最后一个 token 的 logits
- 采样是否正确
- 输入是否随着生成结果不断追加

## 适合你的学习节奏

你的背景是“懂概念、跑过机器学习代码，但没系统跑过 PyTorch 和深度学习工程”。更稳的节奏是：

- 阶段 0：快速通过
- 阶段 1-3：重点投入
- 阶段 4：补训练直觉
- 阶段 5：进入序列
- 阶段 6-8：核心攻坚
- 阶段 9：完整项目闭环

如果每天投入 2 小时，推荐时间安排：

- 第 3 周：阶段 3
- 第 4 周：阶段 4-5
- 第 5 周：阶段 6
- 第 6 周：阶段 7-8
- 第 7 周：阶段 9 初版
- 第 8 周：脱离教程重写一次 mini Transformer

## 最终毕业标准

至少满足下面 8 条：

1. 能独立写 PyTorch 标准训练循环
2. 能独立做文本 token 化与 batch 构造
3. 能手写单头和多头 attention
4. 能实现 causal mask
5. 能手写位置编码
6. 能手写 Transformer block
7. 能拼出 decoder-only mini Transformer
8. 能训练并生成文本

如果这 8 条全部完成，你就不只是“看过 Transformer”，而是真的“会手写 Transformer”。
