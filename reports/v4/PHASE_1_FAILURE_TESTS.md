# Phase 1 结果

- 改动文件：`tests/test_business_invariants.py`、`tests/test_minimum_information.py`、`tests/test_approval_provenance.py`、`tests/test_node_dependencies.py`、`tests/test_v3_to_v4_migration.py`。
- 新增行为：把已知业务错误转成 R01–R15 可重复反例，并为合法场景保留正向测试。
- 先失败的测试：v3 基线下首次运行 15 项全部报错；直接原因是不存在 OutcomeContract、业务节点、preflight、最小信息、审批溯源和 v4 迁移接口，符合预期业务能力缺口，不是夹具损坏。
- 修复后测试：18/18 PASS，其中 17 项覆盖 R01–R15 与依赖/审批，1 项覆盖非破坏式回滚。
- 仍然失败：无确定性回归失败；独立模型自然运行不属于本阶段。
- 业务规则如何进入运行时：每个反例绑定固定错误码、阻断条件、最小修复和合法反例。
- 对 v3 兼容影响：测试只读取合成 v3 夹具；历史 tag、commit 和包不变。
- 风险与下一步：自然语言模型是否稳定遵守这些门禁仍需隔离模型运行验证。
