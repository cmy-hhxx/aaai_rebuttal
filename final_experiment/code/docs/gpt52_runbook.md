# 运行手册：GPT-5.2 造题与对比

本手册补充 [README](../README.md) 的操作细节：预检、续跑、故障处理、成本和完成标准。设计与指标见 [实验协议](experiment_protocol.md)。

## 1. 运行前检查

| 检查项 | 要求 |
|---|---|
| Python | `.venv/bin/python` 为 3.12，依赖按 `runtime-requirements.lock` 安装 |
| 数据 | `sources/puzzleforge_supplement/data/` 下有 129 个 seed、1720 道 PF 参考题 |
| 平台 | macOS；framework 组执行 GPT-5.2 现场返回的程序，需要可用的 `sandbox-exec` |
| endpoint | 已填进 `configs/gpt52_paper_v2_20261028.json`，且在 `prepare` 之前 |
| key | 只在 `OPENAI_API_KEY` 或根目录 `.env`，不写进 JSON |
| 评审模型 | 已确定独立模型；若只有 GPT-5.2，报告只能标“自评” |

预检：

```bash
.venv/bin/python -m experiment.run prepare \
  --config configs/gpt52_paper_v2_20261028.json \
  --out runs/gpt52_paper_v2_20261028

jq '{model: .config.model, prompt: .config.prompt_variant,
     language: .config.output_language,
     matched_total: ([.matched_slots[] | length] | add),
     counts: .counts}' runs/gpt52_paper_v2_20261028/manifest.json
```

预期：`model=gpt-5.2-2025-12-11`、`prompt=paper_v2`、`language=zh`、`matched_total=1720`。`matched_total` 是全 129 seed 的配额；本轮 97 seed 的实际 matched 从 `records_selected.jsonl` 统计。`counts` 是协议原始规模，不是本轮实际生成量。

## 2. 分步操作

命令全文见 README 第 3–6 步。各步只做一件事：

1. **generate**：跑 97 个语言控制 seed；B 直接出题，C 由 GPT-5.2 现场写程序；失败和修复结果保留。
2. **export**：只导出这 97 个 seed，写 `records_selected.jsonl`，不要拿全量 `records.jsonl` 做盲评抽样。
3. **evaluation**：生成 1000+ 题盲评材料；`--min-audit 1000` 会在不足时失败。
4. **autojudge**：用独立评审模型做解题+评审；自动标签不写进人工表。

每一步的检查：

```bash
# 生成后：每个 seed 的批次文件是否齐全
find runs/gpt52_paper_v2_20261028/results -name '*.json' | wc -l

# 导出后：三组行数
jq -s 'group_by(.method) | map({method: .[0].method, n: length,
       matched: map(select(.cohort=="matched")) | length})' \
  runs/gpt52_paper_v2_20261028/records_selected.jsonl

# 盲评准备后：必须 >= 1000
wc -l runs/gpt52_paper_v2_20261028/audit/audit_blind.jsonl
wc -l runs/gpt52_paper_v2_20261028/audit/audit_key.jsonl

# C 组：确认代码是模型现场返回的，不是仓库预置的
ls runs/gpt52_paper_v2_20261028/programs/<seed_id>/
jq '{attempt, sample_seed, code_sha256}' \
  runs/gpt52_paper_v2_20261028/programs/<seed_id>/accepted.json

# 自动初评后：报告与逐题标签
ls runs/gpt52_paper_v2_20261028/auto/auto_report.md \
   runs/gpt52_paper_v2_20261028/auto/model_labels.jsonl
```

预期行数：`records_selected.jsonl` 约 5180（PF 约 1300、direct 1940、framework 1940），其中 matched 从 `records_selected.jsonl` 统计；盲评约 1400，且至少 1000。

## 3. 续跑与故障

### 续跑

同一条 `generate` 命令重新执行即可：

- 已有 `results/<method>/<seed>/<batch>.json` 会跳过。
- 已保存的 `traces/attempt-*.json` 会按原 messages 重放。
- `api_cache/` 命中直接返回原响应。
- 改了 config、prompt、代码或输入，`prepare` 会拒绝复用目录；必须新建 run。

### 常见错误

| 现象 | 含义 | 处理 |
|---|---|---|
| `Set endpoint` | config 没填 endpoint | 填好后再 `prepare` |
| `Frozen run changed` | config/输入/prompt 变了 | 新建 run 目录，不改旧目录 |
| `runtime not available` | sandbox 不可用 | 换允许启动 `sandbox-exec` 的终端，不裸跑 |
| `truncated_response` | 达到 token 上限 | 已进入修复；看 `traces/.../attempt-*.json` |
| `call_budget_exhausted` | 请求硬上限用完 | 提高 `max_calls` 或新建 run，不绕过预算 |
| 盲评少于 1000 | 子集不完整或 per_seed 太小 | 确认 97 seed 子集；把 `--per-seed` 提到 6 |
| auto 报告 pending | 初评未跑完 | 续跑同一 `autojudge` 命令 |
| 区间跨 0 | 无差异或证据不足 | 不能写“显著更优” |

### 失败语义

- 格式错误、截断、三次修复仍失败 → `generation_failed`，保留槽位。
- 网络、鉴权、预算错误 → 基础设施问题，停机后续跑；不要计为方法质量差异。
- 自动评审 schema 三次失败 → 执行未决；不要伪造 valid/invalid 标签。

## 4. 成本

| 阶段 | 成功请求（约） |
|---|---:|
| direct 生成 | 388 |
| framework 生成 | 97 |
| 自动初评 k=1 | 约 2800 |
| 自动初评 k=4 | 约 7000 |

修复和重试会增加请求。`max_calls` 是 HTTP 尝试硬上限，不是美元额度；金额需要端点真实单价。生成与评测用量分别写入 `generation_costs.json`、`evaluation_costs.json`。

## 5. 完成标准

- [ ] `manifest.json` 的 model、prompt、language 与协议一致
- [ ] C 的 `programs/<seed>/attempt-*.py` 来自 API 响应，代码 hash 已记录
- [ ] 97 个 seed 的 B/C 结果齐全，失败槽位保留
- [ ] `records_selected.jsonl` 的 matched 总量与 manifest 一致
- [ ] `audit_blind.jsonl` 至少 1000 行，且不含 method/seed/原生解释
- [ ] `auto_report.md` 标明模型数、k、覆盖和 `uncertain`
- [ ] 人工表没有被自动标签代填
- [ ] 报告写清 PF 历史数据、语言、单次生成、自动代理的边界
- [ ] 没有预设“PF 全面胜出”的结论
