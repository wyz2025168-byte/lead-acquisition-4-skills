# 线索生客｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一位虚构创始人长期坚持先诊断再行动，并有真实经历支撑。请形成理念候选与一致性检查，理念型表达停在已批准的方向与价值判断边界。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C40-D01 → C40-D02 → C40-D03 → C40-D04 → C40-D05 → C40-D06 → C40-D07 → C40-D08 → C40-D09 → C40-D10` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：positioning_ref、lock_baseline_ref、conversion_brief_ref、core_idea、idea_direction、idea_extension_directions、idea_expression_rules、interpretation_trace、practice_evidence、consistency_filter、optional_slogan、formation_check、truth_status_by_field、approval_state、uncertainties、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
