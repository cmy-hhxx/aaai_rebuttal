# 可复现材料索引

一次实验（97 seeds / 1,440 道盲评）的全部材料分布在三处：`final_experiment/` 是冻结归档（含校验和），[experiment/](experiment/) 是实际运行的 Python 包，[sources/](sources/) 是论文与补充材料原件。下面把每一类材料的位置、数量、口径与校验方式列清楚，任何一项都能单独核对。

## 1. 运行矩阵

```
+------------------------+-------------------------------------------------+
| field                  | value                                           |
+------------------------+-------------------------------------------------+
| seeds                  | 97 (Chinese-language subset of the paper's 129) |
| matched slots per seed | 4/6/8/12/14/16 (median 16); 1,284 per condition |
| items blind-judged     | 480 per condition; 5 per seed (4 for 5 seeds)   |
| generator              | gpt-5.2, max_completion_tokens=32768            |
| judge                  | gpt-5.6-luna, k=1, max_completion_tokens=16384  |
| prompts                | paper_v2 / zh; one prompt per condition         |
| repair budget          | B1 3 repairs/batch; B2 3 attempts/seed          |
| decoding               | only max_completion_tokens is set               |
| sampling seed          | rng_seed 20261028 (slot order)                  |
+------------------------+-------------------------------------------------+
```

endpoint、超时、重试、并发等完整配置在 [final_experiment/configs/gpt52_paper_v2_20261028.json](final_experiment/configs/gpt52_paper_v2_20261028.json)；Python 与包版本在 [final_experiment/environment/environment.json](final_experiment/environment/environment.json)。

## 2. 提示词

```
+-----------------------------------+-------+-------------------+---------+
| artifact                          | chars | sha256 (first 16) | used as |
+-----------------------------------+-------+-------------------+---------+
| prompts/paper_v2/zh/direct.txt    | 1,586 |  26264280a10085d7 |   B1    |
| prompts/paper_v2/zh/framework.txt | 2,077 |  61ace6c3be2d6e2f |   B2    |
| prompts/paper_v2/en/direct.txt    | 4,300 |  0c92421f7a3c230f |    -    |
| prompts/paper_v2/en/framework.txt | 5,851 |  ca7bda22252b107e |    -    |
| autojudge.py SOLVE_SYSTEM         |   543 |  50d73d72a9e1fa48 | solver  |
| autojudge.py JUDGE_SYSTEM         | 3,055 |  871bef4e854415a2 |  judge  |
+-----------------------------------+-------+-------------------+---------+
```

- **生成 prompt**：四个文件，中英各两份，本次实际使用中文版（B1 用 `direct.txt`，B2 用 `framework.txt`）。字符数与 SHA256 记录在 [final_experiment/prompts/paper_v2/checksums.json](final_experiment/prompts/paper_v2/checksums.json)，并写入 `run/manifest.json` 的 `input_hashes`。prompt 一旦改动，`prepare` 会拒绝复用已有目录。
- **评审 prompt**：两个常量 `SOLVE_SYSTEM` / `JUDGE_SYSTEM`，内联在 [experiment/autojudge.py](experiment/autojudge.py) 第 20-62 行，原因是它们要与判定 schema 校验一起演进。成对 hash 为 `d11af858f492a8e88de6dc69be618c7912f8ffb0f930ecf84acad4d8b0fd8ab1`，与 [final_experiment/run/auto/manifest.json](final_experiment/run/auto/manifest.json) 的 `prompt_hash` 一致（[tools/make_tables_ascii.py](tools/make_tables_ascii.py) 每次运行都会重算并断言）。
- **评审 prompt 的硬约束**（可直接引用）：只接收题面、规范答案与匿名求解证书；显式要求"Do not infer origin"；错误类型与标签取自封闭词表；判定非 `valid` 时深度分与解释分必须为 `null`；要求给出可核验的理由而不是复述题面。
- **逐条请求快照**：`run/api_cache/` 保存每次调用的请求体（prompt 逐字）与响应，可直接抽查任何一条判定对应的完整输入。

## 3. Token 消耗

```
+----------------------+----------+-----------+------------+--------------------+-----------+-------+
| stage                | requests |    prompt | completion | of which reasoning |     total |   USD |
+----------------------+----------+-----------+------------+--------------------+-----------+-------+
| direct generation    |      391 | 1,519,200 |    954,940 |                  0 | 2,474,140 | 14.97 |
| framework generation |      116 |   336,295 |    413,235 |                  0 |   749,530 |  6.10 |
| judge: solve         |    1,421 |   741,205 |  2,092,446 |          1,839,144 | 2,833,651 |  2.56 |
| judge: verdict       |    1,474 | 1,915,649 |  1,598,368 |          1,209,031 | 3,514,017 |  2.23 |
+----------------------+----------+-----------+------------+--------------------+-----------+-------+
| total                |    3,402 | 4,512,349 |  5,058,989 |          3,048,175 | 9,571,338 | 25.86 |
+----------------------+----------+-----------+------------+--------------------+-----------+-------+
```

- `reasoning` 是 `completion` 的子集，`total = prompt + completion`，不重复计数。
- 美元取自网关响应的 `usage.cost` 字段，只覆盖成功响应；失败的 HTTP 尝试没有 usage，因而不计费也不计量。
- **每有效题口径**：生成 token ÷（有输出的题数 × 题级有效率）。B1 分母 1,935 × 0.2797、B2 分母 1,840 × 0.7737、PF 按每个 generator 200 个实例 × 0.7625。[final_experiment/analysis/analyze.py](final_experiment/analysis/analyze.py) 的 `tokens.per_valid` 与 fig6 用同一公式，数值与 T6 一致。
- **PF 的 spec 构造成本**是补测值：10 个 seed 重跑 encoding + debugging，10/10 成功，每次 3.1 次调用，187,068 token/generator（中位 116,064，范围 56k-434k），$0.098。原始 usage 在 [final_experiment/pf_cost/](final_experiment/pf_cost/)，口径说明见其中的 `AUDIT.md`。这 31 次调用不计入上表。该补测只含 encoding 与 debugging，不含 expansion 与 evaluation，因此是下界。
- **生成侧的 HTTP 实况**：B1 393 次尝试 / 391 次成功 / 2 次失败（Azure 内容策略 400，同一 payload 重放即过）；B2 116/116/0；累计 HTTP 时间 9,560 s 与 4,100 s。见 `run/generation_costs.json`。
- **每请求明细**：[final_experiment/run/tokens_requests.csv](final_experiment/run/tokens_requests.csv)（3,402 行，字段含 stage、method、model、prompt/completion/reasoning token 与 cost）；汇总脚本是 [final_experiment/analysis/token_ledger.py](final_experiment/analysis/token_ledger.py)。

## 4. 数据与输入

- 论文与补充材料原件：[sources/](sources/)，来源与 SHA256 见 [sources/PROVENANCE.md](sources/PROVENANCE.md)（OpenReview 投稿 44511）。
- 全部 129 个 seed、1,720 道 PF 参考题。
- 本次实际使用的输入被完整快照：`run/seeds.json`（97 个 seed）、`run/reference.json`、`run/snapshot/`（代码、prompt 与数据在 prepare 时刻的副本）。
- seed 清单：[final_experiment/configs/gpt52_seed_ids.txt](final_experiment/configs/gpt52_seed_ids.txt)；每 seed 的槽位配额由 `run/manifest.json` 的 `matched_slots` 固定（取值为 4/6/8/12/14/16，中位 16，合计 1,284）。

## 5. 产物清单

```
+----------------------------------+-----------------------+-----------------------------------+
| artifact                         |                 count | what it pins down                 |
+----------------------------------+-----------------------+-----------------------------------+
| checksums.sha256                 |          11,564 files | every archived byte               |
| run/manifest.json                |                     - | config, prompt and input hashes   |
| run/seeds.json + reference.json  |            97 / 1,720 | exact inputs used                 |
| run/records_selected.jsonl       |            5,164 rows | all three conditions              |
| run/programs/                    | 97 dirs, 116 attempts | every generator written           |
| run/traces/                      |                   507 | every generation request/response |
| run/audit/                       |              1,440 x2 | blind items + sealed key          |
| run/auto/model_labels.jsonl      |                 1,440 | per-item verdicts and tags        |
| run/tokens_requests.csv          |            3,402 rows | per-request token ledger          |
| run/tokens_summary.json          |                     - | T6/T7 stage totals                |
| run/analysis/rebuttal_tests.json |                     - | paired statistics behind T1-T5    |
+----------------------------------+-----------------------+-----------------------------------+
```

## 6. 重跑

```
+-----------------------------+------------------+-----------+
| item                        |         expected |  observed |
+-----------------------------+------------------+-----------+
| seeds                       |               97 |        97 |
| matched slots per condition |            1,284 |     1,284 |
| raw slots per condition     |            1,940 |     1,940 |
| records_selected.jsonl rows |            5,164 |     5,164 |
| blind-judged items          |            1,440 |     1,440 |
| generation requests         |   ~485 + repairs |       507 |
| judge requests              | ~2,880 + repairs |     2,895 |
| total tokens                |                - | 9,571,338 |
| total cost                  |                - |    $25.86 |
+-----------------------------+------------------+-----------+
```

```bash
cd /Users/cmy/Desktop/aaai_rebuttal
export R=runs/gpt52_final_20261028
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r final_experiment/code/runtime-requirements.lock

.venv/bin/python -m experiment.run prepare    --config configs/gpt52_paper_v2_20261028.json --out $R
.venv/bin/python -m experiment.run generate   --config configs/gpt52_paper_v2_20261028.json --out $R --method direct    --seed-file configs/gpt52_seed_ids.txt
.venv/bin/python -m experiment.run generate   --config configs/gpt52_paper_v2_20261028.json --out $R --method framework --seed-file configs/gpt52_seed_ids.txt
.venv/bin/python -m experiment.run export     --out $R --seed-file configs/gpt52_seed_ids.txt --filename records_selected.jsonl
.venv/bin/python -m experiment.evaluation     --data $R/records_selected.jsonl --out $R/audit --per-seed 5 --min-audit 1000
.venv/bin/python -m experiment.autojudge      --audit $R/audit/audit_blind.jsonl --key $R/audit/audit_key.jsonl --out $R/auto \
  --endpoint https://internal-idc-equ.ainvest.com/ind/iwc-aime-model/litellm/v1 --api-key-env JUDGE_API_KEY \
  --models gpt-5.6-luna --k 1 --workers 8 --timeout 600 --max-calls 4000 --parameters $R/judge_parameters.json
.venv/bin/python final_experiment/analysis/token_ledger.py --run $R --judge-dir $R/auto
MPLCONFIGDIR=tmp/mplconfig tmp/figvenv/bin/python final_experiment/analysis/analyze.py --run $R --figs $R/figures
```

完整版（含依赖、凭据、噪声说明）见 [final_experiment/REPRODUCE.md](final_experiment/REPRODUCE.md)。`framework` 组需要非沙箱 shell 执行 `sandbox-exec`，否则生成器无法运行。

## 7. 校验

```bash
(cd final_experiment && shasum -a 256 -c checksums.sha256)   # 11,564 个文件全量校验，须在 final_experiment 内执行
python3 tools/make_tables_ascii.py --check                   # 重算全部表格并断言评审 prompt hash
```

`run/manifest.json` 记录 config、prompt、代码与输入在 prepare 时刻的 SHA256；任一文件变化，`prepare` 会拒绝复用目录。

## 8. 已知边界

- 网关只暴露别名 `gpt-5.2`，不是带日期的快照；本实验记录实际返回的 `model` 字段。
- PF 组是论文历史筛选后的测试集，不是同模型、同预算重跑；因此只能做"固定 seed 与设置下的测试集比较"，不能做端到端成本比较。
- 评审为单一模型、k=1、**非人工**。pilot 上更换评审 prompt 有 8.4% 的题目级判定翻转（105 题中 8 题），因此正文结论全部按 seed 配对报告，不依赖题目级显著性。
- 盲评中有 26 题 `unavailable`（B2 25 题、B1 1 题），计划中按 0 计；条件有效率（0.774）与全样本有效率（0.734）两个口径都报告。
- 运行噪声：Azure 内容策略 400 出现 2 次，同一 payload 重放即通过；一条题面含 U+2029，读取器后来改为只按 `\n` 切分。
- `executor.py` 对 macOS sandbox 的 metadata 权限做过修复（否则 `execvp` EPERM）；沙箱内仍禁止读工作区文件与联网。

## 9. 未完成与缺口

- **人工双审没有做。** [final_experiment/run/audit/audit_labels.csv](final_experiment/run/audit/audit_labels.csv) 是 1,440 × 2 的空模板，[final_experiment/run/audit/report.md](final_experiment/run/audit/report.md) 明确写着"尚无可用于主终点的独立审核标签"。本回复中所有的有效、深度、标签判定都来自 `gpt-5.6-luna` 的自动评审。这是目前最容易被审稿人追问的一点：若要补，按 `audit_blind.jsonl` 双人填写后重跑 evaluation 报告即可，不需要重新生成或重新采样。
- PF-86K 的历史真实消耗不可复原；本索引里 PF 的成本全部来自 10-seed 重测估计（下界）。
- k=2 一致性未做；评审噪声只有 pilot 上的一次 v1/v2 对比。

## 10. 随论文/补充材料打包的清单

- **必交（< 3 MB）**：`prompts/paper_v2/`（44K）、`configs/`、`seeds.json`、`tokens_requests.csv`（524K）、`run/figures/`（1.6M）、`rebuttal_tables.md` 里 T1-T7 的 JSON 中间量（`run/analysis/rebuttal_tests.json`、`run/stats.json`）。
- **建议交（~30 MB）**：`run/audit/`（1,440 道盲评题面 + 封存 key）、`run/auto/model_labels.jsonl`（逐题判定与标签）、`run/programs/`（97 个 seed 的全部生成器尝试，14M）、`pf_cost/`（2.4M）。
- **不必交（~75 MB）**：`run/api_cache/`（19M）与 `run/auto/api_cache/`（56M）只是逐请求原始响应，与 traces 和 model_labels 重复，留作本地审计。
- 无论交哪一档，都附 `checksums.sha256` 与 `run/manifest.json`，对方可逐文件校验后重跑。
