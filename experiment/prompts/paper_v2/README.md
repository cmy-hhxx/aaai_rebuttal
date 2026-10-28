# 依据论文方法修订的中英文提示词 v2

这四份是**依据论文方法重新编写的 baseline 提示词**，不是论文原作者的 agent prompt 原文。投稿附件没有原始五 agent prompts。本版本已接入运行器；当前 GPT-5.2 对比使用 [configs/gpt52_paper_v2_20261028.json](../../../configs/gpt52_paper_v2_20261028.json)。提示词本身不绑定具体生成模型。注意：这四份 `.txt` 是 system prompt，不是生成器；C 组的 Python 生成器由模型在运行时现场返回。

**发送边界：**四份 `.txt` 正文只使用通用任务、质量及接口要求，保留 L1–L4 标签及含义，但不包含论文／框架／数据集名称、专用 DSL 名称或 agent 名称。方法来源与论文对应关系只保留在这份内部说明中；本 README 不得拼接到发送给模型的 system 或 user 消息中。

## 两份中文完整版

- [直接造题](zh/direct.txt)：完整 system prompt，可单独复制，不必再拼接旧 quality.txt。
- [编写数据合成生成器](zh/framework.txt)：完整 system prompt，要求模型写可复用 Python 程序，再由程序本地造题。

对应英文版为 [直接造题](en/direct.txt)、[编写生成器](en/framework.txt)。两种语言表达同样的要求，不能把“中文提示词”和“中文题目”混为同一个实验因素：本版本通过 output_language 指定题面和解释语言，缺省为中文；以后比较三组时仍须确保参考数据也使用相同语言。

## 与论文的对应

依据 `sources/puzzleforge_paper.txt` 的 Framework／Hierarchical Perturbation for Diversity／Multi-Agent Generator Synthesis：

| 论文方法 | 新提示词如何体现 |
|---|---|
| L1 Scenario-level | 改场景和问法，改变查询后重新计算答案 |
| L2 Type-level | 新变量／约束类型及其完整定义 |
| L3 Multiplicity-level | 同一约束模板在不同对象绑定上的多次实例化，调节数量和规模 |
| L4 Value-level | 合法具体值、参数及查询位置的变化 |
| Expansion Agent | 两组都获得L1–L2的质量目标；不要求单独调用该agent |
| Encoding Agent | C 组提取变量、定义域、约束和查询，并实现L3–L4参数化 |
| Debugging Agent | C 组进行自测并利用真实语法／运行报错修复；B 组自检题目和输出格式 |
| Evaluation Agent | 完整性、可解性、语义忠实、真实推理需求、题面无答案泄漏 |
| Solving Agent | 依据题面重新求解／交叉核验的质量目标；不伪称实际调用了独立模型 |

论文采用 PuzzleClone DSL；C 组保留自由 Python＋标准库／SymPy／Z3 的 baseline 接口，不称为论文实现复现。L1–L4 是变化层级，不是每道题必须依次完成的四个阶段。

L4 参数化本身也能构成合法可复用生成器，是论文中大量实例的重要来源；提示词鼓励适用的 L1–L3，但不会仅因程序只做取值参数化就把它判为“不可复用”。结构多样性是否提高，应由后续指标评估。

论文中 K=3 是扩展变体数，N=20 是解题验证抽样量；它们与实验的20道生成配额含义不同。当前程序不支持运行时API调用，因此本提示词不会谎称执行了论文的独立解题模型验证或零通过过滤。同一模型写的自检也可能共享错误，仍需独立评测。

## 动态 user 输入

两组第一条输入相同，seed_answer 保留原 JSON 类型：

```json
{"seed_question":"<种子题全文>","seed_answer":"<种子参考答案>"}
```

直接造题的下一条输入：

```json
{"count":5,"already_generated_problems":[],"output_language":"zh"}
```

编写生成器的下一条输入：

```json
{"available_libraries":["sympy","z3"],"target_count":20,"output_language":"zh"}
```

源码修复仍使用真实报错，不把独立评测标签反馈给生成器。涉及“多解、蕴含方向、校验路径、中间计算”的具体提醒是质量要求；不将本次已发现的错误题、金标或核验结果放进提示词。下一轮若评估修订后的方法，应使用未用于调提示词的验证种子，不能把旧试跑同时当开发集和最终验证集。

## 与 legacy 提示词的关系

旧版 `experiment/prompts/quality.txt`、`direct.txt`、`framework.txt` 保持原样。**省略 `prompt_variant` 仍加载 legacy；`prompt_variant=paper_v2` 只加载新版完整单文件。**通过 `prompt_language=zh/en` 选择指令语言，`output_language=zh/en` 单独控制产物语言；两者默认 zh。GPT-5.2 配置为 `configs/gpt52_paper_v2_20261028.json`。运行器把实际提示词复制到 snapshot 并冻结 hash，生成时要求副本存在且 hash 一致。采用 v2 须使用新 run 目录，不能把旧结果标成 v2 结果。
