# Source of Truth

## 公开运行时真源

`skills/` 是本发行仓库唯一需要长期维护的运行时真源。

- 课程能力：`jw-positioning`、`jw-lock`、`jw-circle`、`jw-convert`、`jw-grow`、`jw-production`、`jw-orchestrator`
- 工程入口：`jw`

## 私有编译基线

本仓库的七个课程能力来自《线索获客4.0》已冻结的 v1 私有编译基线，当前统一状态为 `PROVISIONAL_STRUCTURAL_VERIFIED`。历史评测只保留为结构单元测试，不再表述为真实业务能力验证。完整 Manifest、源文件哈希、审批记录和逐决策追溯只保留在私有项目中，不随公开包分发。

v2 在独立私有工作区开发。它通过真实 G4–G8 之前，不得复制到本仓库的 `skills/` 真源，也不得发布 `v2.0.0`。

## 发行层允许的修改

相对私有 G3 Skill，本仓库只允许增加或修改：

- 可移植运行说明
- 本地完整性校验脚本和 Manifest
- `standalone_manual` 运行边界
- 安装、更新、发行与隐私说明
- 不改变运行语义的公开脱敏元数据
- 不创建课程规则的统一路由入口

脱敏只删除私有路径、哈希、题库/Rubric 绑定和内部追溯编号；`references/course-rules.md` 的规则语义、核心决策流程、能力 owner 和业务判断不得因发行便利被改写。
