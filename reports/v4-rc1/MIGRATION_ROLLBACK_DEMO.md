# v3→v4 迁移与回滚演示

## 迁移

```text
python3 skills/jw/scripts/jw_project.py migrate <项目目录> --to 4
```

运行时把原 `.jw-project` 原子移动为带 UTC 时间戳的只读备份，再建立 v4。只导入来源与已确认事实；旧业务结论降为 `NEEDS_REQUALIFICATION`，旧审批缺原话时降为 `NEEDS_RECONFIRMATION`，旧领先事件不再冒充成交。

重复执行迁移返回 `already_v4`，不重复建备份、不改变状态哈希。

## 回滚

```text
python3 skills/jw/scripts/jw_project.py rollback-migration <项目目录>
```

运行时把当前 v4 目录整体移动到带 UTC 时间戳的隔离快照，再把迁移前备份恢复为 `.jw-project`。如果恢复动作失败，v4 目录会自动移回原位。该命令不删除任何一边。

## 自动验证

- 迁移前后只读备份的内容树 SHA-256 一致。
- 两次迁移后的 v4 状态哈希一致。
- 回滚后的 v3 内容树 SHA-256 与迁移前一致。
- v4 隔离快照仍存在。
