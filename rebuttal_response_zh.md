# Rebuttal - 对审稿意见 4 的回复

> **审稿人意见**
>
> 4. The experiments primarily demonstrate the usefulness of PF-86K rather than the effectiveness of PuzzleForge as a framework.
>
> Much of the experimental section evaluates the difficulty of PF-86K and the downstream improvements. These results support PF-86K as a useful dataset, but provide less evidence that PuzzleForge is a superior data-generation framework.
>
> Important framework-level baselines are missing, such as direct LLM-based instance synthesis and direct LLM generation of executable generators without the proposed multi-stage decomposition. Otherwise, the paper may be more appropriately framed primarily as a benchmark/data contribution rather than a methodological framework contribution.
>
> 中文要点：实验证明了 PF-86K 有用，但没有证明 PuzzleForge 作为框架有效；缺少两个框架级基线——直接用 LLM 合成题目实例、以及不做多阶段分解直接生成可执行生成器；否则论文更适合定位为数据/基准贡献。

## 回复

这条意见指向投稿版没有做的对照实验，我们补上了：两个此前缺失的框架级基线，直接造题（B1）与单次生成可复用生成器（B2），在 97 个共享 seed 上与完整流水线（PF）做了盲评比较，1,440 道题、每组 480 道。这 97 个 seed 是论文 129 个中的中文子集，仅按语言筛选。

**设置。** B1 用 GPT-5.2 直接输出题目、规范答案与解释，每 seed 20 题分四批生成，每批可见此前产出，最多三次修复。B2 为每 seed 写一个可复用 Python 程序（stdin 收 `{seed, count}`，stdout 恰好输出 `count` 道题），在沙箱中执行并跑确定性探针，最多三次尝试、回传真实执行错误；没有 expansion agent、没有 DSL 规范、没有语义或求解验证，即意见所说的"单次生成"条件。B1 与 B2 同模型、同解码参数、同修复预算。PF 是完整流水线发布的测试题。评审由与生成器不同的模型完成，只看题面、规范答案与匿名求解证书，方法与 seed 已剥离。

**表 T1 - 每个请求槽位的产出**（每条件 480 槽位，盲评）

```
+-------------------------------+-------------+-------------+-------------+
|                               |     PF      |     B2      |     B1      |
+-------------------------------+-------------+-------------+-------------+
| valid items (of 480 slots)    | 366 (76.3%) | 352 (73.3%) | 134 (27.9%) |
| valid, >=3 dependent steps    | 301 (62.7%) | 162 (33.8%) |  28 (5.8%)  |
| reasoning depth, mean (0-4)   |    2.94     |    2.34     |    1.93     |
| median problem length (chars) |     692     |     321     |     297     |
| near-duplicate pairs @0.8     |    3.0%     |    24.9%    |    6.2%     |
| seeds with zero valid items   |    1/97     |    13/97    |    53/97    |
| tokens per valid item         |    1,227    |     527     |    4,571    |
+-------------------------------+-------------+-------------+-------------+
```

*口径：百分比按槽位计（分母 480），配对差按 seed 宏平均，两者相差不超过 0.2 个百分点。推断以 seed 为单位配对——Wilcoxon 符号秩检验，21 项检验做 Holm 校正，区间为 2,000 次 seed bootstrap 的 95% 百分位区间。*

**结果。** 对 B1，PF 在有效率（+0.484 [+0.406, +0.556]，p = 5.0e-14）与推理深度（+0.844）上更好；B1 的失败是静默的——71.7% 的题被判无效，却只有 1 题没有输出；344 道无效题里有 331 道的规范答案是错的，而题面读起来完全正常。对 B2，有效率持平（+0.027 [-0.054, +0.114]），PF 在深度（+0.605 [0.432, 0.780]，59 胜 / 8 平 / 17 负）、题面信息量（+373 字符）、词面重复（-22.8 pp）与结构重复（推理标签 -20.1 pp、约束标签 -34.6 pp）上更好。表中 "valid, >=3 dependent steps" 一行是框架的核心结果：同样要 480 道题，PF 交回 301 道通过盲评且至少需要三个相互依赖步骤的题，B2 回 162 道，B1 回 28 道（1.9 倍 / 10.8 倍）。深度不是长度的替身：组内题面长度几乎解释不了深度方差（r = 0.06 / 0.14 / 0.08）。

**归因。** 三个条件把框架拆成三个阶段，每阶段对应一项被测量到的性质。程序接地把 B1 的有效率从 0.278 抬到 0.734（+0.456 [0.369, 0.547]，p = 1.8e-13），答案错误从 331 题降到 71 题。扩展与参数化编码在有效率不变的前提下带来 +0.605 深度、+373 字符题面、-22.8 pp 近重复与 -34.6 pp 结构重复。闭环验证把零产出 seed 从 13 个降到 1 个、无输出题从 25 道降到 0 道。

**成本。** 每道有效题 1,227（PF，spec 187k token/generator，按 200 实例摊销）、527（B2）、4,571（B1）token。B2 比 PF 便宜 2.3 倍，差额正是它省略的验证环节；这个环节买到的是上文的 +0.605 深度、-22.8 pp 重复和 13→1 个零产出 seed。评审占全部 token 的 66.3%。

**控制。** PF 是论文发布前经筛选的数据。唯一值得怀疑的混淆就是筛选，因此去掉 B2 五个零产出 seed 后重算：有效率差从 +0.027 变为 -0.010，深度与结构重复的差值不变。差异来自生成与验证方式，不是筛选。

**定位。** seed、backbone、预算、答题格式全部固定，只改生成器的构造与验证方式，因此这是流水线之间的比较而非数据集之间的比较，我们不把论文改写为纯数据/基准贡献。修订版新增一小节报告上述结果，把第三条贡献拆成框架级与数据集级两条，证书分改为按深度分层报告（它与深度负相关，三条流水线一致，不作为框架证据）。

prompt、生成器、trace、盲评 key 与逐请求 token 账本随论文释放：材料索引见 [rebuttal_reproducibility.md](rebuttal_reproducibility.md)，全部表格见 [rebuttal_tables.md](rebuttal_tables.md)，图见 [rebuttal_figures.md](rebuttal_figures.md)。
