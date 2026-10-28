# 盲审说明

只向审核者提供 audit_blind.jsonl 及空白标注表；audit_key.jsonl 保持私有。
原生解释另存 audit_native_explanations.private.jsonl，正确性／深度盲审时不提供，避免解释缺失泄露来源。
两位审核者应独立作答，提交前不互看标签；reviewer_1/reviewer_2 替换为稳定的匿名人员ID。
valid: 1=题意完整一致、可解且参考答案正确，0=不满足；无输出记0。必须填写 evidence。
多答案任务以题目声明的答案类型为准，不能一律要求单一解。
depth: 有效题的最短充分推理依赖链必要步骤数（非解释长度）；不能确定留空。
explainability: 第一轮正确性／深度盲审留空；另行原生解释审核时，有效且提供了解释才评分，0=错误，1=关键步骤缺失，2=部分可核查，3=主要步骤可核查，4=完整且正确；无解释留空，另计解释提供率。
error_type: missing_constraint/ambiguous/unsatisfiable/wrong_answer/rendering/other。
两位valid不同由第三人用reviewer=adjudicator填valid及证据；未裁决不进入主终点。
深度、解释评分为两位有效评分的均值，只报告可评估子集及覆盖率。
禁止根据方法或预期结论挑选审核对象。实际独立性无法由CSV自动证明，需保留审核流程记录。
