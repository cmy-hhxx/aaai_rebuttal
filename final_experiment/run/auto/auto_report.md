# 自动模型初评（非人工复核）

已处理 1440/1440 题；模型判定 1414 题；执行未决 0 题；无输出槽位 26 题；待处理pending 0。

模型共识仅是正确性代理，不是真值；同一模型解题和评判存在相关偏差。单个生成端点不能支持跨所有模型的泛化结论。历史PF数据与新生成基线也不构成同模型、同预算的因果比较。
本报告不做比较显著性检验；组别均值为描述统计，人工独立复核以后补充。有效性代理将uncertain分别计0/1形成敏感性下/上值，unavailable两端均计0；这不是真实有效率的置信界。有pending的组不输出总体有效性范围。

**仅单模型初评：重复请求不是独立模型面板，结论强度更弱。**

| 组别 | 全部请求槽N | 模型判定 | 未决/无输出 | pending | valid/N 下代理 | (valid+uncertain+unknown)/N 上代理 | uncertain | 深度代理均值(题n) | 统一证书均值(题n) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 480 | 479 | 1 | 0 | 134/480 (0.279) | 135/480 (0.281) | 1 | 1.925 (134题) | 3.724 (134题) |
| framework | 480 | 455 | 25 | 0 | 352/480 (0.733) | 352/480 (0.733) | 0 | 2.341 (352题) | 3.315 (352题) |
| puzzleforge | 480 | 480 | 0 | 0 | 366/480 (0.762) | 369/480 (0.769) | 3 | 2.943 (366题) | 3.123 (365题) |

## 按seed配对比较

仅双方每seed各至少2个已处理槽（模型判定、执行未决或unavailable）进入比较；其他seed仍在覆盖分母。按seed宏平均，配对bootstrap 2000次、固定随机种子20261028。只描述已覆盖seed子集；95%统计区间不代表真值保证，也不作显著性断言。

lower−lower及upper−upper是相同敏感性设定的差；真正不确定项最不利分配下的差界为PF_lower−B_upper到PF_upper−B_lower，两种范围不能混用。

| PF减去基线 | 代理比较 | 配对seed覆盖 | 宏平均差 | 95%bootstrap区间 |
|---|---|---:|---:|---|
| PF − direct | lower_minus_lower | 97/97 | +0.484 | [+0.406, +0.561] |
| PF − direct | upper_minus_upper | 97/97 | +0.488 | [+0.410, +0.564] |
| PF − direct | difference_lower | 97/97 | +0.481 | [+0.402, +0.559] |
| PF − direct | difference_upper | 97/97 | +0.490 | [+0.413, +0.565] |
| PF − framework | lower_minus_lower | 97/97 | +0.027 | [-0.054, +0.109] |
| PF − framework | upper_minus_upper | 97/97 | +0.034 | [-0.047, +0.114] |
| PF − framework | difference_lower | 97/97 | +0.027 | [-0.054, +0.109] |
| PF − framework | difference_upper | 97/97 | +0.034 | [-0.047, +0.114] |

## 自动初评结论

本次自动初评在 97/97 个共同seed上，PF相对direct的有效性代理宏平均差，随uncertain最不利分配的点估计范围为[+0.481, +0.490]。
本次自动初评在 97/97 个共同seed上，PF相对framework的有效性代理宏平均差，随uncertain最不利分配的点估计范围为[+0.027, +0.034]。
以上数值限定于本次自动初评及覆盖子集，不能推断人审真值、全部质量维度或框架因果优势。pending不纳入结论，任何未测结果都不会被当作不合格题。

## 难度与标签代理

direct / panel_0 (gpt-5.6-luna)：avg@k=0.933，可独立一致判断全部k次的共识有效题 134/134；其余难度NA。

direct / reasoning_type_tags：标签熵 2.225 bits；分布 {'algebra': 20, 'arithmetic': 60, 'causal': 4, 'cipher': 3, 'combinatorial_search': 10, 'counting': 9, 'deduction': 113, 'other': 5, 'spatial': 9, 'temporal': 2}。

direct / constraint_type_tags：标签熵 3.041 bits；分布 {'adjacency': 10, 'all_different': 18, 'boolean': 17, 'cardinality': 15, 'equality': 73, 'graph': 5, 'implication': 10, 'inequality': 10, 'ordering': 15, 'other': 16, 'string': 20}。

direct / scenario：标签熵 2.245 bits；分布 {'abstract': 32, 'language': 24, 'numbers': 52, 'objects': 9, 'people': 4, 'spatial': 12, 'temporal': 1}。

direct：观测结构标签组合数 65。标签多样性是judge代理，不是语义嵌入或真实生成结构证明。


framework / panel_0 (gpt-5.6-luna)：avg@k=0.828，可独立一致判断全部k次的共识有效题 349/352；其余难度NA。

framework / reasoning_type_tags：标签熵 2.430 bits；分布 {'algebra': 46, 'arithmetic': 166, 'cipher': 58, 'combinatorial_search': 50, 'counting': 46, 'deduction': 294, 'spatial': 56, 'temporal': 7}。

framework / constraint_type_tags：标签熵 3.025 bits；分布 {'adjacency': 42, 'all_different': 45, 'boolean': 34, 'cardinality': 86, 'equality': 176, 'graph': 8, 'implication': 14, 'inequality': 30, 'ordering': 51, 'other': 25, 'string': 101}。

framework / scenario：标签熵 2.123 bits；分布 {'abstract': 47, 'language': 106, 'numbers': 123, 'objects': 8, 'people': 8, 'spatial': 60}。

framework：观测结构标签组合数 136。标签多样性是judge代理，不是语义嵌入或真实生成结构证明。


puzzleforge / panel_0 (gpt-5.6-luna)：avg@k=0.792，可独立一致判断全部k次的共识有效题 360/366；其余难度NA。

puzzleforge / reasoning_type_tags：标签熵 2.384 bits；分布 {'algebra': 63, 'arithmetic': 248, 'cipher': 30, 'combinatorial_search': 72, 'counting': 103, 'deduction': 365, 'other': 1, 'spatial': 55, 'temporal': 6}。

puzzleforge / constraint_type_tags：标签熵 3.140 bits；分布 {'adjacency': 47, 'all_different': 65, 'boolean': 60, 'cardinality': 189, 'equality': 235, 'graph': 17, 'implication': 56, 'inequality': 100, 'ordering': 126, 'other': 36, 'string': 81}。

puzzleforge / scenario：标签熵 2.324 bits；分布 {'abstract': 44, 'language': 94, 'numbers': 120, 'objects': 23, 'people': 12, 'spatial': 70, 'temporal': 3}。

puzzleforge：观测结构标签组合数 229。标签多样性是judge代理，不是语义嵌入或真实生成结构证明。

## 案例候选

自动标签只能提示支持／反驳假设的候选；以下完整题面、答案、证书和证据保存在 examples.jsonl。不能仅从这些案例认定框架普遍胜出。

- valid / direct / `0038aa98af8825d0fc43`：网格中唯一未揭示单元格为 (2,2)。相邻的数字 1 要求其邻域包含恰好一枚地雷；所有其他相邻单元格均为已揭示数字，因此不可能是雷，所以 (2,2) 在所有满足约束的方案中都必为雷。给定答案与此一致。

- valid / framework / `007cc0e4c80f53d67412`：The canonical grid is a valid complete assignment: every digit can point downward, and the consecutive blank-cell run below each digit has exactly the stated length. These vertical runs partition all X cells by column, so every X is covered and no two arrows intersect. The supplied certificate contains an incorrect uniqueness claim: for example, the digit at row 3, column 3 has blank cells both above and below, so its left/right/up directions are not all blocked as stated. This flaw does not invalidate the submitted assignment.

- invalid / puzzleforge / `00084fb3e1fa901c46d8`：使用给定权重[18,17,9]计算第一组 AOH：0×18+14×17+7×9=238，238 mod 26=4，而标准答案给出15。其余各组与标准答案一致；因此标准明文首字母应为 W（4−8 mod 26=22），不是 H。供应的尝试答案实际上正确，但与错误的canonical_answer不一致。

- invalid / puzzleforge / `00352c90f1d93361fd63`：按计划 BMBIB 顺序计算：B 保持输入 [0, 0, 0, 1, 1, 1]；M 在非掩码位置翻转，得到 [0, 0, 1, 0, 0, 0]；随后 B 保持不变；I 全部翻转，得到 [1, 1, 0, 1, 1, 1]；末级 B 保持不变。因此第一问应为 [1, 1, 0, 1, 1, 1]，而 canonical_answer 的第一部分错误地使用了 M 级后的中间结果。canonical_answer 的第二部分 [0] 也错误，因为无故障已经与观测一致，且故障集合 [0] 会改变最终结果。

- uncertain / direct / `19417585e6a923d26105`：The eight listed items are exactly the nodes satisfying the stated cousin relation, but the requirement to sort Chinese item names by “alphabetical order” is undefined. The canonical answer is not in standard pinyin lexicographic order, so it is unclear whether the canonical sequence is intended to enforce ordering or merely represent an unordered set.

- uncertain / puzzleforge / `5c34b533440d2296c902`：The canonical grid satisfies the numeric clues, snake ranges, four-neighbor path adjacencies, bridge adjacencies, row-8 sum 260, column-2 sum 100, and the stated A/B/C label restrictions. However, the checkerboard condition is ambiguous: the puzzle does not define whether the white parity of (row+column+number) is even or odd. The canonical grid makes this expression odd in every cell, so it is valid only if odd is designated as white. The supplied attempt also claims multiple candidates but provides no concrete alternative grid.

同seed配对候选（仅共识valid/invalid且每组至少2题，不含未确定项；仍需复核）：

- direct / supporting / seed `arrow_maze`：共识有效率差 +0.200，匿名记录 ['8b8e21a07aa59b379db2', '70ce953d3acdc6a52316', '1806562a4cf9813ef068', '0eba9e57937b158a51f6', 'f69a30a184ae6049e73f', '389892946f23cd4fa219', 'e97d709438fadb53c0e7', '7ed6473188788fa07758', '3c888db60f0d76b02ff8', '1ecd256e21cd7c757a07']。

- direct / similar / seed `buggy_tables`：共识有效率差 +0.000，匿名记录 ['e84830253b019f6084bf', '9c7d7b5c1ec30a0d56d5', 'afe49c71224577123075', '2dee91aff9602110a227', '3ff6fb4725fb3666254b', '28ac41fd28edda482854', 'a8ceee171b47bf1a4e21', '49d47ec7c40063994fe0', '9462245d0c9c2cbef5f2', '206a92d51d269a61227b']。

- direct / refuting / seed `numbrix`：共识有效率差 -0.250，匿名记录 ['16aa4ceed06e984a3eaf', 'abc6fff21f4ac2350539', '4df23d8bcbb12bf0cd3e', 'ef50cc8de611e3e9dea5', '68ecab9a74997784cfb9', 'b0bc0f6049c386b5ffe2', '32121596fcc066dcac8c', 'a115a6296009da0a0756', '10d6dc682ae118fc9642']。

- framework / refuting / seed `boolean_expressions`：共识有效率差 -0.200，匿名记录 ['eeaf99eb007b5b82ae8a', '77ef195309e3064e5a4e', '7501974f9e38c4a23a0e', '1d6d5871f4daae300432', '719d3c476d9b55af611a', '2f3ae8909f0c24113441', '1f77372567b002dcdb3d', '8d3f7102a0050f5a0328', '56ced14520a00f8f2bbe', '5188d645ef30329424b4']。

- framework / similar / seed `buggy_tables`：共识有效率差 +0.000，匿名记录 ['e84830253b019f6084bf', '9c7d7b5c1ec30a0d56d5', 'afe49c71224577123075', '2dee91aff9602110a227', '3ff6fb4725fb3666254b', '876470261093b55d938a', 'cc7d69f3b5bcbda96db7', 'ee3a8509739999379f8c', '2d6ff66a5b5f080d36bd', '2235e84148321e488afb']。

- framework / supporting / seed `cipher_10`：共识有效率差 +1.000，匿名记录 ['a142abacccb5bb750bb8', '99ff814446d9ed07bb9f', '73e3cd96c272df54e1a3', '84efbefb47849b0620a1', '34c5a8f4b45339798f1f', '4eb74dfccbd0b11fbff3', '18c995e4764d700a6d9c', '431af86535665573c9af', '710983d3c6f76ef72d18', '1b8c3ddc509379bebded']。
