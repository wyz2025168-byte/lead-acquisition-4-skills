# 定位基座｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一家虚构服务商正在诊断服务与代执行服务之间取舍；已有需求访谈、竞争替代和创始人经历记录，但最终方向尚未批准。请只依据这些离线事实生成方向候选、缺口与审批请求。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C00-D01 → C00-D02 → C00-D03 → C00-D04 → C00-D05` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：business_and_product_boundary、demand_direction_candidates、competition_mindshare、founder_fit_and_constraints、approved_direction、tradeoff_reasons、discarded_directions、truth_status_by_field、approval_state、uncertainties、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
