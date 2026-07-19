# 线索圈客｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一个虚构项目已有批准的人群与买单前阶段；现有开头面向客户，正文却滑向同行术语。请检查四圈是否始终对同一人，并输出修复后的候选 Brief。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C20-D01 → C20-D02 → C20-D03 → C20-D04 → C20-D05` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：lock_baseline_ref、same_target_audience_and_stage、opening_circle、visual_circle、content_circle、viewpoint_circle、same_person_continuity、midstream_switch_risks、circle_visual_brief、truth_status_by_field、approval_state、uncertainties、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
