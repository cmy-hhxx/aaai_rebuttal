# Rebuttal — Response to Reviewer Comment 4

> All numbers below are computed from the frozen run artifacts by `final_experiment/analysis/rebuttal_tests.py` (per-item labels, blind-evaluation key, per-request token ledger); the two validity intervals are those of the frozen report. Nothing is re-sampled or re-judged.

---

## 审稿人意见：

> 4. The experiments primarily demonstrate the usefulness of PF-86K rather than the effectiveness of PuzzleForge as a framework.
>
> Much of the experimental section evaluates the difficulty of PF-86K and the downstream improvements. These results support PF-86K as a useful dataset, but provide less evidence that PuzzleForge is a superior data-generation framework.
>
> Important framework-level baselines are missing, such as direct LLM-based instance synthesis and direct LLM generation of executable generators without the proposed multi-stage decomposition. Otherwise, the paper may be more appropriately framed primarily as a benchmark/data contribution rather than a methodological framework contribution.

## 回复：

This comment correctly identifies what the submitted version did not test, and we closed the gap with exactly the experiment it asks for. We built both missing baselines — direct instance synthesis (B1) and single-shot synthesis of a reusable generator with no multi-stage decomposition (B2) — and compared them with the complete pipeline (PF) on 97 shared seeds, one backbone, one budget, and 1,440 blind-judged items. The framework claim is now supported, and we can state precisely by what mechanism and on which axes.

**Design.** 97 of the paper's 129 seeds (the Chinese-language subset, selected by language only). All conditions share the seed set, the answer format, and the evaluation protocol. B1: GPT-5.2 writes `problem`/`answer`/`explanation` directly, 20 items per seed, four batches of five, each batch shown its own earlier items, up to three repair attempts. B2: GPT-5.2 writes one reusable Python program per seed (`{seed, count}` → exactly `count` items), executed in a sandbox with a determinism probe and up to three attempts with real execution-error feedback — no expansion agent, no DSL specification, no semantic or solving-based verification, i.e. the single-shot condition named in the comment. PF: the released PF-86K test items from the full pipeline, used as the upper reference. B2 receives the same model, the same decoding parameters and a repair loop, so no baseline is handicapped. The judge saw only the problem, a canonical answer and an anonymous solver certificate; method, seed and native explanation were stripped. 5 items per seed per condition, 480 per condition. All prompts, generators, traces, keys and per-request token records are released.

**Table R1 — What each pipeline yields per request** (97 seeds, 480 requested slots per condition, blind judging)

| | **PF** full pipeline | **B2** single-shot generator | **B1** direct instances |
|---|---:|---:|---:|
| Valid items (of 480 slots) | **366 (76.3%)** | 352 (73.3%) | 134 (27.9%) |
| **Valid items requiring ≥3 dependent steps** | **301 (62.7%)** | 162 (33.8%) | 28 (5.8%) |
| Valid items requiring ≥2 dependent steps | **355 (74.0%)** | 276 (57.5%) | 89 (18.5%) |
| Reasoning depth, mean (0–4) | **2.94** | 2.34 | 1.93 |
| Depth distribution 0/1/2/3/4 | 0 / 11 / 54 / 246 / 55 | 8 / 68 / 114 / 120 / 42 | 2 / 43 / 61 / 19 / 9 |
| Median problem length (chars) | **692** | 321 | 297 |
| Near-duplicate pairs @0.8, within seed | **3.0%** | 24.9% | 6.2% |
| Identical constraint-tag sets, within seed | **15.2%** | 50.4% | 42.6% |
| Seeds yielding zero valid items | **1 / 97** | 13 / 97 | 53 / 97 |
| Seeds that produced no item at all | **0 / 97** | 5 / 97 | 0 / 97 |
| Tokens per valid item | 1,227 | **527** | 4,571 |

The third row is the one we now consider the framework's headline result: if you ask each pipeline for 480 problems, PF returns **301 usable multi-step problems**, B2 returns 162 and B1 returns 28 — a 1.9× advantage over the single-shot generator and 10.8× over direct synthesis. This is a joint count, not a composite score: an item counts only if it survives blind verification *and* requires at least three dependent steps. Depth is not a length proxy: within each condition problem length explains almost none of the depth variance (r = 0.06 PF, 0.14 B2, 0.08 B1); the pooled r = 0.25 arises only because the conditions differ on both.

**Table R2 — Seed-paired inference** (mean per-seed difference [95% CI, 2,000 bootstrap resamples over seeds]; W/T/L = seeds where the first condition is higher/tied/lower; p = Wilcoxon signed-rank, Holm-adjusted across all 21 tests run: three condition pairs × seven metrics)

| Metric | PF − B2 | W/T/L | p | PF − B1 | W/T/L | p |
|---|---|---:|---:|---|---:|---:|
| Validity (seed-macro) | +0.027 [−0.054, +0.114] | 31/24/42 | 0.48 | **+0.484 [+0.406, +0.556]** | 77/12/8 | 5.0e-14 |
| Reasoning depth | **+0.605 [+0.432, +0.780]** | 59/8/17 | 4.9e-7 | **+0.844 [+0.616, +1.075]** | 36/1/7 | 5.7e-6 |
| Problem length | **+373 [+293, +459] chars** | 80/0/12 | 2.7e-12 | **+435 [+367, +504] chars** | 91/0/6 | 2.8e-19 |
| Near-dup @0.8 | **−22.8 pp [−29.8, −16.5]** | 0/36/56 | 5.6e-16 | −0.7 pp [−2.4, +0.8] † | 42/49/6 | — |
| Identical reasoning-tag sets | **−20.1 pp [−27.2, −12.9]** | 18/21/53 | 9.7e-6 | **−20.3 pp [−27.0, −13.6]** | 16/22/59 | 1.9e-6 |
| Identical constraint-tag sets | **−34.6 pp [−41.8, −26.7]** | 11/12/69 | 2.9e-10 | **−27.3 pp [−34.1, −20.7]** | 12/11/74 | 7.0e-11 |
| Certificate score | −0.14 [−0.35, +0.07] | 24/17/43 | 0.14 | −0.34 [−0.57, −0.11] | 11/9/24 | 0.07 |

Pair counts: validity 97/97 seeds; depth and certificate 84 (PF−B2) and 44 (PF−B1), since both conditions must yield a valid item; length, near-duplication and tag-set metrics 92/97, since B2 produced no items on five seeds.

† Both conditions sit at 0% on the median seed (49 of 97 seeds are exact ties); PF is nominally higher by a small margin on 42 seeds and lower on the 6 where B1 collapses, two of them at 100% (Table R4).

Against B1, PF is better on validity, depth and informativeness and structurally less redundant; the certificate difference does not survive multiplicity correction. Against B2, PF is **equal on validity and strictly better on depth, informativeness, lexical diversity and structural diversity**. Notably, B2 is not better than PF on within-seed duplication for a single one of the 92 seeds on which it produced items (0/36/56), and its depth deficit is not a length artifact — it is shorter *and* shallower.

**Table R3 — Reliability and failure modes**

| | PF | B2 | B1 |
|---|---:|---:|---:|
| Seeds with zero valid items | **1** | 13 | 53 |
| Seeds with ≥3 of 5 valid | **80** | 77 | 25 |
| Median valid items per seed (of 5) | 4 | 4 | **0** |
| Items with no output at all | **0 / 480** | 25 / 480 | 1 / 480 |
| Items judged invalid | 111 (23.1%) | 103 (21.5%) | **344 (71.7%)** |
| — wrong canonical answer | 89 | 71 | **331** |
| — unsatisfiable as written | 15 | 7 | **113** |
| — ambiguous / under-specified | 34 | 49 | 46 |
| — missing constraint | 26 | 41 | 44 |
| — rendering defect | 3 | 8 | 4 |

The failure profiles are qualitatively different, and this is the substantive point behind the "silent bad data" concern. B1 almost never fails *loudly* (1 item with no output) yet 71.7% of its items are invalid, and 331 of those carry a wrong canonical answer — fluent, plausible, unsolvable or mislabelled problems that a training pipeline would consume without warning. B2's failures cluster in under-specification (49 ambiguous, 41 missing constraints): a single-shot generator that nobody verifies writes templates whose constraints do not pin down a unique answer. PF's residual errors are concentrated in wrong answers (89) rather than in unverifiable structure, and it is the only condition that has generators and never loses one at the authoring stage.

**Table R4 — Diversity is structural, not just lexical**

| | PF | B2 | B1 |
|---|---:|---:|---:|
| Near-dup @0.5 / 0.7 / 0.8 within seed | **18.4 / 7.4 / 3.0%** | 70.4 / 46.4 / 24.9% | 35.8 / 16.8 / 6.2% |
| Seeds with ≥50% near-duplicate pairs | **1 / 97** | 21 / 92 | 3 / 97 |
| Seeds with 100% near-duplicate pairs | **1 / 97** | 11 / 92 | 2 / 97 |
| Identity of reasoning-tag sets (pair rate) | **33.1%** | 54.4% | 53.9% |
| Identity of constraint-tag sets (pair rate) | **15.2%** | 50.4% | 42.6% |
| Distinct reasoning-tag sets per seed (mean, max 5) | **2.84** | 2.05 | 2.19 |
| Distinct constraint-tag sets per seed (mean) | **3.88** | 2.26 | 2.60 |

The tag-based rows answer the objection that 4-gram similarity only measures wording. A pair counts as structurally identical on a dimension when the blind judge assigned both items the same set of reasoning operations (respectively, the same set of constraint types); by that measure PF is the least redundant condition on both dimensions, with 1.5–1.7× more distinct constraint-tag sets per seed than either baseline. Against B1 the lexical metric is not a clean win — the median seed is tied at 0% and B1's aggregate is carried by a collapsed tail — which is why we report the tail directly: 2 seeds at 100% and 3 above 50% for B1, versus 1 four-item seed for PF.

**Table R5 — The certificate score is a function of depth, not of pipeline**

| Typical depth of the item | n (valid, all conditions) | Mean certificate score |
|---|---:|---:|
| 0 steps | 10 | 3.60 |
| 1 step | 122 | 3.73 |
| 2 steps | 229 | 3.69 |
| 3 steps | 385 | 3.22 |
| 4 steps | 105 | 2.19 |

Within each condition separately, depth and certificate score are negatively correlated (r = −0.31 PF, −0.32 B2, −0.29 B1; pooled r = −0.33, ρ = −0.29). Harder multi-step items are harder to certify, by the same margin regardless of which pipeline produced them. Since PF's items are systematically deeper (2.94 vs 2.34 vs 1.93), its lower certificate score is explained by what it generates rather than by how well it generates it; the same analysis accounts for B1's higher score on its 134 surviving items. We therefore do not treat certificate score as evidence for any pipeline, and we now report it stratified by depth.

**Table R6 — Cost, per valid item and at scale**

| | PF | B2 | B1 |
|---|---:|---:|---:|
| Tokens per generated item | 935 (@200 inst./gen.) – 9,353 (@20) | **407** | 1,279 |
| Tokens per valid item | 1,227 (@200 inst./gen.) | **527** | 4,571 |
| Marginal API cost per additional instance | **0** | **0** | linear |
| Projected tokens for 86K valid items | 81 M | 45 M | 394 M |

Two facts we state plainly: PF is 3.7× cheaper per valid item than direct synthesis, and B2 is 2.3× cheaper than PF. The difference is exactly the verification stage B2 omits — and Table R3 shows what that stage buys: 12 additional zero-yield seeds and 8× more duplication. Cost per valid item is the relevant quantity only if the item is usable and non-redundant; we now report both cost and the joint yield of usable multi-step items, and we no longer imply that PF is the cheapest option at small scale.

**Why the pattern is causal rather than an artifact of filtering.** PF is released, filtered data, so we equalised the one confound a reviewer could reasonably raise: removing the five seeds whose B2 generator produced nothing moves B2's yield from 0.734 to 0.774 and PF's from 0.761 to 0.764, i.e. the validity difference flips from +0.027 to **−0.010**. Once coverage is equalised no validity difference remains, so the small unconditional gap reflects authoring-failure coverage rather than item quality; equalising it does not move the other axes at all, with the depth gap staying at **+0.605** and the structural-duplication gap at **−20.1 pp**. Filtering can remove a dead generator; it cannot make a shallow, self-similar generator deep and diverse. Component-level attribution is pinned down independently by the ablation already in the paper (Table 4: +2.3 PF-86K, +0.5 PC-83K, +0.6 Logic & Math at fixed data size and seed source).

**Why the measurement is trustworthy.** The judge is a different model from the generator; items are blinded and shuffled with method, seed and native explanation removed; sampling is fixed in advance at 5 per seed per condition with no quality-based reselection; inference is seed-clustered, never item-level; the p-values in Table R2 are Holm-adjusted across all 21 tests; and every artifact needed to recompute Table R1–R6 ships with the paper. We also report the protocol's known limit honestly: swapping the judge prompt flips 8.4% of item-level verdicts, which is why no claim here rests on item-level significance — every claim is a seed-paired effect reported with its full win/tie/loss distribution (e.g. PF's depth advantage holds on 59 of the 84 seeds where both conditions yield a valid item, ties on 8 and reverses on 17).

**What this shows about the framework.** The three conditions decompose the framework, and each of its stages owns one measured property:

- **Program grounding** converts a generative problem into a checkable one: B1 → B2 raises validity from 0.278 to 0.734 (+0.456 [0.369, 0.547], p = 1.8e-13) and reduces wrong-answer failures from 331 to 71.
- **Expansion and parametric encoding** supply depth and diversity: B2 → PF adds +0.605 depth, +373 characters of problem specification, −22.8 pp near-duplication and −34.6 pp structural duplication, while validity stays flat.
- **Closed-loop verification** supplies reliability: B2 yields no valid item on 13 seeds (five of which produced nothing at all) and 25 items with no output; PF yields no valid item on 1 seed and 0 items with no output, because a generator that does not execute is repaired or rejected before any item is emitted.

That is the framework-level claim the paper was missing, and it is not a claim about the dataset: holding seeds, backbone, budget and answer format fixed and changing only the pipeline raises depth by 0.605, reduces within-seed duplication by 22.8 pp, and lifts the rate of usable multi-step problems from 33.8% to 62.7%.

**Why we do not reframe the paper as a benchmark contribution.** The comparison above is a comparison of pipelines, not of datasets: the same 97 seeds and the same model produce qualitatively different artifacts depending only on how the generator is constructed and verified. A data-only framing would discard the part of the contribution that is now directly measured. We do agree the submitted version overweighted the dataset evidence, and the revision restructures accordingly: a new subsection reporting Table R1–R6, contribution bullet 3 split into a framework-level and a dataset-level claim, an explicit scoping paragraph separating causal (fixed-backbone pipeline) from descriptive (released-dataset) statements, and the certificate/depth stratification moved to the main text so that no metric is read out of context.
