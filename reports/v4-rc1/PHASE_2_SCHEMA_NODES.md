# Phase 2 结果

- 改动文件：`skills/jw/schemas/`、`skills/jw/scripts/jw_project.py`、`skills/jw/references/business-node-map.md`、`skills/jw/references/outcome-contract.md`。
- 新增行为：实现 OutcomeContract、B0–O1 十二个原子节点、替代方案、最小信息请求、Approval v4、节点级失效和 v3→v4 迁移。
- 先失败的测试：缺少 `set_outcome`、`set_node`、`preflight` 和 `migrate --to 4`。
- 修复后测试：迁移幂等、原目录字节哈希保持、领先事件语义降级、审批待重确认、单节点局部失效和回滚全部通过。
- 仍然失败：无确定性失败。
- 业务规则如何进入运行时：节点状态、依赖、证据、反证、替代方案、审批引用和 30/90 天影响均为受 Schema 约束的记录。
- 对 v3 兼容影响：旧来源与已确认事实迁移；旧业务结论不自动批准；旧审批无原话时转为 `NEEDS_RECONFIRMATION`。
- 风险与下一步：迁移不会推断旧成果依赖，无法确认的成果保持待重新资格审查。
