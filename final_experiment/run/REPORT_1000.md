# 1000+ 题全量报告：GPT-5.2 造题 vs PuzzleForge

> 97 个语言控制 seed，每组 1284 matched，盲评 **1440 题**（480/组）。生成 `gpt-5.2`，评审 `gpt-5.6-luna`（k=1，单模型自动初评）。全部 3,402 个付费请求逐条记账。

## 0. 结论

1. **PF 大幅优于 direct**：有效题率 0.76 vs 0.28，配对差 **+0.48 [+0.41, +0.56]**；PF 深度 2.94 vs 1.93，题面中位 692 vs 297 字符。
2. **PF 与 framework 在有效率上打平**：0.76 vs 0.73，差 +0.03（[−0.05, +0.11]）；若扣除 framework 无输出的 25 题，framework 条件有效率为 0.774，略高于 PF 的 0.763。**不能写 PF 有效率更高。**
3. **PF 的优势在深度、信息量、多样性与稳定性**：深度 2.94 vs 2.34；题面 692 vs 321 字符；同 seed 近重复率 3.0% vs 24.9%（0.8 阈值）；framework 有 21/92 个 seed 的题对近重复率 ≥50%，其中 11 个 100% 重复，另有 5 个 seed 完全生成失败。**成本不是 PF 的优势**：补测的 spec 构造成本为 187k token/generator，按 200 实例摊销仍为 1,227 token/有效题，高于 framework 的 527（见 5.1）。
4. **direct 的“静默坏数据”最严重**：344/480 判 invalid，只有 1 题无输出；0.8 阈值重复率 6.2%，且有 2 个 seed 100% 重复。

## 1. 设置

| 项目 | 值 |
|---|---|
| 生成模型 | `gpt-5.2` |
| 评审模型 | `gpt-5.6-luna`，k=1 |
| 提示词 | `paper_v2` 中文 |
| seeds | 97（`configs/gpt52_seed_ids.txt`） |
| 原始槽位 | 每组 1940（97 × 20） |
| matched | 每组 1284 |
| 盲评 | 1440（97 × 3 × 5；5 个配额 4 的 seed 取 4） |

## 2. 有效性

![有效性](figures/fig1_validity.png)

| 组别 | valid | invalid | uncertain | unavailable | 有效率（seed 宏平均） | 条件有效率 |
|---|---:|---:|---:|---:|---:|---:|
| PF | 366 | 111 | 3 | 0 | **0.76** [0.71, 0.80] | 0.763 |
| direct | 134 | 344 | 1 | 1 | 0.28 [0.21, 0.35] | 0.280 |
| framework | 352 | 103 | 0 | 25 | 0.73 [0.66, 0.81] | **0.774** |

配对差（按 seed 配对 bootstrap，2000 次）：

| 比较 | 差值 | 95% CI |
|---|---:|---|
| PF − direct | **+0.48** | [+0.41, +0.56] |
| PF − framework | +0.03 | [−0.05, +0.11] |

![按 seed 配对](figures/fig2_per_seed.png)

左图每个点是一个 seed：PF 几乎全部在对角线上方；右图 PF 与 framework 互有胜负，差距集中在少数 seed。

## 3. 深度与题面

![深度与长度](figures/fig7_depth_length.png)

| 组别 | 深度均值 | 证书分 | 题面中位字符 |
|---|---:|---:|---:|
| PF | **2.94** | 3.12 | **692** |
| direct | 1.93 | 3.72 | 297 |
| framework | 2.34 | 3.32 | 321 |

PF 的深度接近 3（至少三步相互依赖），direct 不到 2；证书分仍是 direct 略高，这一点不利于 PF。

## 4. 多样性与重复

![重复率随阈值](figures/fig3_diversity.png)

| 阈值 | PF | direct | framework |
|---|---:|---:|---:|
| 0.5 | 18.4% | 35.8% | 70.4% |
| 0.7 | 7.4% | 16.8% | 46.4% |
| 0.8 | **3.0%** | 6.2% | **24.9%** |

![按 seed 的坍缩比例](figures/fig3b_seed_ecdf.png)

- framework：92 个有产出的 seed 中，**21 个的近重复率 ≥50%，11 个 100% 重复**；曲线在 0.5 处约 0.77，说明 23% 的 seed 已经“坍缩”。
- direct：3/97 个 seed ≥50%，2 个 100% 重复；整体重复率 6.2%，是 PF 的两倍。
- PF：仅 1/97 个 seed ≥50%，且是只有 4 道题的 `logic_3`（6/6 对重复，样本很小）。

![新颖度衰减](figures/fig4_novelty.png)

direct 的“与更早题目的最大相似度”从 0.40 升到 0.65；framework 从 0.59 升到 0.72；PF 参考均值 0.55。direct 在第 6 题后越过 PF 的参考线，说明它随题量增加会向 PF 的重复水平靠拢；framework 从一开始就更高。

## 5. Token 成本

![成本 Pareto](figures/fig5_cost_pareto.png)

| 阶段 | 请求 | prompt | completion | reasoning | 总 token | 费用 |
|---|---:|---:|---:|---:|---:|---:|
| direct 生成 | 391 | 1,519,200 | 954,940 | 0 | 2,474,140 | $14.97 |
| framework 生成 | 116 | 336,295 | 413,235 | 0 | 749,530 | $6.10 |
| 评审解题 | 1,421 | 741,205 | 2,092,446 | 1,839,144 | 2,833,651 | $2.56 |
| 评审判定 | 1,474 | 1,915,649 | 1,598,368 | 1,209,031 | 3,514,017 | $2.23 |
| **合计** | **3,402** | **4,512,349** | **5,058,989** | **3,048,175** | **9,571,338** | **$25.86** |

| 指标 | direct | framework | PF@200 | PF@20 |
|---|---:|---:|---:|---:|
| token / 生成题 | 1,279 | **407** | 935 | 9,353 |
| token / 有效题 | 4,571 | **527** | 1,227 | 12,267 |

- 评审占全部 token 的 **66.3%**（6.35M/9.57M）：造题不是主要成本，筛选/评审才是。
- framework 的成本与题量脱钩：一个 seed 一份生成器；direct 线性增长。
- PF 的实例生成是本地 z3/translator，边际 API 为 0；但 spec 构造的一次性成本不便宜，见 5.1。

### 5.1 PF 的 spec 构造成本（补测）

PuzzleClone 仓库没有历史 usage 日志；用同一模型重跑 10 个 seed 的编码+调试（不含 expansion/evaluation）：

| 指标 | 值 |
|---|---:|
| 成功 | 10/10 |
| 调用 / seed | 3.1 |
| token / spec | 187,068（中位 116,064；范围 56k–434k） |
| 费用 / spec | $0.098 |

![PF 成本](figures/fig6b_pf_cost.png)

- 按 PF 设计规模 200 实例/generator：935 token/题、**1,227 token/有效题**。
- 按本次 20 实例/seed：9,353 token/题、**12,267 token/有效题**。

所以每道有效题的 token 排序是 framework 527 < PF@200 1,227 < direct 4,571 < PF@20 12,267。PF 只有在“每个生成器摊到几百个实例”时才比 direct 便宜，且始终贵于 framework。历史 PF-86K 的实际消耗不可复原，以上是 10-seed 重测的估计（下界，未含 expansion/eval）。这 31 次补测调用不计入上表的 3,402 次。

## 6. 失败与覆盖

- direct：1935/1940 有输出；`time_sequence` 的 slots 15–19 三次修复后仍失败（5 个槽位）。
- framework：1840/1940 有输出；**5 个 seed 完全失败**（`arrow_maze`、`puzzle_14`、`cipher_16`、`puzzle_19`、`math_path`），各 20 槽位；13 个 seed 的 260 个槽位至少重试过一次，其中 6 个 seed 用到第三次尝试（5 个仍失败，1 个恢复）。
- 盲评中 framework 有 25 题 `unavailable`（5 个失败 seed × 5 题），direct 1 题；PF 全部有题面。
- 这 25 题在“全样本”口径下按 0 计，因此 framework 的条件有效率（0.774）高于全样本口径（0.734）。两种口径都报告，不藏覆盖缺口。

## 7. 限制

1. 单评审模型、k=1；pilot 上换 judge prompt 有 8.4% 判定翻转，结论对评审版本敏感。
2. PF 是历史筛选数据；只能限定为“固定 seed 与设置下的测试集比较”。
3. 近重复是字符 4-gram 词面指标，不等于结构重复；framework 的模板重复可能被低估。
4. 97 个 seed 聚类，PF−framework 的 +0.03 不能写成胜出；条件口径下甚至略负。
5. 费用来自网关 usage 的 `cost` 字段，仅覆盖成功响应；失败 HTTP 尝试无 usage。
6. PF 的 spec 成本来自 10-seed 重测（encoding+debug only），不是历史真实值；美元受 prompt caching 影响，主口径用 token。

## 8. 复现

全部材料在 `final_experiment/`：配置、提示词、代码快照、生成程序、traces、盲评、逐题标签、逐请求 token、统计、图。按 `final_experiment/REPRODUCE.md` 可重跑；`final_experiment/checksums.sha256` 校验完整性。

运行噪声：Azure 内容策略偶发 400 两次（同一 payload 重放即过）；一条题面含 U+2029，读取器已改为只按 `\n` 切分。

## 9. 产物

| 内容 | 路径 |
|---|---|
| 本报告 | `runs/gpt52_final_20261028/REPORT_1000.md` |
| 自动初评 | `runs/gpt52_final_20261028/auto/auto_report.md` |
| 逐请求 token | `runs/gpt52_final_20261028/tokens_requests.csv` |
| token 汇总 | `runs/gpt52_final_20261028/tokens_summary.json` |
| 统计 | `runs/gpt52_final_20261028/stats.json` |
| 图 | `runs/gpt52_final_20261028/figures/` |
| 归档 | `final_experiment/` |
