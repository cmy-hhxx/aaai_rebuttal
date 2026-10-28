# PuzzleClone 源码审计：缺什么、怎么补

源码：`puzzle_forge/`（PuzzleClone，Apache-2.0）。结论先说：**实例生成是本地代码，不调 API；缺的是“把一个自然语言 seed 编码成可执行 spec”的一次性 token 账，仓库和上游都没有留下历史 usage 日志。**

## 1. 源码里有什么

- `translator.py` + `customs/` + `specs/`：给定 YAML spec，用 z3 本地批量生成题目实例。**没有模型调用**，所以 PF 的边际生成成本确实是 0。
- `run_support_code_langgraph.py`：5-agent 的 spec 构造/调试/评估流水线（expansion、encoding、debug、evaluation），调用 `model_client.text2text(...)`。
- `prompts/Stage/stage_1.md`（4,841 行）、`stage_88.md`（2,533 行）等：编码/修复用的超长提示词。
- `specs/` 298 个 YAML：历史产出的 generator（部分对应我们 97 个 seed，`cipher_*`/`logic_*`/`operation_*` 不在其中，需要重新编码）。

## 2. 缺什么

| 缺失项 | 证据 | 影响 |
|---|---|---|
| `ExternalApi` 模块 | 顶部 `from ExternalApi import ...`，`sys.path.append("/mnt/omniSSD/...")` | 流水线无法直接运行 |
| token/usage 日志 | 全仓库无 `usage`/`completion_tokens` 记录；`.gitignore` 排除 `output*`/`results*`/`config.json` | **历史 PF 的 token 消耗不可恢复** |
| API 配置 | `config.json` 被 ignore；模型端点是内部 `ep-20250822145246-jc6j8` | 不知道原始调用的模型/价格 |
| 运行输出 | 没有 `output/`、`results/`、`yaml/` 目录 | 无法从产物反推调用次数 |

## 3. 能补什么

1. **边际成本**：由代码可确认——`translator.py` 本地执行，0 API token/题。这一条可以直接写进论文，不需要重跑。
2. **一次性 spec 成本**：提供 `ExternalApi.py` shim + `sample_pf.py`，用同一模型（`gpt-5.2`）重跑编码流水线的小样本，记录每次调用的 prompt/completion token 与网关费用。

产物：

- `ExternalApi.py`：实现 `GPT5Client` / `DEEPSEEKClient` 的最小接口，逐调用写入 `PF_USAGE_LOG`。
- `sample_pf.py`：对 10 个 seed 逐个跑 `run_support_code_langgraph.py`，输出 `pf_sample.jsonl`（calls / tokens / cost / 是否产出 YAML）。
- `pf_sample.jsonl`：实测样本。

复现命令：

```bash
uv venv tmp/pfvenv --python 3.12
uv pip install -r puzzle_forge/requirements.txt langgraph

cd puzzle_forge
PATH=../tmp/pfvenv/bin:$PATH \
PYTHONPATH=../final_experiment/pf_cost \
OPENAI_API_KEY=... PF_USAGE_LOG=usage.jsonl PF_MAX_CALLS=25 \
python run_support_code_langgraph.py \
  -question "$(cat question.txt: 原题 + answer)" \
  -question_name seed_id -output_folder out -workspace .
```

## 4. 口径与限制

- 样本只跑 **encoding + debugging**，不含 expansion（K=3）与最终 evaluation；因此是 PF 一次性成本的**下界**。
- 模型用网关 `gpt-5.2`，与论文 backbone 同族；网关单价与论文内部端点可能不同，报告 token 数为主、美元为辅。
- 历史 PF-86K 的 432 个 generator 究竟花了多少 token 无法复原；样本均值只能作为估计，需在论文中标注“estimated from 10-seed replication”。
- 摊销口径：PF 设计上每个 generator 产 200 个实例；我们的对比每 seed 只用 20 个。报告同时给 `per 20` 与 `per 200` 两种，避免用 200 摊销掩盖小规模成本。
