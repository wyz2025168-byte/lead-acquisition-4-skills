# 制作呈现｜中性离线调用示例

> fixture_origin=`AI_ENGINEERING`。该示例独立于黄金题，只演示调用边界，不提供评测答案。

## 请求

一个虚构咨询项目已有批准的画面圈、内容角色和创始人条件。请选择简单可重复的场景与呈现方式；把具体设备参数标成使用时复核项，不反向修改策略。

## 执行要求

- 只把明确提供的内容标成离线夹具事实；缺失字段保持 unknown 并最小追问。
- 按 `C50-D01 → C50-D02 → C50-D03 → C50-D04 → C50-D05 → C50-D06 → C50-D07 → C50-D08` 的冻结顺序执行。
- 命中失败、审批或漂移时按 `schemas/contract-binding.json` 路由，不替用户批准。
- 正常完成时生成合同字段全集：circle_visual_ref、conversion_presentation_ref、target_audience_ref、content_role、audience_scene_and_image_intent、presentation_form、repeatability_plan、short_video_execution、live_image_and_environment、fact_and_claim_constraints、time_sensitive_references、current_verification_required、implementation_limits、uncertainties、truth_status_by_field、approval_state、provenance、version、payload_hash。
- 不加载黄金题正文，不提前读取评分答案，不发布任何业务内容。
