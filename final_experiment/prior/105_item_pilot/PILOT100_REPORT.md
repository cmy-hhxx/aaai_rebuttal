# GPT-5.2 造题 pilot：7 seeds / 105 题盲评（v2 评测）

> 单模型自动初评（gpt-5.6-luna），k=1，非人工复核。数字只描述这一批固定样本，不作因果或显著性断言。

## 0. 与上一版报告的差异

上一版评审 prompt 有 schema 缺陷，105 题里 10 题（9.5%）三次修复仍失败、记 `execution_unknown`。修复后重跑（`auto_v2`）：**unknown 10 → 0**，所有有题面的样本都拿到了模型判定。判定结果也随之变化，以下是 v2 数字，旧 `auto/` 仅留档。

## 1. 一句话结论

- **PF 对 direct：明确更好。** 共识 valid 24/35 vs 17/35，配对差 +0.200，95% bootstrap 区间 [+0.086, +0.314] 不含 0；PF 深度 3.00 vs 2.12，题面中位 692 vs 310 字符。
- **PF 对 framework：有效率打平，其他维度 PF 更好。** 24/35 vs 25/35，差 −0.029，区间 [−0.143, +0.086]；但 PF 深度 3.00 vs 2.72，单 seed 近重复率 2.0% vs 26.4%，边际 API 成本 ≈0 vs 4.2k token/有效题。
- 因此可以写“PF 在有效题率（对 direct）、推理深度、多样性、边际成本上更优”，**不能写“PF 在所有维度优于 framework”**。

## 2. 设置

| 项目 | 值 |
|---|---|
| 生成模型 | `gpt-5.2`（网关实际返回 140/140 条 `model=gpt-5.2`） |
| 评审模型 | `gpt-5.6-luna`，k=1，单模型 |
| 提示词 | `paper_v2` 中文（direct / framework 各一份 system prompt） |
| endpoint | `https://internal-idc-equ.ainvest.com/ind/iwc-aime-model/litellm/v1` |
| seeds | 7 个：cipher_8, logic_11, operation_22, word_sorting, puzzle_15, futoshiki, campsite |
| matched 槽位 | 每组 100（PF 参考题、direct、framework 各 100） |
| 盲评样本 | 105 题（7 seed × 3 组 × 5 题） |

seed 选择规则：从 `configs/gpt52_seed_ids.txt` 的 97 个语言控制 seed 中固定取 7 个，使其 PF 参考题配额恰好合计 100；不按生成质量挑选。

## 3. 生成结果

| 组 | 请求槽位 | 有输出 | 唯一题面 | 失败槽位 |
|---|---:|---:|---:|---:|
| direct | 140 | 140 | 140 | 0 |
| framework | 140 | 120 | 119 | 20 |

- framework 的 20 个失败全部来自 `cipher_8`：3 次现场生成的程序都在自身校验处报错（如 “Invalid cipher alphabet for UV: must be a 26-letter permutation”），按协议记 `generation_failed`，未人工补题。
- framework 其余 6 个 seed 均为 20/20 产出（119 个唯一题面，1 个重复）。
- direct 全部一次通过，无修复重试；题面中位中文字符数 85，framework 为 137。

生成产物：`results/<method>/<seed>/*.json`；framework 的程序与执行记录：`programs/<seed>/attempt-*.py`、`accepted.json`、`jobs/`。

## 4. 自动初评 v2（105 题）

| 组别 | 盲评 N | 模型判定 | 执行未决 | 无输出 | 共识 valid | 深度均值 | 证书均值 | 题面中位字符 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 35 | 35 | 0 | 0 | 17/35 (0.486) | 2.118 (17) | 3.647 (17) | 310 |
| framework | 35 | 30 | 0 | 5 | 25/35 (0.714) | 2.720 (25) | 3.160 (25) | 353 |
| puzzleforge | 35 | 35 | 0 | 0 | 24/35 (0.686) | 3.000 (24) | 3.375 (24) | 692 |

- 无 uncertain、无 unknown；framework 的 5 个无输出仍是 cipher_8 生成失败。
- 深度与证书分数只在共识 valid 子集上统计，不是全样本均值。

### 按 seed 的共识结果（v2）

| seed | PF | direct | framework |
|---|---|---|---|
| campsite | 3 valid / 2 invalid | 3 valid / 2 invalid | 4 valid / 1 invalid |
| cipher_8 | 1 valid / 4 invalid | 0 valid / 5 invalid | 5 unavailable（生成失败） |
| futoshiki | 4 valid / 1 invalid | 2 valid / 3 invalid | 5 valid |
| logic_11 | 3 valid / 2 invalid | 2 valid / 3 invalid | 3 valid / 2 invalid |
| operation_22 | 5 valid | 4 valid / 1 invalid | 4 valid / 1 invalid |
| puzzle_15 | 5 valid | 5 valid | 5 valid |
| word_sorting | 3 valid / 2 invalid | 1 valid / 4 invalid | 4 valid / 1 invalid |

### 按 seed 配对比较（v2）

| PF 减去基线 | 宏平均差 | 95% bootstrap 区间 |
|---|---:|---|
| PF − direct | +0.200 | [+0.086, +0.314] |
| PF − framework | −0.029 | [−0.143, +0.086] |

- PF − direct：区间不含 0，但只有 7 个 seed 聚类，仍应写成“方向一致的描述性证据”。
- PF − framework：区间跨 0，**不能写 PF 有效性更高**；差异只有 1 题。

### 评审器修复记录（v1 → v2）

- 根因：gpt-5.6-luna 把约束标签（`ordering`、`string`）放进 `reasoning_type_tags`；另有 invalid 时 `explanation_evidence` 返回 null、`solver_correct` 返回 true 两类边界错误。
- 修复：JUDGE_SYSTEM 改成两个互斥的封闭词表，加入“invalid 时 `solver_correct` 全 null、证据字段仍须非空”的显式规则；schema 报错直接点名非法值。先在 10 道历史失败题上探针，10/10 通过，再全量重跑。
- 代价：v1 与 v2 在 105 题上仅 87 题判定一致（82.9%）；在 v1 已给出判定的 95 题里仍有 8 题翻转（8.4%）。这说明 **单 judge、k=1 本身有不可忽略的噪声**，v2 更稳但不是真值。

## 5. 案例（v2，按 anon_id 可在 `audit_blind.jsonl` / `examples.jsonl` 追溯）

- direct / valid / campsite：4×3 营地题，答案 `[['X','C','T'],...]`；评审复核帐篷与树一一正交相邻、互不接触、行列计数一致。
- direct / invalid / campsite：约束自相矛盾——第 2 行要求 1 顶帐篷，但可放位置与列约束冲突；canonical 网格里的帐篷也不挨树。
- framework / valid / operation_22：自定义偏导运算题，评审逐步展开并核对 LaTeX 答案。
- framework / invalid / campsite：canonical 答案本身可行，但证书中的两个帐篷上下相邻，违反“帐篷不能接触”。
- PF / invalid / cipher_8：评审按题面三步规则复算第 6 位，得到 O 而 canonical 为 C。

## 6. 重要限制

1. **单评审模型、k=1**：v1→v2 有 8.4% 翻转，说明结论对 judge 版本敏感；需要 k=2 或人工双审。
2. **PF 是历史筛选数据**：PF 参考题经过论文流程筛选，不是同模型、同预算重跑；结论只能限定为“固定 seed 与设置下的测试集比较”。
3. **PF 的 invalid 也不少**：11/35（31.4%），与 direct（18/35）相比好很多，但绝对水平不高；长题面可能让 judge 更难复核，需人工抽查。
4. **单次生成**：每个 seed 只生成一次，不构成稳定性实验；framework 的 cipher_8 失败也不能外推为“框架在 cipher 类上普遍失败”。
5. **7 个 seed 是配额抽样**：不是随机样本；按 seed 配对 bootstrap 只有 7 个聚类，区间很宽。
6. 全量 97 seed 前应重新冻结 run：本次前后修改了 `executor.py`（sandbox metadata 权限）与 `autojudge.py`（schema 处理与 prompt），旧 manifest 不能复用。

## 7. 产物

| 内容 | 路径 |
|---|---|
| 本报告 | `runs/gpt52_pilot100_20261028/PILOT100_REPORT.md` |
| 自动初评 v2 完整报告 | `runs/gpt52_pilot100_20261028/auto_v2/auto_report.md` |
| 逐题模型标签（v2） | `runs/gpt52_pilot100_20261028/auto_v2/model_labels.jsonl` |
| 案例（v2） | `runs/gpt52_pilot100_20261028/auto_v2/examples.jsonl` |
| 旧版初评（v1，留档） | `runs/gpt52_pilot100_20261028/auto/` |
| 盲评输入 / 私有映射 | `runs/gpt52_pilot100_20261028/audit/audit_blind.jsonl`、`audit_key.jsonl` |
| 三组记录 | `runs/gpt52_pilot100_20261028/records_selected.jsonl` |
| 冻结清单 | `runs/gpt52_pilot100_20261028/manifest.json` |

## 8. 建议的下一步

1. 用 k=2（同一 judge 两次）或人工双审复核 105 题，至少覆盖 34 道 invalid；目标把 judge 噪声压到可接受范围。
2. 做 N=100/seed 的多样性衰减实验（direct + framework），验证“生成次数上升后重复率如何变化”；当前 20 槽只能看到趋势。
3. 若扩到 97 seed，按协议新开 run，保留本 pilot 作为方法学预试，不并入主分析。
