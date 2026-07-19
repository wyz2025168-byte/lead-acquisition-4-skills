# 线索成客｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一个虚构账号已经圈到批准人群，但内容只获得认可，没有形成可感知购买理由。请基于真实身份与交付事实设计候选内容角色和消费旅程，不虚构能力。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C30-D01 → C30-D02 → C30-D03 → C30-D04 → C30-D05 → C30-D06 → C30-D07` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：lock_baseline_ref、circle_brief_ref、product_fact_ref、audience_and_stage、professional_recognition_gap、trust_mechanism、factual_support、immediate_purchase_reason、customer_decision_pattern、content_role_plan、idea_role_pointer、consumer_journey、conversion_presentation_brief、truth_status_by_field、approval_state、uncertainties、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
