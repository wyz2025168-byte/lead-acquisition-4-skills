# 隔离安装测试

## 本地发行候选测试

- 日期：2026-07-19
- skills CLI：`1.5.19`
- 来源：脱敏后的本地发行仓库
- HOME：独立临时目录，不使用用户真实 HOME
- 安装命令语义：`skills add <local-repo> -g --all`
- 调用方式：`pnpm dlx skills@1.5.19`（本机未预装 `npx`，执行的是同一个 `skills` CLI）

### 结果

1. 安装器成功验证本地路径。
2. 自动发现 8 个 Skill：`jw` 与七个 `jw-*` 课程能力。
3. 8 / 8 均安装到通用 `~/.agents/skills/` 入口。
4. CLI 同时为支持的 Agent 创建派生入口；Eve 与 PromptScript 明确不支持 global 安装，因此各跳过 8 项。这是宿主限制，不是包结构失败。
5. 安装后的 8 个 `scripts/validate-bundle.py` 全部 PASS。
6. 用户真实 HOME 中原有 Skill 链接保持不变。
7. 安装后的七个公开运行合同与私有冻结合同结构对比通过：决策、失败码、审批点和失效规则数量保持一致。
8. 公开元数据脱敏检查通过，未发现私有课程路径、源哈希、内部审批/RCA 编号或黄金题/Rubric 绑定。

## 公开 GitHub 远程安装测试

- 日期：2026-07-19
- 公开来源：`https://github.com/wyz2025168-byte/lead-acquisition-4-skills.git`
- 测试入口：`wyz2025168-byte/lead-acquisition-4-skills`
- HOME：`/private/tmp/lead-acquisition-remote-sanitized-20260719`，不使用用户真实 HOME
- 实际测试命令：`pnpm dlx skills@1.5.19 add wyz2025168-byte/lead-acquisition-4-skills -g --all`
- 对外等价安装命令：`npx -y skills add wyz2025168-byte/lead-acquisition-4-skills -g --all`

### 结果

1. CLI 从公开 GitHub 地址成功克隆仓库。
2. 自动发现 8 个 Skill。
3. 8 / 8 均安装到隔离 HOME 的 `~/.agents/skills/`。
4. 安装后的 8 个 `scripts/validate-bundle.py` 全部 PASS。
5. Eve 与 PromptScript 不支持 global 安装，因此各跳过 8 项；这是宿主限制，不影响 Codex、Claude Code 等受支持入口。
6. 用户真实 HOME 中原有 Skill 保持不变。

## 结论

脱敏发行仓库已经同时通过本地发行候选安装测试和公开 GitHub 远程安装测试：均能用一条 skills CLI 命令发现全部 8 个 Skill、安装到隔离 HOME，并在安装后完成 8 / 8 逐包校验。
