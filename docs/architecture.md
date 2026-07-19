# 架构

```text
$jw 统一入口（只路由）
  ├── C00  $jw-positioning   定位基座
  ├── C10  $jw-lock          线索锁客
  ├── C20  $jw-circle        线索圈客
  ├── C30  $jw-convert       线索成客
  ├── C40  $jw-grow          线索生客
  ├── C50  $jw-production    制作呈现
  └── C90  $jw-orchestrator  全案编排
```

课程主链是 `C00 → C10 → C20 → C30 → C40`。C50 是制作支撑能力，C90 只维护状态、依赖、失效传播与唯一下一步。

每个 Skill 都能独立安装。没有上游批准成果时，它必须追问最小缺口或返回部分结果，不能伪造上游事实。

