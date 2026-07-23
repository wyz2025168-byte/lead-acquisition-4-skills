# v4 项目运行时

从当前 Skill 安装目录调用：

```text
python3 <JW_SKILL_DIR>/scripts/jw_project.py <command> <PROJECT_PATH> ...
```

模型不得手写 ID、版本、哈希、时间戳、审批有效性或 stale 字段。

## 核心命令

```text
doctor                         检查版本、包哈希、方法、旧残留和环境
capabilities                   显示五阶段、七方法和 B0–O1
init                           初始化 .jw-project v4
set-outcome --json             设置 OutcomeContract
set-node --node B4 --json      设置原子节点
add-alternative --json         登记结构化候选
add-information-request --json 登记最小信息请求
preflight --target C1          列依赖、阻断、警告和最小修复
validate                       默认同时校验结构和业务不变量
validate --structural-only     仅迁移/维修，不得用于发行验收
status                         恢复唯一状态与节点表
migrate --to 4                只读备份并迁移 v3
rollback-migration            恢复旧项目并隔离当前 v4，不删除数据
handoff                        生成业务型 HANDOFF
```

初始化示例：

```text
python3 <JW_SKILL_DIR>/scripts/jw_project.py init <PROJECT_PATH> --project-id <稳定项目ID> --name <项目名>
```

claim 的 `truth_status` 只能是 `CONFIRMED_FACT / SUPPORTED_HYPOTHESIS / UNVERIFIED / DISPUTED / REJECTED`。命令字段不确定时先运行 `<command> --help`；不得搜索或读取 Python 实现源码来猜 Schema。

现有来源、实体、claim、decision、experiment、artifact、content、asset、portfolio、feedback、invalidate、can-publish 和 export-feedback 命令继续保留。

## v4 状态

`.jw-project/` 新增 `outcome-contracts.json`、`business-nodes.json`、`alternatives.json`、`information-requests.json` 和 `migration-report.json`。B0–O1 使用七态；五阶段仅供用户导航。

所有高影响决定保存节点、结构化候选、证据范围、反证、拒绝理由、推翻条件、30/90天、依赖与审批。审批类型为 `DIRECTION / EXPERIMENT / ARTIFACT / PUBLISH`，并保存原话、解释范围、明确排除和来源。

## 恢复、迁移与失效

- 新任务先 `validate` 再 `status`，不得凭聊天记忆恢复。
- v3 迁移先原子移动为只读备份；重复迁移幂等。
- 回滚会恢复迁移前项目，并把当前 v4 状态移入隔离快照；两边均保留。
- 旧事实和来源可保留；旧决定降为待复核；缺原话审批转 `NEEDS_RECONFIRMATION`。
- 旧咨询、预约或到店“成功”只迁为领先事件，不自动形成 v4 success_event。
- 节点变化只失效真正依赖的节点、审批和成果；来源与无关事实保留。

## 外部动作

`can-publish` 通过只表示存在范围匹配的 `PUBLISH`；真实执行仍需宿主工具，且渠道、对象、动作、版本和期限全部匹配。否则返回 `NOT_EXECUTED`。

## 唯一下一步

下一步字段固定为 owner、minimum_input、timebox、artifact、decision_threshold、stop_rule、expansion_condition。禁止“若干、足量、适当、尽量”；信息请求必须说明会改变哪个决定。
