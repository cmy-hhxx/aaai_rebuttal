# final_experiment：GPT-5.2 vs PuzzleForge 的完整留档

这个目录存放最终实验（97 seeds / 1440 道盲评）的全部可复现材料：配置、提示词、代码快照、生成程序、盲评输入、逐题标签、逐请求 token、统计、图与报告。密钥不在目录内。

## 目录

| 路径 | 内容 |
|---|---|
| `REPRODUCE.md` | 从零重跑的命令、计数与校验方式 |
| `environment/environment.json` | Python/包版本、endpoint、模型 id、参数、平台 |
| `configs/` | 实验配置与 97 个 seed 清单 |
| `prompts/paper_v2/` | 中英文 direct/framework system prompt 与 checksums |
| `code/experiment/` | 实际运行的 Python 包（run/evaluation/autojudge/executor/api/...） |
| `code/tests/` | 单元测试（mock，不调用付费 API） |
| `code/docs/` | 实验协议、运行手册、论证草稿 |
| `analysis/analyze.py` | 统计与 7 张图的生成脚本 |
| `analysis/token_ledger.py` | 逐请求 token 汇总脚本 |
| `pf_cost/` | PF spec 构造成本补测：ExternalApi shim、10-seed 样本、原始 usage 日志、PF 成本图 |
| `run/` | 冻结清单、输入快照、生成结果、程序、traces、盲评、标签、token、统计、图、报告 |
| `prior/200_item/` | 200 题中间实验的报告、统计、token 明细与图 |
| `prior/105_item_pilot/` | 105 题 pilot 报告 |
| `checksums.sha256` | 本目录全部文件的 SHA256 |

## 关键结果（97 seeds / 1440 盲评）

完整数字见 `run/REPORT_1000.md`。

- 有效率：PF 0.76，direct 0.28，framework 0.73（条件 0.774）；PF−direct +0.48 [+0.41, +0.56]，PF−framework +0.03 [−0.05, +0.11]。
- 深度：PF 2.94 > framework 2.34 > direct 1.93；题面中位 692 / 321 / 297 字符。
- 重复（0.8 阈值）：PF 3.0%，direct 6.2%，framework 24.9%；framework 21/92 个 seed 的重复率 ≥50%，11 个 100%。
- 生成 token/有效题：framework 527，PF@200 1,227，direct 4,571，PF@20 12,267；PF 的 spec 构造成本 187k token/generator（10-seed 补测）。
- 3402 个请求、9,571,338 token、$25.86，评审占 66.3%。

## 完整性

```bash
cd final_experiment && shasum -a 256 -c checksums.sha256
```

`run/manifest.json` 记录 config、prompt、代码、输入的 hash；任何文件被改动都会被 `prepare` 拒绝复用。
