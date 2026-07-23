# Phase 4 结果

- 改动文件：`skills/jw/scripts/jw_project.py`、`business-invariants.json`、`critic-and-safety.md`、`runtime.md`、`failure-catalog.md`。
- 新增行为：默认 `validate` 同时检查结构和业务；新增 `preflight`、可解释错误、审批溯源、局部失效和业务型 HANDOFF。
- 先失败的测试：结构合法但把领先事件当成交、内部职责当购买理由、未锁人先做内容等反例可穿透。
- 修复后测试：R01–R15 全部通过；每个阻断返回记录、违反关系、原因和最小修复。
- 仍然失败：无确定性失败。
- 业务规则如何进入运行时：业务不变量以注册表和运行时代码双重实现，`--structural-only` 只保留给维修/迁移且不进入发行命令。
- 对 v3 兼容影响：旧对象可读但不自动变成 v4 业务批准；HANDOFF 重新展示结果合同、节点、反证、已否路径和唯一下一步。
- 风险与下一步：模型可能在自然对话中不调用正确命令，必须用隔离模型题验证。
