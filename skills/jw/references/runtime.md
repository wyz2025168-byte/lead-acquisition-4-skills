# 项目运行时

## 脚本

从当前 Skill 安装目录调用：

```text
python3 <JW_SKILL_DIR>/scripts/jw_project.py <command> <PROJECT_PATH> ...
```

先对写入命令运行 `--help`。模型不得手写 ID、版本、哈希、时间戳、审批有效性或 stale 字段。

## 常用命令

```text
init                 初始化 .jw-project
validate             校验文件、记录、依赖和哈希
status               恢复唯一当前状态
legacy-scan          检测旧 jw-* Skill，不删除
set-objectives       登记30天目标与90天预测
set-stage            登记阶段、瓶颈和唯一下一步
add-claim            登记事实或假设
add-decision         登记候选比较和决定
add-approval         登记四种明确审批
add-experiment       登记可复现实验
register-artifact    登记真实成果及依赖
add-content          登记内容计划
record-asset         关联实际拍摄/编辑素材
reconcile-portfolio  对账计划与实际内容组合
record-feedback      登记真实观察和纠正
invalidate           从上游根沿依赖图局部失效
can-publish          校验范围匹配的生产批准
migrate              备份并迁移旧项目
handoff              生成唯一 HANDOFF_LATEST
export-feedback      导出不含原始资料的脱敏反馈包
```

## 项目文件

`.jw-project/` 包含 project-state、entities、claims、decisions、approvals、experiments、feedback、content-inventory、artifact-registry、source-registry、sources、artifacts、backups、exports 和唯一 HANDOFF。

## 状态规则

- 业务阶段只有 `POSITIONING / CONTENT / PRODUCTION / PORTFOLIO / OPERATIONS`。
- 新任务先 `validate` 再 `status`；损坏时停止业务推进。
- 上游判断改变时使用 `invalidate`，不得手写 stale。
- 旧项目迁移只保留事实、来源和历史审批记录；旧业务结论统一 `NEEDS_REQUALIFICATION`，不得自动成为 v2.0.0 有效结论。
- 内容计划与实际素材分别登记，使用 `reconcile-portfolio` 对账。
- `can-publish` 通过只代表审批范围匹配；真实执行仍需要宿主工具并必须记录结果。

## 唯一下一步

`set-stage` 的下一步 JSON 必须包含：owner、minimum_input、timebox、artifact、decision_threshold、stop_rule、expansion_condition。不得使用“若干、足量、适当、尽量”等不可复现词代替项目参数。
