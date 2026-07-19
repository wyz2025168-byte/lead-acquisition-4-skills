# 线索锁客｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一个虚构的正价诊断服务已有一笔可追溯交易；创始人熟悉那些尝试过多种方案却无法排序的项目负责人。请判断四锁是否指向同一批人，并在需要时请求人群与阶段审批。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C10-D01 → C10-D02 → C10-D03 → C10-D04 → C10-D05 → C10-D06 → C10-D07` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：positioning_ref、product_anchor、purchasable_audience、founder_familiar_audience、pre_purchase_stage、pre_purchase_topics、four_lock_intersection、excluded_audiences、transaction_validation、truth_status_by_field、approval_state、uncertainties、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
