审稿意见原文

> 4. The experiments primarily demonstrate the usefulness of PF-86K rather than the effectiveness of PuzzleForge as a framework.
>
> Much of the experimental section evaluates the difficulty of PF-86K and the downstream improvements. These results support PF-86K as a useful dataset, but provide less evidence that PuzzleForge is a superior data-generation framework.
>
> Important framework-level baselines are missing, such as direct LLM-based instance synthesis and direct LLM generation of executable generators without the proposed multi-stage decomposition. Otherwise, the paper may be more appropriately framed primarily as a benchmark/data contribution rather than a methodological framework contribution.

## 中文翻译

> 4. 实验主要证明了 PF-86K 的实用性，而非 PuzzleForge 作为框架的有效性。
>
> 实验部分的大量内容都在评估 PF-86K 的难度及其带来的下游性能提升。这些结果支持 PF-86K 是一个有用的数据集，但不足以证明 PuzzleForge 是一个更优的数据生成框架。
>
> 论文缺少重要的框架层面对比基线，例如直接使用 LLM 合成题目实例，以及不采用所提出的多阶段分解、直接使用 LLM 生成可执行的生成器。否则，这篇论文可能更适合主要定位为基准／数据贡献，而非方法框架贡献。

注：审稿原文使用的是 LLM，并未指定 GPT、GPT API 或具体模型；上述两种基线分别对应“直接生成题目实例”和“直接生成可执行生成器”。