# Rebuttal - Response to Reviewer Comment 4

> **Reviewer comment**
>
> 4. The experiments primarily demonstrate the usefulness of PF-86K rather than the effectiveness of PuzzleForge as a framework.
>
> Much of the experimental section evaluates the difficulty of PF-86K and the downstream improvements. These results support PF-86K as a useful dataset, but provide less evidence that PuzzleForge is a superior data-generation framework.
>
> Important framework-level baselines are missing, such as direct LLM-based instance synthesis and direct LLM generation of executable generators without the proposed multi-stage decomposition. Otherwise, the paper may be more appropriately framed primarily as a benchmark/data contribution rather than a methodological framework contribution.

## Response

We ran both baselines the comment names: direct instance synthesis (B1) and one-pass synthesis of a reusable generator with no multi-stage decomposition (B2), against the full pipeline (PF), on 97 shared seeds, blind-judging 1,440 items (480 per condition).

**Design.** All three conditions use GPT-5.2. PF is the paper's released test split: a 2% random holdout per generator, after the pipeline's own deduplication and generator filtering; the holdout itself is not quality-selected. B1 and B2 share model, decoding and a 20-item quota. B2 gets three execution-debug attempts with real errors, but no expansion agent, DSL, semantic verification or solve-based filtering, which makes it the stronger baseline. The judge sees only the problem, a canonical answer and anonymous certificates; method and seed are stripped.

**Table T1 - what each pipeline yields per requested slot** (480 slots per condition, blind judging; `tokens per valid item` at 20 instances/unit)

```
+-------------------------------+-------------+-------------+-------------+
|                               |     PF      |     B2      |     B1      |
+-------------------------------+-------------+-------------+-------------+
| valid items (of 480 slots)    | 366 (76.3%) | 352 (73.3%) | 134 (27.9%) |
| valid, >=3 dependent steps    | 301 (62.7%) | 162 (33.8%) |  28 (5.8%)  |
| reasoning depth, mean (0-4)   |    2.94     |    2.34     |    1.93     |
| median problem length (chars) |     692     |     321     |     297     |
| near-duplicate pairs @0.8     |    3.0%     |    24.9%    |    6.2%     |
| generators represented        |     284     |     97      |     97      |
| tokens per valid item         |   12,267    |     527     |    4,571    |
+-------------------------------+-------------+-------------+-------------+
```

*Percentages per slot (denominator 480); near-dup is over the 1,284 matched items per condition, not the 480 judged slots. Paired differences are seed-macro; inference is seed-paired (Wilcoxon, Holm across 21 tests, 2,000 seed bootstrap).*

**Against B1**, PF is far better on validity (+0.484 [+0.406, +0.556], p = 5.0e-14) and depth (+0.844). B1's failure is silent: 71.7% of items are invalid, yet only one has no output, and 331 of the 344 invalid items carry a wrong canonical answer. Execution grounding is the decisive factor, and B1 is not the strong baseline.

**Against B2**, validity is a tie: generator-level 0.775 vs 0.774; seed-level +0.027 [-0.054, +0.114], which becomes -0.010 when B2's five zero-output seeds are dropped. PF's advantage is yield: 62.7% vs 33.8% of slots produce a valid >=3-step item (1.86x; unit-matched 63.8% [56.6, 70.5] vs 33.8%).

Because PF items are also about twice as long (median 692 vs 321 chars), we tested the length confound directly rather than relying on one model. The raw depth gap is +0.602; OLS with log length gives +0.418, while strict matching is more conservative: nearest length (caliper 0.5) gives +0.439 [+0.150, +0.764]; coarsened exact matching on seed x length quintile gives +0.207 [-0.020, +0.443], and the top length quintile is essentially flat (-0.14). Single-subquestion items, which rule out "PF just bundles sub-questions", give +0.541 [+0.353, +0.827] raw and +0.548 [+0.120, +0.900] length-matched. **We therefore use depth as supporting evidence and anchor the main claim on the >=3-step yield:** +24.6 pp [+11.6, +35.9] after standardising B2 to PF's length distribution, and +15.8 pp [-1.2, +33.7] under strict nearest-length matching. The direction is stable in every specification; the strict matched estimate is smaller because the length overlap is thin, but it remains positive.

**Diversity.** Unit-matched (PF generator, B2/B1 seed) near-duplicate @0.8 is 13.2% vs 24.9%; identical constraint-tag sets 30.2% vs 53.1%; reasoning-tag sets 46.1% vs 56.8%. PF's seed-level 3.0% is partly a mixing effect (five items from three generators), which we correct. Against B1, PF has more near-duplicates (13.2% vs 6.2%) but fewer identical tag sets; B1's items are also shorter.

**Cost.** At the paper's 200-instance scale, PF is 1,227 tokens per valid item vs 50 for B2 and 4,571 for B1; at 20 instances, 12,267 vs 527 and 4,571. PF/B2 is ~23-25x at either scale, and PF's spec cost is 0.34-0.55M tokens per seed vs B2's 7.7k (45-70x). Cost is the trade-off: PF's extra budget buys >=3-step yield and structural diversity. We report it explicitly rather than claim a cost advantage; the earlier draft compared PF at 200 instances/generator with B2 at 20/seed, and the corrected table puts both on the same basis.

**Judge reliability.** On a 560-item cross-family subsample (both models see the same three solver attempts; one verdict per model), exact verdict agreement is 83.4% (Cohen's kappa 0.67). The two families differ in strictness: PF's invalid rate is 30.9% under `gpt-5.6-luna` but 12.6% under `gemini-3.1-pro-preview`, and the PF-B2 validity difference flips sign (luna 0.686 vs 0.730; gemini 0.863 vs 0.789). B1 is 25.5% vs 27.5% valid, i.e. 72-74% invalid under both. The PF-B2 validity difference is therefore within judge noise; the B1 gap is not. The depth gap is +0.729 (luna) and +0.536 (gemini) on items both call valid.

**What the 23.1% consists of.** The judge marks 111/480 (23.1%) of PF's released test items invalid, 89 for a wrong canonical answer. Two real items show why this figure needs care. In `PF / operation_21/08`, the double integral of a separable trigonometric polynomial, the released answer is `[[0.133046]]` while an independent evaluation gives `[[-0.133046]]`: a sign error, a genuinely invalid item. In `PF / number_wall/14`, a compound-interest problem (2433 at 3% quarterly for 3 years, then +3723 at 6% quarterly for 4 years), the released answer is `7946.95` while the computation gives `7946.9444`, which rounds to `7946.94`: a 0.01 rounding difference, cosmetic rather than a broken puzzle. Both count as invalid, so 23.1% is an upper-end proxy that mixes substantive and cosmetic errors. The cross-family panel shows the same sensitivity: PF's invalid rate is 30.9% under luna and 12.6% under gemini, while B1 is 72-74% under both. The revision will report the two categories separately and correct the released labels.

**Framing.** We agree the framing should be explicit, and the added comparisons let us state it precisely. The framework's contribution is the yield of >=3-step items and structural diversity per seed; the trade-off is ~25x generation tokens, with validity on par with the strongest one-pass baseline. The revision will present this as a framework-level contribution alongside the dataset contribution, add the generator-level and length-matched tables, and rewrite the abstract and introduction to match. This is a more precise claim than an unqualified "superior framework".

Prompts, generators, traces, blind keys and the per-request token ledger are released with the paper and the revision.
