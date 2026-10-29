# PuzzleForge rebuttal

最终交付：

- [rebuttal_response.md](rebuttal_response.md) — 英文 Rebuttal
- [rebuttal_response_zh.md](rebuttal_response_zh.md) — 中文翻译
- [rebuttal_illustrated.docx](rebuttal_illustrated.docx) — 带图的双语版（4 张图，Word）
- [rebuttal_illustrated.pdf](rebuttal_illustrated.pdf) — 同上的 PDF

## 这次补的实验

在 97 个共享 seed 上，用同一 GPT-5.2 跑三条流水线并做盲评（每组 480 题，共 1,440 题）：

- **PF**：论文发布的 test split（每生成器 2% 随机 holdout，经过流水线自己的去重与生成器过滤）。
- **B1**：直接生成题目实例（direct）。
- **B2**：直接生成一个可复用 Python 生成器，沙箱执行；三次带真实报错的调试，无 expansion / DSL / 语义验证。

## 核心结果

- 对 **B1**：PF 显著更好（有效率 +0.484；深度 +0.844）；B1 71.7% 无效，且多数是静默的答案错误。
- 对 **B2**：有效率持平（生成器级 0.775 vs 0.774）；PF 的 **>=3 步产出率**是 62.7% vs 33.8%（1.86×），按长度分布标准化后 +24.6 pp [+11.6, +35.9]。
- 深度：原始 +0.602，OLS +0.418，但严格长度匹配（CEM）+0.207 [-0.020, +0.443]；因此 depth 作为支持性证据，主主张是 >=3 步产出率。
- 成本：同一摊销尺度下 PF/B2 约 **23-25×**（200 实例/单位：1,227 vs 50；20 实例/单位：12,267 vs 527）。
- 跨家族评审（560 题交叉子样本）：exact agreement 83.4%，kappa 0.67；PF−B2 有效率差随 judge 翻符号，B1 在两个家族下都是 72-74% invalid。
- PF 的 23.1% invalid 是 judge-specific 的偏高代理；两个真实例子（积分符号错误、0.01 舍入差）说明它混合了实质错误与瑕疵。

## 数据与复现

- 生成、盲评、token 账本：`final_experiment/run/`
- 分析脚本：`final_experiment/analysis/`
- 第二批评审（560 题交叉子样本）：`runs/judge_k3/agreement.md`
- 表格中间量：`final_experiment/run/analysis/`

## 归档

旧的表格、可复现说明、2,500 字符短版与 4,000 字符版都在 `tmp/archive_rebuttal/`，需要时再取。

## 带图版本

`rebuttal_illustrated.docx / .pdf` 是英文 Rebuttal + 中文翻译的排版版，内嵌 4 张图：

1. 盲评有效率（PF / B2 / B1）。
2. 按题面长度五分位的 depth 与 >=3 步产出率。
3. 两个摊销尺度下的每有效题 token。
4. 两个评审家族在 560 题重叠样本上的有效率区间。

图源在 `tmp/doc_figures/`，生成脚本是 `tools/make_doc_figures.py`；文档脚本是 `tools/build_rebuttal_docx.py`。
