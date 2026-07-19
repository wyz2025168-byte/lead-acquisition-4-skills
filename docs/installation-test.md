# 隔离安装测试

## 环境

- 日期：2026-07-19
- skills CLI：`1.5.19`
- 来源：脱敏后的本地发行仓库
- HOME：独立临时目录，不使用用户真实 HOME
- 安装命令语义：`skills add <local-repo> -g --all`
- 调用方式：`pnpm dlx skills@1.5.19`（本机未预装 `npx`，执行的是同一个 `skills` CLI）

## 结果

1. 安装器成功验证本地路径。
2. 自动发现 8 个 Skill：`jw` 与七个 `jw-*` 课程能力。
3. 8 / 8 均安装到通用 `~/.agents/skills/` 入口。
4. CLI 同时为支持的 Agent 创建派生入口；Eve 与 PromptScript 明确不支持 global 安装，因此各跳过 8 项。这是宿主限制，不是包结构失败。
5. 安装后的 8 个 `scripts/validate-bundle.py` 全部 PASS。
6. 用户真实 HOME 中原有 Skill 链接保持不变。
7. 安装后的七个公开运行合同与私有冻结合同结构对比通过：决策、失败码、审批点和失效规则数量保持一致。
8. 公开元数据脱敏检查通过，未发现私有课程路径、源哈希、内部审批/RCA 编号或黄金题/Rubric 绑定。

## 结论

脱敏发行仓库已通过“一条 skills CLI 命令发现全部 Skill、安装到隔离 HOME、安装后逐包校验”的本地可安装性测试。

远程 GitHub 安装结果将在公开仓库上传完成后写入本文件。
