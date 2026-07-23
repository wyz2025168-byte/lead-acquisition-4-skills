# 线索获客 4.0 v4.0.0-rc.1

> Semantic Rebuild Candidate：保留 v3 控制能力，新增从真实价值交换倒推的业务推理内核。确定性门禁与独立自然盲评已通过，可进入受控 Field Validation；当前尚未 commit、push 或发布。

## 安装与启动

公开发布后仍使用：

```bash
npx -y skills add wyz2025168-byte/lead-acquisition-4-skills -g --all
```

启动：`使用 $jw，初始化并接管这个项目。`

## v4 解决什么

v4 不再把“文件完整”当成“业务正确”。内部以 B0–O1 推进：结果合同 → 产品边界 → 交易角色 → 触发阶段 → 线上可转化 → W1–W6 → 内容 → 脚本 → 生产 → 组合运营。

- 咨询、预约、到店、检查和方案沟通只能是领先事件，不能替代真实正价或等价价值交换。
- 本地人群不能只靠泛行业研究排序；线上可触达、识别、影响和归因必须分别判断。
- 人物路线必须通过去头衔和客户侧障碍测试，内部职责不能直接成为购买理由。
- 信息请求必须说明它会改变哪个决定，并限制为最小样本。
- `validate` 默认同时检查工程结构和业务不变量；业务 FAIL 时整体 FAIL。
- 五阶段仍面向用户，七个课程方法仍按需调用；课程原理不能覆盖项目事实。

## 关键命令

`doctor`、`capabilities`、`set-outcome`、`set-node`、`add-alternative`、`add-information-request`、`preflight`、`validate`、`status`、`migrate --to 4`、`rollback-migration`、`handoff`。

审批分为 `DIRECTION / EXPERIMENT / ARTIFACT / PUBLISH`。没有范围匹配的 `PUBLISH` 和可用工具，不会真实发布、投流、外发或联系客户。

## 状态边界

本候选已通过19项确定性测试、10项脱敏回放和21次独立自然运行盲评（6/7场景稳定通过、硬失败0）。真实获客与成交效果仍需现场验证；不保证流量、咨询或成交。升级见 [UPGRADE](docs/UPGRADE.md)，测试见 [FIELD_TESTING](docs/FIELD_TESTING.md)。

许可证：[Restricted Evaluation License 1.0](LICENSE.md)。
