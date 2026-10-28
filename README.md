# PuzzleForge rebuttal：GPT-5.2 数据质量对比

在**同一批种子题**上，让 GPT-5.2 用两种方式造题，再与现有 PuzzleForge（PF）参考题做盲评，检验 PF 的题目质量是否更好：

- A：PF 已有测试题，历史数据，作为参考组。
- B：API 直接造题（direct）。
- C：GPT-5.2 现场编写可复用 Python 生成器，再由本地执行器运行造题（framework）。

结论尚未产生。仓库只提交代码、提示词和非敏感配置；`sources/`、`output/`、`runs/` 中的数据与报告留在本地。

> C 组没有预写的 per-seed 生成器。我们只预写 system prompt 和本地执行/校验器；每个 seed 的 Python 程序由 GPT-5.2 在 `generate` 时现场返回，原样保存到 `programs/<seed>/attempt-*.py` 后再执行。

规模：97 个语言控制 seed，每个 baseline 20 槽/seed，共 **1940** 个原始槽位；三组 matched 总量从 `records_selected.jsonl` 统计（约 1300/组）。盲评每 seed 每组最多 5 题，**目标 ≥1000 题**。

## 指导思想

1. **目标是可核查的比较，不是预设 PF 胜出。** 允许结论为支持、部分支持、无差异、baseline 更好或证据不足。
2. **只差一个变量。** 三组同种子、同语言、同答题格式；B 与 C 只差“直接出题”还是“写生成器”。
3. **不把历史数据当因果实验。** A 已经过论文的生成器验证、过滤和测试集选择；结论只描述“固定种子与设置下的测试集比较”，不写成框架的普遍因果优势。
4. **生成与评价分离。** 生成提示词不看评测反馈；盲评去掉方法、seed 和原生解释；自动初评只是代理，人工双审才是主终点。
5. **失败保留，抽样固定。** 不删失败槽位、不按质量补选；报告分母、覆盖和区间，不合成一个总分。
6. **baseline 不能故意弱化。** B/C 用同一 GPT-5.2、同一预算和同等提示词投入；不靠弱 baseline 或窄提示词制造优势。
7. **一切冻结。** config、prompt、代码、输入都有 hash；改动就新建 run，不覆盖旧结果。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 中英文提示词 | 已就绪 | `experiment/prompts/paper_v2/`，四份完整 system prompt，已冻结 hash |
| direct 调用 / framework 执行链 | 已就绪 | `experiment/run.py`、`experiment/executor.py` |
| GPT-5.2 配置 | 已就绪，endpoint 待填 | `configs/gpt52_paper_v2_20261028.json` |
| 子集导出、1000+ 题盲评、自动初评 | 已就绪 | `experiment/run.py`、`evaluation.py`、`autojudge.py` |
| GPT-5.2 实际生成 | **尚未运行** | 本检出没有 endpoint、API key、`sources/` 数据 |
| 对比报告 | **尚未产生** | 不能填预设结论 |

## 最小流程

```text
prepare → generate（97 seeds，direct + framework）→ export 子集
        → evaluation（1000+ 题盲评）→ autojudge → auto_report.md
```

### 1. 环境与数据

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r runtime-requirements.lock
```

`sources/puzzleforge_supplement/data/` 需要：

```text
seed_puzzles.jsonl      129 个种子
test_normal.jsonl       862 道 PF 参考题
test_hard.jsonl         858 道 PF 参考题
```

这些数据不随仓库分发；生成器执行还需要 macOS `sandbox-exec`。

### 2. 配置 endpoint 与 key

编辑 `configs/gpt52_paper_v2_20261028.json`：

```json
"endpoint": "https://YOUR_ENDPOINT/v1"
```

- 兼容 OpenAI Chat Completions，可填 base URL 或完整 `/chat/completions` URL。
- 默认模型 `gpt-5.2-2025-12-11`；端点只支持别名时改成实际 id，并记录差异。
- key 只放环境变量或根目录 `.env`，不要写进 JSON。
- **先填 endpoint，再 `prepare`。** 之后改 endpoint 会被冻结检查拒绝。

```bash
read -rs "OPENAI_API_KEY?请输入 API key: "
export OPENAI_API_KEY
```

### 3. 预检（不调用 API）

```bash
.venv/bin/python -m experiment.run prepare \
  --config configs/gpt52_paper_v2_20261028.json \
  --out runs/gpt52_paper_v2_20261028
```

检查：

```bash
jq '{model: .config.model, prompt: .config.prompt_variant,
     language: .config.output_language,
     matched_total: ([.matched_slots[] | length] | add)}' \
  runs/gpt52_paper_v2_20261028/manifest.json
```

预期 `model=gpt-5.2-2025-12-11`、`matched_total=1720`（全 129 seed 的配额；本轮 97 seed 的实际 matched 从导出结果统计）。

### 4. 造题

```bash
.venv/bin/python -m experiment.run generate \
  --config configs/gpt52_paper_v2_20261028.json \
  --out runs/gpt52_paper_v2_20261028 \
  --method both \
  --seed-file configs/gpt52_seed_ids.txt
```

同一条命令可续跑；已完成的批次和缓存会跳过。不要为了重跑换新目录。97 个 seed 的完整清单在 `configs/gpt52_seed_ids.txt`。

### 5. 导出子集并准备 1000+ 题盲评

```bash
.venv/bin/python -m experiment.run export \
  --out runs/gpt52_paper_v2_20261028 \
  --seed-file configs/gpt52_seed_ids.txt \
  --filename records_selected.jsonl

.venv/bin/python -m experiment.evaluation \
  --data runs/gpt52_paper_v2_20261028/records_selected.jsonl \
  --out runs/gpt52_paper_v2_20261028/audit \
  --per-seed 5 --min-audit 1000
```

`records_selected.jsonl` 含 97 个 seed 的 PF matched（约 1300 行）加两个 baseline 各 1940 行；主比较只用 matched。盲评按每 seed 每组最多 5 题抽样，**低于 1000 会直接报错**；若实际不足，把 `--per-seed` 提到 6 重跑，不能按质量补选。

### 6. 自动初评

```bash
export JUDGE_API_KEY=...
.venv/bin/python -m experiment.autojudge \
  --audit runs/gpt52_paper_v2_20261028/audit/audit_blind.jsonl \
  --key runs/gpt52_paper_v2_20261028/audit/audit_key.jsonl \
  --out runs/gpt52_paper_v2_20261028/auto \
  --endpoint 'https://YOUR_JUDGE_ENDPOINT/v1' \
  --api-key-env JUDGE_API_KEY \
  --models JUDGE_MODEL \
  --k 1 --workers 8 --timeout 300 --max-calls 4000
```

评审模型应与生成模型不同；只有 GPT-5.2 时只能标“自评/单模型初评”。`k=1` 约 2800 次请求，`k=4` 约 7000 次请求。

### 7. 结果

| 内容 | 文件 |
|---|---|
| 子集记录/失败/产量 | `runs/gpt52_paper_v2_20261028/records_selected.jsonl` |
| 自动初评主表 | `runs/gpt52_paper_v2_20261028/auto/auto_report.md` |
| 逐题标签 | `runs/gpt52_paper_v2_20261028/auto/model_labels.jsonl` |
| 案例候选 | `runs/gpt52_paper_v2_20261028/auto/examples.jsonl` |
| 人工盲审 | `runs/gpt52_paper_v2_20261028/audit/audit_labels.csv` |

## 提示词与题目位置

| 文件 | 用途 |
|---|---|
| `experiment/prompts/paper_v2/zh/direct.txt` | 中文直接造题 system prompt |
| `experiment/prompts/paper_v2/zh/framework.txt` | 中文 system prompt，要求模型现场写生成器（不是生成器本身） |
| `experiment/prompts/paper_v2/en/direct.txt` | 英文直接造题 |
| `experiment/prompts/paper_v2/en/framework.txt` | 英文 system prompt，要求模型现场写生成器 |
| `experiment/prompts/paper_v2/README.md` | 提示词说明与论文映射（内部，不发送） |

实际发送的完整 messages 在 `runs/gpt52_paper_v2_20261028/traces/`；题目在 `results/`；C 的模型生成代码在 `programs/<seed>/attempt-*.py`，`accepted.json` 记录被采用的版本和 hash；统一记录在 `records.jsonl` / `records_selected.jsonl`。

## 对比口径

- 分别报告 PF−direct、PF−framework；不合成总分。
- 正确性/有效性是主终点；自动 `valid/invalid/uncertain` 只是代理，人工双审才作准。
- 主统计按 97 个 seed 配对 bootstrap；不能把 1000+ 题当独立样本。
- 深度、难度、证书评分只在有效且可评估子集报告，并给出覆盖。
- 当前脚本的配对区间是 PF−baseline；direct 与 framework 的差异先看分组表，B−C 区间需另加比较。

必须写明：PF 是历史筛选数据；语言要控制；单次生成不是稳定性实验；自动初评不是人工审核。

## 文档

- [实验协议](docs/experiment_protocol.md)：组别、种子、盲评、指标、统计边界。
- [运行手册](docs/gpt52_runbook.md)：预检、续跑、故障排查、成本、完成清单。
- [提示词说明](experiment/prompts/paper_v2/README.md)：中英对照、动态输入、论文映射。

## 验证

```bash
.venv/bin/python -m unittest discover -s tests -v
pyright
```

测试使用本地 HTTP mock、模拟响应和自写程序，不调用付费 API。
