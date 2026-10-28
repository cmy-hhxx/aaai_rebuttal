# 复现指南：GPT-5.2 造题 vs PuzzleForge（97 seeds / 1440 盲评）

本目录冻结了一次完整实验的全部输入、提示词、代码、中间数据、统计与图。按下面的顺序可以在同一网关上重跑。

## 1. 环境

- macOS arm64，Python 3.12.12。
- 生成运行时：`sympy==1.14.0`、`z3-solver==5.3.2.0`、`mpmath==1.3.0`（见 `code/runtime-requirements.lock`）。
- 分析运行时：`matplotlib==3.11.2`、`numpy==2.5.4`（见 `analysis/requirements-analysis.txt`）。
- 数据：仓库根 `sources/puzzleforge_supplement/data/`，129 个 seed、1720 道 PF 参考题；provenance 见 `sources/PROVENANCE.md`。本目录的 `run/snapshot/` 与 `run/seeds.json`、`run/reference.json` 保存了实际使用的输入。

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r final_experiment/code/runtime-requirements.lock
```

## 2. 凭据

只放在仓库根 `.env`（已 gitignore），不要写进任何 JSON 或本目录：

```text
OPENAI_API_KEY=...
JUDGE_API_KEY=...
```

endpoint 与模型参数在 `configs/gpt52_paper_v2_20261028.json`：

- base URL：`https://internal-idc-equ.ainvest.com/ind/iwc-aime-model/litellm/v1`
- 生成：`gpt-5.2`，`max_completion_tokens=32768`
- 评审：`gpt-5.6-luna`，`max_completion_tokens=16384`，k=1

## 3. 运行顺序

```bash
cd /Users/cmy/Desktop/aaai_rebuttal

# 1) 冻结输入（config/prompt/代码/数据 hash）
.venv/bin/python -m experiment.run prepare \
  --config configs/gpt52_paper_v2_20261028.json \
  --out runs/gpt52_final_20261028

# 2) direct 组：97 seeds × 4 批 × 5 题
.venv/bin/python -m experiment.run generate \
  --config configs/gpt52_paper_v2_20261028.json \
  --out runs/gpt52_final_20261028 \
  --method direct --seed-file configs/gpt52_seed_ids.txt

# 3) framework 组：每个 seed 由模型现场写生成器，本地 sandbox-exec 执行
#    在 DSH 里需要非沙箱 shell（否则 sandbox_apply 被拒）
.venv/bin/python -m experiment.run generate \
  --config configs/gpt52_paper_v2_20261028.json \
  --out runs/gpt52_final_20261028 \
  --method framework --seed-file configs/gpt52_seed_ids.txt

# 4) 导出 97 个 seed 的三组记录
.venv/bin/python -m experiment.run export \
  --out runs/gpt52_final_20261028 \
  --seed-file configs/gpt52_seed_ids.txt \
  --filename records_selected.jsonl

# 5) 盲评抽样：每 seed 每组 5 题，最少 1000
.venv/bin/python -m experiment.evaluation \
  --data runs/gpt52_final_20261028/records_selected.jsonl \
  --out runs/gpt52_final_20261028/audit \
  --per-seed 5 --min-audit 1000

# 6) 自动评审（1440 题 × 2 次请求）
export JUDGE_API_KEY=...
.venv/bin/python -m experiment.autojudge \
  --audit runs/gpt52_final_20261028/audit/audit_blind.jsonl \
  --key runs/gpt52_final_20261028/audit/audit_key.jsonl \
  --out runs/gpt52_final_20261028/auto \
  --endpoint https://internal-idc-equ.ainvest.com/ind/iwc-aime-model/litellm/v1 \
  --api-key-env JUDGE_API_KEY \
  --models gpt-5.6-luna \
  --k 1 --workers 8 --timeout 600 --max-calls 4000 \
  --parameters runs/gpt52_final_20261028/judge_parameters.json

# 7) 逐请求 token 记账
.venv/bin/python final_experiment/analysis/token_ledger.py \
  --run runs/gpt52_final_20261028 \
  --judge-dir runs/gpt52_final_20261028/auto

# 8) 统计与图
MPLCONFIGDIR=tmp/mplconfig tmp/figvenv/bin/python \
  final_experiment/analysis/analyze.py \
  --run runs/gpt52_final_20261028 \
  --figs runs/gpt52_final_20261028/figures
```

## 4. 预期计数

| 项目 | 期望 |
|---|---:|
| seed | 97 |
| matched / 组 | 1284 |
| 原始槽位 / 组 | 1940 |
| `records_selected.jsonl` 行数 | 5164 |
| 盲评 | 1440（480/组） |
| 生成请求 | 约 485 + 修复 |
| 评审请求 | 约 2880 + 格式修复 |

每 seed 的 `matched_slots` 由 `manifest.json` 固定；`cipher_18`、`cipher_25`、`logic_2`、`logic_3`、`operation_21` 的配额为 4，其余为 5–16。

## 5. 校验

```bash
cd final_experiment
shasum -a 256 -c checksums.sha256
```

`run/manifest.json` 内记录了 config、prompt、代码与输入的 SHA256；如任一文件变化，`prepare` 会拒绝复用目录。

## 6. 已知差异与边界

- 网关只暴露别名 `gpt-5.2`，不是 `gpt-5.2-2025-12-11`；本实验记录实际返回的 `model` 字段。
- PF 组是论文历史筛选后的测试集，不是同模型、同预算重跑；只能做固定 seed 下的测试集比较。
- 评审为单模型、k=1；pilot 上换 judge prompt 后有 8.4% 判定翻转，结论对评审版本敏感。
- `framework` 的程序由模型现场生成；`programs/<seed>/attempt-*.py` 与 `accepted.json` 保留每次尝试，失败不补题。
- `executor.py` 对 macOS sandbox 的 metadata 权限做过修复（否则 `execvp` EPERM）；沙箱内仍禁止读工作区文件与联网。

## 7. 运行噪声与冻结后修复

- **Azure 内容策略 400**：本次出现 2 次（direct 的 operation_4/0、operation_2/15），同一 payload 立即重放即通过；用同一 `generate` 命令重跑即可，不计为 `generation_failed`。
- **JSONL 行分隔符**：一条生成题面含 U+2029，`str.splitlines()` 会把它当换行，导致 `JSONDecodeError`。分析期把 `evaluation._jsonl`、`autojudge._read`、`analyze.jsonl` 改为只按 `\n` 切分；生成代码未变，不影响已冻结的生成数据。
- 这两项都是 `prepare` 之后的分析/重跑修复，`run/manifest.json` 里的 `input_hashes` 仍对应 prepare 时刻；若要完全从零复现，使用本目录 `code/` 的当前版本重新 `prepare` 即可。


## 8. PF spec 成本补测（pf_cost/）

PuzzleClone 的实例生成本地执行（0 API），但 spec 构造依赖缺失的 `ExternalApi` 与历史 usage。补测流程：

```bash
uv venv tmp/pfvenv --python 3.12
uv pip install -r puzzle_forge/requirements.txt langgraph
cd puzzle_forge
PATH=../tmp/pfvenv/bin:$PATH PYTHONPATH=../final_experiment/pf_cost \
OPENAI_API_KEY=... PF_USAGE_LOG=usage.jsonl PF_MAX_CALLS=25 \
python run_support_code_langgraph.py -question "<seed + answer>" \
  -question_name <seed> -output_folder out -workspace .
```

`pf_cost/sample_pf.py` 对 10 个 seed 批量执行并写 `pf_sample.jsonl`；原始逐调用 usage 与产出在 `pf_cost/raw/`；汇总在 `pf_cost/pf_cost_summary.json`。口径：仅 encoding+debugging，不含 expansion/evaluation，是下界。
