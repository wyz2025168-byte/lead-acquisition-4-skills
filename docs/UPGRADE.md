# 从旧版升级

1. 安装 v2.0.0 后始终从 `$jw` 启动，不再调用旧 `jw-*`。
2. `$jw` 会用 `legacy-scan` 检测残留，但不会擅自删除。
3. 旧 `.jw-project` 先执行 `migrate`；脚本建立只读备份，只迁移事实、来源和历史审批。
4. 旧业务结论统一标为 `NEEDS_REQUALIFICATION`。
5. 确认 v2 项目可恢复后，再按宿主 Skill 管理方式清理旧 Skill。
