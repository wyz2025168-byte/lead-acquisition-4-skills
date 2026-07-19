# 全案编排器｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一个虚构项目的 C20 批准版本被新事实否定，C30 与 C50 仍依赖旧版本。请只做状态、失效传播和最早 owner 路由，不创建内容答案或代替批准。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C90-D01 → C90-D02 → C90-D03 → C90-D04 → C90-D05 → C90-D06 → C90-D07` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：current_gate、active_task、route_decision、selected_owner、unique_next_task、artifact_registry_snapshot、input_versions_and_hashes、dependency_state、stale_targets、earliest_return_owner、gate_result、validation_replay_state、origin_partition、exclusions、truth_status_by_field、approval_state、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
