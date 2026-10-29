# Rebuttal - Response to Reviewer Comment 4

> **Reviewer comment**
>
> 4. The experiments primarily demonstrate the usefulness of PF-86K rather than the effectiveness of PuzzleForge as a framework.
>
> Much of the experimental section evaluates the difficulty of PF-86K and the downstream improvements. These results support PF-86K as a useful dataset, but provide less evidence that PuzzleForge is a superior data-generation framework.
>
> Important framework-level baselines are missing, such as direct LLM-based instance synthesis and direct LLM generation of executable generators without the proposed multi-stage decomposition. Otherwise, the paper may be more appropriately framed primarily as a benchmark/data contribution rather than a methodological framework contribution.

## Response

The comment identifies what the submission did not test, and we ran exactly that experiment: two missing framework-level baselines, direct instance synthesis (B1) and single-shot synthesis of a reusable generator with no multi-stage decomposition (B2), compared against the full pipeline (PF) on 97 shared seeds, blind-judging 1,440 items, 480 per condition. The 97 seeds are the Chinese-language subset of the paper's 129, selected by language only.

**Design.** B1 has GPT-5.2 emit problem, canonical answer and explanation directly, 20 items per seed in four batches of five, each batch shown its earlier output, with up to three repairs. B2 has GPT-5.2 write one reusable Python program per seed (stdin `{seed, count}`, stdout exactly `count` items), executed in a sandbox with a determinism probe and up to three attempts that receive the real execution error; no expansion agent, no DSL specification, no semantic or solving-based verification - the single-shot condition the comment names. B1 and B2 share model, decoding parameters and repair budget. PF is the test set emitted by the full pipeline. A judge model different from the generator sees only the problem, a canonical answer and an anonymous solver certificate; method and seed are stripped.

**Table T1 - what each pipeline yields per requested slot** (480 slots per condition, blind judging)

```
+-------------------------------+-------------+-------------+-------------+
|                               |     PF      |     B2      |     B1      |
+-------------------------------+-------------+-------------+-------------+
| valid items (of 480 slots)    | 366 (76.3%) | 352 (73.3%) | 134 (27.9%) |
| valid, >=3 dependent steps    | 301 (62.7%) | 162 (33.8%) |  28 (5.8%)  |
| reasoning depth, mean (0-4)   |    2.94     |    2.34     |    1.93     |
| median problem length (chars) |     692     |     321     |     297     |
| near-duplicate pairs @0.8     |    3.0%     |    24.9%    |    6.2%     |
| seeds with zero valid items   |    1/97     |    13/97    |    53/97    |
| tokens per valid item         |    1,227    |     527     |    4,571    |
+-------------------------------+-------------+-------------+-------------+
```

*Percentages are per slot (denominator 480), paired differences are seed-macro; the two never differ by more than 0.2 pp. Inference is seed-paired: Wilcoxon signed-rank, Holm across 21 tests, 95% intervals from 2,000 bootstrap resamples over seeds.*

**Results.** Against B1, PF is better on validity (+0.484 [+0.406, +0.556], p = 5.0e-14) and depth (+0.844), and B1's failure is silent: 71.7% of its items are invalid while only one has no output, and 331 of those 344 carry a wrong canonical answer on prose that reads perfectly well. Against B2, validity is equal (+0.027 [-0.054, +0.114]) and PF is better on depth (+0.605 [0.432, 0.780], 59 wins / 8 ties / 17 losses), specification length (+373 chars), lexical duplication (-22.8 pp) and structural duplication (-20.1 pp reasoning tags, -34.6 pp constraint tags). The "valid, >=3 dependent steps" row is the framework's headline: asked for 480 problems, PF returns 301 that pass blind verification and need at least three dependent steps, B2 returns 162 and B1 returns 28 (1.9x and 10.8x). Depth is not a length proxy: within condition, length explains almost none of the depth variance (r = 0.06 / 0.14 / 0.08).

**Attribution.** The three conditions isolate the three stages, each owning one measured property. Program grounding raises B1's validity from 0.278 to 0.734 (+0.456 [0.369, 0.547], p = 1.8e-13) and cuts wrong answers from 331 to 71. Expansion and parametric encoding add +0.605 depth, +373 characters and -22.8 / -34.6 pp duplication while validity stays flat. Closed-loop verification reduces zero-yield seeds from 13 to 1 and items with no output from 25 to 0.

**Cost.** Per valid item: 1,227 tokens for PF (187k per generator, amortised over 200 instances), 527 for B2, 4,571 for B1. B2 is 2.3x cheaper than PF, and the difference is exactly the verification stage it omits; what that stage buys is the +0.605 depth, the -22.8 pp duplication and the 13 to 1 reduction in zero-yield seeds reported above. Judging accounts for 66.3% of all tokens.

**Control.** PF is filtered data released with the paper, so the one confound worth testing is filtering: dropping the five seeds whose B2 generator produced nothing moves the validity difference from +0.027 to -0.010, while the depth and duplication differences are unchanged. The differences come from how generators are built and verified, not from filtering.

**Framing.** Seeds, backbone, budget and answer format are fixed and only generator construction and verification change, so this compares pipelines rather than datasets, and we are not reframing the paper as a data/benchmark contribution. The revision adds a subsection reporting these results, splits the third contribution into a framework-level and a dataset-level claim, and moves the certificate score to a depth-stratified presentation (it tracks depth identically across pipelines and is not used as framework evidence).

Prompts, generators, traces, blind-judging keys and the per-request token ledger ship with the paper: see [rebuttal_reproducibility.md](rebuttal_reproducibility.md), [rebuttal_tables.md](rebuttal_tables.md) and [rebuttal_figures.md](rebuttal_figures.md).
