# Rebuttal - 对审稿意见 4 的回复

> **审稿人意见**
>
> 4. The experiments primarily demonstrate the usefulness of PF-86K rather than the effectiveness of PuzzleForge as a framework.
>
> Much of the experimental section evaluates the difficulty of PF-86K and the downstream improvements. These results support PF-86K as a useful dataset, but provide less evidence that PuzzleForge is a superior data-generation framework.
>
> Important framework-level baselines are missing, such as direct LLM-based instance synthesis and direct LLM generation of executable generators without the proposed multi-stage decomposition. Otherwise, the paper may be more appropriately framed primarily as a benchmark/data contribution rather than a methodological framework contribution.
>
> 中文要点：实验证明了 PF-86K 有用，但没有证明 PuzzleForge 作为框架有效；缺少两个框架级基线——直接用 LLM 合成题目实例、以及不做多阶段分解直接生成可执行生成器。

## 回复

我们补上了审稿人点名的两个框架级基线：直接造题（B1）与不做多阶段分解、直接生成可复用生成器（B2），在 97 个共享 seed 上与完整流水线（PF）做盲评比较，1,440 道题，每组 480 道。

**设置。** 三组都用 GPT-5.2。PF 是论文发布的 test split：每个生成器 2% 的随机 holdout，已经过流水线自己的去重与生成器过滤；holdout 本身不是按质量挑的。B1/B2 同模型、同解码参数、同 20 题配额。B2 有三次带真实执行报错的调试机会，但没有 expansion agent、DSL、语义验证或 solve-based filtering，因此是更强的基线。评审只看题面、规范答案与匿名证书，方法和 seed 已剥离。

**表 T1 - 每个请求槽位的产出**（每条件 480 槽位，盲评；`tokens per valid item` 为 20 实例/单位口径）

```
+-------------------------------+-------------+-------------+-------------+
|                               |     PF      |     B2      |     B1      |
+-------------------------------+-------------+-------------+-------------+
| valid items (of 480 slots)    | 366 (76.3%) | 352 (73.3%) | 134 (27.9%) |
| valid, >=3 dependent steps    | 301 (62.7%) | 162 (33.8%) |  28 (5.8%)  |
| reasoning depth, mean (0-4)   |    2.94     |    2.34     |    1.93     |
| median problem length (chars) |     692     |     321     |     297     |
| near-duplicate pairs @0.8     |    3.0%     |    24.9%    |    6.2%     |
| generators represented        |     284     |     97      |     97      |
| tokens per valid item         |   12,267    |     527     |    4,571    |
+-------------------------------+-------------+-------------+-------------+
```

*百分比按槽位计（分母 480）；near-dup 是在每条件 1,284 个 matched 题上算的，不是 480 个盲评槽位。配对差为 seed 宏平均；推断按 seed 配对（Wilcoxon，21 项 Holm，2,000 次 seed bootstrap）。*

**对 B1**，PF 在有效率（+0.484 [+0.406, +0.556]，p = 5.0e-14）与深度（+0.844）上明显更好。B1 的失败是静默的：71.7% 的题无效，却只有 1 题无输出，344 道无效题里 331 道规范答案错误。执行接地是决定性因素，B1 不是强基线。

**对 B2**，有效率持平：生成器级 0.775 vs 0.774；seed 级 +0.027 [-0.054, +0.114]，去掉 B2 五个零产出 seed 后变为 -0.010。PF 的优势在产出率：62.7% vs 33.8% 的槽位产出一道有效且 >=3 步的题（1.86 倍；单位匹配后 63.8% [56.6, 70.5] vs 33.8%）。

PF 的题面也约长一倍（中位 692 vs 321 字符），所以我们直接检验长度混杂，而不是只依赖一个模型。原始深度差 +0.602；OLS 加 log(length) 为 +0.418；严格匹配更保守：最近邻（caliper 0.5）+0.439 [+0.150, +0.764]；按 seed × 长度五分位的 CEM +0.207 [-0.020, +0.443]，最高长度分位基本持平（-0.14）。单小问子组（排除"PF 只是把小问拼在一起"）给出 +0.541 [+0.353, +0.827]（原始）与 +0.548 [+0.120, +0.900]（长度匹配）。**因此我们以 depth 作为支持性证据，主主张落在 >=3 步产出率上：** 把 B2 按 PF 的长度分布标准化后 +24.6 pp [+11.6, +35.9]；严格最近邻匹配后 +15.8 pp [-1.2, +33.7]。方向在所有设定下一致；严格匹配的重叠较少、估计更小，但方向不变。

**多样性。** 单位匹配（PF = 生成器，B2/B1 = seed）后，near-dup @0.8 是 13.2% vs 24.9%；约束标签集合相同 30.2% vs 53.1%；推理标签集合相同 46.1% vs 56.8%。PF 的 seed 级 3.0% 部分是"5 道题来自 3 个生成器"的混合效应，我们做了校正。对 B1，PF 的 near-dup 更高（13.2% vs 6.2%），但两个 tag 集指标都更好；B1 的题面也更短。

**成本。** 按论文的 200 实例/单位尺度，PF 每有效题 1,227 token，B2 是 50，B1 是 4,571；按 20 实例/单位，分别是 12,267、527、4,571。PF/B2 在两个尺度上都是 ~23-25 倍；PF 的 spec 成本是 0.34-0.55M token/seed，B2 是 7.7k（45-70 倍）。成本是 trade-off：PF 多出的预算买到的是 >=3 步产出与结构多样性。我们明确报告这一点，不声称成本优势；上一版把 PF 的 200 实例/generator 与 B2 的 20 实例/seed 放在同一行，修正后的表把两者放在同一摊销尺度。

**评审可靠性。** 在 560 道交叉子样本上（两个家族看到同样的 3 个 solver 尝试，每个模型一个 verdict），exact agreement 83.4%，Cohen's kappa 0.67。两个家族的严格度不同：PF 的 invalid 率在 `gpt-5.6-luna` 下是 30.9%，在 `gemini-3.1-pro-preview` 下是 12.6%；PF−B2 的有效率差随 judge 翻符号（luna 0.686 vs 0.730；gemini 0.863 vs 0.789）。B1 在两个家族下分别是 25.5% 与 27.5% valid，即 72-74% invalid。**因此 PF−B2 的有效率差在 judge 噪声内，B1 的差距不在。** 两家都判 valid 的题上，depth 差是 +0.729（luna）与 +0.536（gemini）。

**23.1% 由什么构成。** judge 判 PF 发布 test set 的 111/480（23.1%）为 invalid，其中 89 道是规范答案错误。两个真实例子说明这个数字需要拆开看。`PF / operation_21/08` 是一道可分离三角多项式在矩形区域上的二重积分题，发布答案是 `[[0.133046]]`，独立计算是 `[[-0.133046]]`：符号错误，真正无效的题。`PF / number_wall/14` 是一道复利题（2433 元按 3% 季度复利存 3 年，再加 3723 元按 6% 季度复利存 4 年），发布答案是 `7946.95`，计算值是 `7946.9444`，四舍五入应为 `7946.94`：0.01 的舍入差，属于瑕疵，不是坏题。两者都被算作 invalid，所以 23.1% 是混合了"实质错误"与"瑕疵"的偏高代理。跨家族 panel 显示同样的敏感性：PF 的 invalid 率在 luna 下 30.9%、gemini 下 12.6%，而 B1 在两个家族下都是 72-74%。修订版会把两类错误分开报告，并修正发布标签。

**定位。** 我们同意定位要写清楚，新增的比较让我们可以写得更精确。框架的贡献是每 seed 产出的 >=3 步题比例与结构多样性；代价是 ~25 倍生成 token，有效率与最强的一遍生成器基线持平。修订版会把这条作为框架级贡献与数据集贡献并列，补上生成器级与长度匹配的表，并同步改写 abstract 与 intro。这比笼统的"框架更优"更精确、也更站得住。

prompt、生成器、trace、盲评 key 与逐请求 token 账本随论文与修订版释放。
