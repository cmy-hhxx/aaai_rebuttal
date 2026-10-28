# PuzzleForge 数据质量对比

公开实验约定见 [docs/experiment_protocol.md](docs/experiment_protocol.md)。本仓库仅提交代码、提示词、非敏感配置及说明；完整审稿记录 `requirements.md`、投稿附件 `sources/`、题目和报告 `output/`、运行缓存均保留在本地。文中的原始附件／结果链接需在具备相应本地数据时打开。原全量计划为现有 PF 题1720道、两个新baseline各2580个槽位；当前任务缩小为约500道比较，全量任务已停止。

**新版 v2 已接入：**配置 [minimax_flash_v2_20261028.json](configs/minimax_flash_v2_20261028.json) 选择完整中文 system prompt，不拼接旧 quality.txt；`output_language=zh`。新目录为 `runs/minimax_flash_v2_20261028/`。从未用于旧试跑且参考题均含至少20个中文字符的种子中，按冻结随机规则抽取14个：两个 baseline 各计划生成280题；三组各164个匹配槽，共492槽。生成及84槽盲评均保留失败和未决结果，不按质量补选。

只运行本轮固定种子（不要省略 `--seed-ids`，否则会执行原129种子计划）：

```bash
.venv/bin/python -m experiment.run generate \
  --config configs/minimax_flash_v2_20261028.json --out runs/minimax_flash_v2_20261028 \
  --method both --seed-ids cipher_18 cipher_4 cipher_8 cipher_17 \
  logic_4 logic_11 logic_17 logic_3 operation_22 operation_20 operation_24 operation_5 word_sorting puzzle_15
```

本轮筛选规则见 `runs/minimax_flash_v2_20261028/pilot_500/selection.json`。完整新题分组保存在 `results/direct/`、`results/framework/`，源代码在 `programs/`，匹配数据导出为 `pilot_500/records_492.jsonl`，与两组全部原始输出一起汇总在 `pilot_500/records_raw_selected.jsonl`。已有数据目录保留，不能将旧分数算作新版结果。

本轮曾遇到300秒网络超时与长度截断，恢复过程单独记录在run内：恢复入口为 `pilot_500/recover_generation.py`，只处理未完成任务，保留已完成和三次失败结果。恢复仅把HTTP等待改为900秒、关闭自动HTTP重试；同一模型、token上限、三次生成／修复预算不变，严格重放已有真实截断响应后使用剩余修复次数。API重新请求本身不保证逐字相同；精确复现依赖已保存的请求／响应缓存，生成器采样和统计分析另由固定随机种子复现。

**v2已完成：**实际新题540道（直接280、生成器260），另外20个生成失败槽保留。匹配492槽中实际有题488道（参考164、直接164、生成器160），84槽单模型盲评全部处理。完整结论和独立核验保留在本地 [v2报告](output/minimax_flash_v2_500_report.md)、[九题独立核验](output/minimax_flash_v2_500_verified_cases.md)。分组题库位于 `pilot_500/puzzleforge.questions.jsonl`、`direct.questions.jsonl`、`framework.questions.jsonl`；两组全部新题另存 `direct.raw.questions.jsonl` 和 `framework.raw.questions.jsonl`。这些题目、报告、缓存与投稿附件不纳入公开仓库。

**上一轮 MiniMax 小规模试验：**使用 `MiniMax-M3.1-Flash`，选取13个相同种子，三组各168个配平位置；计划和结果位于 `runs/minimax_flash_20261028/pilot_500/`。已有未入选的全量运行结果保留，但不纳入该轮比较。

**上一轮结果：**504个配平位置实际得到480道题（PF168、直接生成168、生成器144），另24个生成失败位置保留。78槽单模型初评完成。[试跑主报告](output/minimax_flash_500_report.md)与[三组真实样题](output/minimax_flash_500_examples.md)保留。初步有更深／更难信号，但不能证明PF在所有质量维度更优；有效性区间跨0，且PF主要中文、baseline英文，语言控制未落实。

原配置 `configs/minimax_flash_20261028.json` 保留用于记录生成参数。入口自动读取根目录 `.env` 的字面量环境变量，不执行其中的 shell 命令；密钥无需另写进 JSON。**不要用下面的通用全量 pipeline 示例重启此次全量任务。**本次只运行指定种子：

```bash
.venv/bin/python -m experiment.run generate \
  --config configs/minimax_flash_20261028.json --out runs/minimax_flash_20261028 \
  --method both --seed-ids cipher_1 cipher_7 cipher_13 cipher_19 \
  logic_1 logic_7 logic_13 logic_19 operation_1 operation_3 operation_6 operation_9 knights_knaves_puzzle
```

## 1. 这个框架怎么用？

所有命令先在项目根目录执行：

```bash
cd /path/to/aaai_rebuttal
```

### 准备环境

本机已建立 Python 3.12 的 `.venv`，安装版本锁在 `runtime-requirements.lock`。重新建立环境时：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r runtime-requirements.lock
```

生成器执行使用 macOS `sandbox-exec`；只有运行时、系统库和任务目录可读，任务目录可写，网络及额外进程不可用。外层工具若禁止启动沙箱，需在授权的终端执行。缺少隔离能力会明确失败，不裸跑模型代码。

### 配置 API

```bash
# 只在本地配置不存在时复制，不覆盖已有配置
cp -n configs/experiment.example.json configs/local.json
```

打开 `configs/local.json`，修改以下字段，保留其他配置：

| 字段 | 填什么 |
|---|---|
| `endpoint` | 兼容端点，如 `https://YOUR_ENDPOINT/v1`，也可填写完整 `/chat/completions` URL |
| `model` | 端点实际支持的生成模型 id；默认 `gpt-5.2-2025-12-11` |
| `api_key_env` | 读取 key 的环境变量名，默认 `OPENAI_API_KEY` |
| `max_calls` | 生成阶段允许的 HTTP 尝试次数上限，默认 2000 |
| `evaluation.models` | 自动初评模型 id 列表；默认 `[]` 表示只生成、不调用评测 API |
| `prompt_variant` | `paper_v2` 使用新版完整提示词；省略时为 `legacy`，兼容旧配置 |
| `prompt_language` | 新版提示词语言：`zh` 或 `en`，默认 `zh` |
| `output_language` | 新版题面及解释语言：`zh` 或 `en`，默认 `zh`；与提示词语言分别配置 |

在当前 zsh 终端输入 key（按提示输入，不回显），再导出环境变量：

```bash
read -rs "OPENAI_API_KEY?请输入 API key: "
export OPENAI_API_KEY
```

默认生成模型为论文引用的 GPT-5.2；不能访问时明确记录差异，不静默替换。API key 不写入 JSON 配置。

若先做自动评测，在 `evaluation.models` 填评测模型 id（优先两个不同于生成模型的模型）。评测可以共用同一兼容端点，也可设置 `evaluation.endpoint` / `evaluation.api_key_env`。仅有一个模型时报告会标记证据较弱。`max_calls` 是 HTTP 尝试次数硬上限，包含重试；它不是美元额度。

先确认参数兼容、可用模型和预算：两个 baseline 通常需 516 次直接造题批次请求 + 129 次生成器初稿请求，修复和网络重试另计。774 道初评、两个模型、每模型 k=4 需 7740 次成功请求。当前默认生成上限 2000、评测上限 10000；根据授权预算在正式冻结前调整。

### 一条命令跑两个 baseline

完成配置后执行：

```bash
.venv/bin/python -m experiment.pipeline --config configs/local.json --out runs/main
```

这条命令会依次导入我们的 1720 道现成题、调用 API 直接造题、调用 API 编写生成器并执行造题、合并数据、检查产量和重复、生成匿名抽检材料。若配置了 `evaluation.models`，最后还会调用评测 API 生成自动初评报告；默认不会执行这一步。

`--out runs/main` 指定本次实验的保存目录，下面的输出路径均以它为准。改为 `--out runs/gpt52_run2` 时，本次产物都写入新目录。**重新执行同一命令可续跑**；不要为了续跑而改用新目录。

仅准备输入、暂不调用 API：

```bash
# 只准备输入与配额，不调用 API；可检查 manifest 和历史题导出
.venv/bin/python -m experiment.run prepare --config configs/local.json --out runs/main
```

同一命令续跑会读取缓存和已完成批次。配置、prompts、代码、输入或生成运行时改变会拒绝复用目录；需新建 run。改变 endpoint 应在首次 prepare **之前**完成。`runs/` 被 Git 忽略，但需自行备份以复现；缓存不是可删除的临时垃圾。

### 只跑一种方法，或分步骤运行

```bash
# B：直接用提示词让模型造题
.venv/bin/python -m experiment.run generate --config configs/local.json --out runs/main --method direct

# C：让模型写生成器，再执行生成器造题
.venv/bin/python -m experiment.run generate --config configs/local.json --out runs/main --method framework

# 更新合并题库；分步骤生成后执行这一步，合并文件才会包含新结果
.venv/bin/python -m experiment.run export --out runs/main

# 离线重复统计与匿名抽样，不调用 API
.venv/bin/python -m experiment.metrics --data runs/main/records.jsonl --out runs/main/lexical_metrics.json
.venv/bin/python -m experiment.evaluation --data runs/main/records.jsonl --out runs/main/audit
```

注意：单独执行 `generate` 保存的是分批结果，不会自动更新 `records.jsonl`；一键 `pipeline` 会自动合并。

自动初评也可在生成完成后单独调用（URL、模型名以下为占位符，不能原样运行）：

```bash
.venv/bin/python -m experiment.autojudge \
  --audit runs/main/audit/audit_blind.jsonl \
  --key runs/main/audit/audit_key.jsonl \
  --out runs/main/auto \
  --endpoint 'https://YOUR_ENDPOINT/v1' \
  --models JUDGE_MODEL_A JUDGE_MODEL_B --k 4 --max-calls 10000
```

提供给 API 的是匿名题面／答案／评测证书；私有映射只在本地聚合。原生解释缺失不算 0 分：PF 没有原生解释，统一证书的可核查度由相同解题器和评审流程衡量。

人工正确性／深度盲审包也不包含原生解释；原生解释另存 `.private.jsonl`，不要与第一轮盲审材料一起发出。人工表的解释评分在第一轮留空，避免从 PF 缺少解释推断组别。

## 2. 调用 API 的提示词在哪里？

**新版中英文提示词已接入：**[中文直接造题](experiment/prompts/paper_v2/zh/direct.txt)、[中文编写生成器](experiment/prompts/paper_v2/zh/framework.txt)。它们都是完整 system prompt，保留论文方法的通用多样性与验证要求，正文保留 L1–L4 标签及含义，不出现论文专名；[中英对照及论文对应说明](experiment/prompts/paper_v2/README.md)包含英文版和动态输入，属于内部说明，不发送给模型。配置 `prompt_variant=paper_v2` 时仅发送所选语言的对应文件；下面的旧版位置继续对应 `legacy` 配置和上一轮数据。

### 生成提示词

| 文件 | 用途 |
|---|---|
| [quality.txt](experiment/prompts/quality.txt) | B/C 共用的题目质量要求：正确性、多样性、推理深度、答案格式和解答证书 |
| [direct.txt](experiment/prompts/direct.txt) | B：直接生成题面的具体指令 |
| [framework.txt](experiment/prompts/framework.txt) | C：编写可复用 Python 生成器的指令、stdin/stdout 接口和自检要求 |

实际生成请求由 [run.py](experiment/run.py) 中的 `generate()` 组装：

1. `system` 消息：`legacy` 为 `quality.txt` + 对应方法文件；`paper_v2` 为所选语言的完整单文件。真实运行从 snapshot 读取并校验 manifest 中的 hash，缺失／被改时停止。
2. 第一条 `user` 消息 = 当前种子的 `seed_question` 和 `seed_answer`，来自 `sources/puzzleforge_supplement/data/seed_puzzles.jsonl`。
3. 下一条 `user` 消息：B 提供本批数量和自己之前已生成的题；C 提供可用依赖和目标数量；v2 两组都明确传入 `output_language`。
4. 需要修复时，追加模型上一次输出和真实格式／执行错误反馈。

**要看某次真正发给 API 的完整提示词，查看运行目录里的 `traces/`，不要只看模板文件：**

```text
runs/main/traces/direct/<seed_id>/<batch_start>/attempt-0.json
runs/main/traces/framework/<seed_id>/0/attempt-0.json
```

文件保存完整 `messages` 数组；修复请求依次为 `attempt-1.json`、`attempt-2.json`。`api_cache/*.request.json` 还保存该请求实际使用的 endpoint、model、messages 和生成参数。

### 自动评测提示词

[autojudge.py](experiment/autojudge.py) 中的 `SOLVE_SYSTEM` 是独立解题提示词，`JUDGE_SYSTEM` 是质量评审提示词。评测的完整请求和响应保存在 `runs/main/auto/api_cache/`，与生成阶段的日志分开。

提示词会被复制到 `snapshot/` 并记录 hash。正式运行后修改提示词，需要使用新实验目录。

## 3. 三种方法造出的题分别放在哪里？

以下路径对应 `--out runs/main`，完整输出根目录为 `<project_root>/runs/main/`。除原始 PF 附件外，这些文件在实际运行对应步骤后才会出现；目前还没有新生成的真实 baseline 题。

| 方法 | 原始／分组题目文件 | 文件里是什么 |
|---|---|---|
| A：我们的 PF 数据 | `sources/puzzleforge_supplement/data/test_normal.jsonl`、`test_hard.jsonl` | 投稿附件原始题库，分别 862、858 道 |
| A：本次实验统一格式 | `runs/main/reference.json` | 导入后的全部 1720 道 PF 题，JSON 数组 |
| B：API 直接造题 | `runs/main/results/direct/<seed_id>/<batch_start>.json` | 每批题目的 JSON 数组；默认每批 5 道，文件名为 `00.json`、`05.json`、`10.json`、`15.json` |
| C：API 写生成器后造题 | `runs/main/results/framework/<seed_id>/00.json` | 该 seed 的 20 个题目槽位，JSON 数组 |
| 三组统一合并题库 | `runs/main/records.jsonl` | 每行一道记录；完整运行包含 6880 个槽位，包括生成失败记录 |

**C 组的生成器代码与题目文件是分开放的：**

```text
runs/main/programs/<seed_id>/attempt-0.py       # API 写出的 Python 程序
runs/main/programs/<seed_id>/attempt-1.py       # 若有修复，保留修复版本
runs/main/programs/<seed_id>/accepted.json      # 被采用的版本、代码 hash、采样 seed
runs/main/results/framework/<seed_id>/00.json  # 程序实际造出的题
```

每道统一记录主要看这些字段：

- `method`：`puzzleforge`、`direct` 或 `framework`，区分来源。
- `problem`、`answer`、`explanation`：题面、答案和原生解答；PF 原生解释缺失为 `null`。
- `seed_id`、`slot`：原始种子及生成槽位。
- `status`：`ok` 是有符合输出格式的题，`generation_failed` 是生成失败；`ok` 不等于题目已经通过质量评审。
- `cohort`：`matched` 进入三组配平主比较，`extra` 只做补充分析。

如果希望把各组成功输出汇总成三个独立 JSONL 文件，**先完成 `export`**，再在项目根目录执行：

```bash
jq -c 'select(.method == "puzzleforge" and .status == "ok")' runs/main/records.jsonl > runs/main/puzzleforge.questions.jsonl
jq -c 'select(.method == "direct" and .status == "ok")' runs/main/records.jsonl > runs/main/direct.questions.jsonl
jq -c 'select(.method == "framework" and .status == "ok")' runs/main/records.jsonl > runs/main/framework.questions.jsonl
```

这三个是手动汇总文件，不是程序默认自动生成的文件；只保留有输出的题。实验统计仍以保留全部失败槽位的 `records.jsonl` 为准。

### 评测报告和其他产物

以下路径相对于 `runs/main/`：

- `manifest.json`：数据、代码、prompt hash、模型与参数、环境、主表槽位和输入规模。
- `snapshot/`：冻结的实验代码、prompts、实际输入和依赖锁；保留原字节，供离线重放和审查。
- `api_cache/`：完整请求响应、usage、模型返回名称、重试及缓存；不保存鉴权头。
- `programs/`：模型生成的程序、每次修复、探针、采样 seed 和隔离任务日志。
- `records.jsonl`：全槽位统一数据。失败不会被删除，matched 与 extra 分开。
- `yield_status.json`：分别检查两个 baseline 是否达到 2000 道成功唯一题；目标未达成会明确显示。
- `generation_costs.json`、`evaluation_costs.json`：实际请求、提供方返回的 token 用量及 API 耗时；缺失用量和历史成本不补造。
- `lexical_metrics.json`：词面近重复指标，不能称作语义多样性。
- `audit/audit_blind.jsonl`、`audit/audit_labels.csv`：774 道固定匿名样本和后续人工审核模板。
- `auto/model_labels.jsonl`、`auto/auto_report.md`、`auto/examples.jsonl`：模型初评、分项指标、真实支持／反驳／相近案例候选。
- `audit/report.md`：后续填写独立双人审核及必要裁决后生成的报告。自动标签不得代填人工表。

```bash
.venv/bin/python -m experiment.evaluation \
  --data runs/main/records.jsonl --out runs/main/audit \
  --labels runs/main/audit/audit_labels.csv
```

生成中断和 API／执行器不可用不是“低质量题”。完整生成仍需检查每个 baseline 的成功唯一题是否达到 2000；2580 个槽位不是有效题数的保证。A 为已筛选历史测试集；自动指标是代理，不能仅凭本轮声称框架对所有模型、所有质量维度都更优。

## 验证

```bash
.venv/bin/python -m unittest discover -s tests -v
pyright
```

测试使用本地 HTTP mock、模拟模型响应和自写程序，不调用付费 API。macOS 沙箱已另外实测数学／约束求解、文件／网络／进程限制及超时。
