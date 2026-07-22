# v3 项目运行时

从当前 Skill 安装目录调用：

```text
python3 <JW_SKILL_DIR>/scripts/jw_project.py <command> <PROJECT_PATH> ...
```

先对写入命令运行 `--help`。模型不得手写 ID、版本、哈希、时间戳、审批有效性或 stale 字段。

## 用户可见能力检查

```text
doctor               检查版本、包哈希、七方法注册、旧 Skill 残留和运行环境
capabilities         显示五阶段、七方法、调用关系、输入输出和资格分类统计
```

## 项目命令

```text
init                 初始化 .jw-project v3
validate             校验文件、记录、依赖和哈希
status               恢复唯一当前状态
migrate              只读备份并迁移旧项目
set-objectives       登记30天目标与90天预测
set-stage            登记阶段、瓶颈和唯一下一步
add-source            登记来源
add-entity            登记人物事实与权限边界
add-claim             登记事实或假设
add-decision          登记方法、候选比较、影响和决定
add-approval          登记四种明确审批
add-experiment        登记可复现实验
register-artifact    登记真实成果、方法与依赖
add-content          登记内容计划
record-asset         关联实际拍摄/编辑素材
reconcile-portfolio  对账计划与实际内容组合
record-feedback      登记真实观察和纠正
invalidate           从上游根沿依赖图局部失效
can-publish          校验范围匹配的生产批准
handoff              生成唯一 HANDOFF_LATEST
export-feedback      导出不含原始资料的脱敏反馈包
```

## 项目状态

`.jw-project/` 保存 project-state、entities、claims、decisions、approvals、experiments、feedback、content-inventory、artifact-registry、source-registry、sources、artifacts、backups、exports 和唯一 HANDOFF。

高影响决定与成果强制包含：`business_stage`、`method_refs`、`evidence_refs`、`counterevidence`、`alternatives`（决定）、`selected_path`（决定）、`depends_on`、`upstream_impacts`、`downstream_impacts`、`horizon_30d`、`horizon_90d`、`approval_state`、`status`。

`method_refs` 只能使用注册表中的七个 method ID。Schema 完整不代表业务正确；反证失败仍须停止下传。

## 恢复、迁移与失效

- 新任务先 `validate` 再 `status`，不得凭聊天记忆恢复。
- v2 或更早项目迁移前用原子移动建立只读备份；只导入来源、已确认事实和历史审批记录。
- 旧业务决定、内容和成果不进入 v3 有效状态，统一视为 `NEEDS_REQUALIFICATION`。
- 上游事实或决定变化时运行 `invalidate`；依赖图中的后代 stale，无关成果保持不变。
- 计划内容与实拍资产分别登记，使用 `reconcile-portfolio` 对账。

## 审批与外部动作

`can-publish` 通过只表示存在范围匹配的 `PRODUCTION_APPROVED`；真实执行仍须具备宿主工具，且渠道、对象、动作、版本和期限全部匹配。不能执行时返回 `NOT_EXECUTED`，不得用计划冒充结果。

## 唯一下一步

`set-stage` 的下一步 JSON 只允许：owner、minimum_input、timebox、artifact、decision_threshold、stop_rule、expansion_condition。不得使用“若干、足量、适当、尽量”等不可复现词。
