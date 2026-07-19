# 线索获客 4.0 Agent Skills

把“定位 → 锁客 → 圈客 → 成客 → 理念 → 制作 → 编排”整理成七个可独立调用、可组合的 Agent Skill，并提供一个统一入口 `$jw`。课程真源与完整追溯保留在私有编译项目中，公开包只提供经过脱敏的运行能力。

适用于 Codex、Claude Code、Cursor、Trae Solo，以及其他支持 Agent Skills 的工具。

## 一句话安装

所有 Skill 可以用同一条命令安装或更新：

```bash
npx -y skills add wyz2025168-byte/lead-acquisition-4-skills -g --all
```

当前本机发行候选可直接测试：

```bash
npx -y skills add "/absolute/path/to/lead-acquisition-4-skills" -g --all
```

安装后对 Agent 说：

```text
使用 $jw，帮我判断现在应该先测试哪个能力。
```

也可以直接点名：

```text
使用 $jw-positioning，先帮我诊断定位。
```

## 8 个安装入口

| Skill | 角色 | 作用 |
|---|---|---|
| `$jw` | 工程路由入口 | 根据问题选择下方唯一能力，不创建课程规则 |
| `$jw-positioning` | C00 定位基座 | 诊断需求方向、竞争心智与创始人适配 |
| `$jw-lock` | C10 线索锁客 | 锁定可成交人群、熟悉人群与买单前阶段 |
| `$jw-circle` | C20 线索圈客 | 保证开头、画面、内容、观点始终面向同一批人 |
| `$jw-convert` | C30 线索成客 | 组织信任、购买理由、内容角色与消费旅程 |
| `$jw-grow` | C40 线索生客 | 提炼长期理念、表达方向与一致性规则 |
| `$jw-production` | C50 制作呈现 | 把策略转成可重复的短视频与直播呈现 Brief |
| `$jw-orchestrator` | C90 全案编排 | 维护版本、依赖、失效传播和唯一下一步 |

## 第一次怎么用

```text
使用 $jw-positioning。

我的产品/服务：[填写]
客户需求证据：[填写]
客户现在会选择的替代方案：[填写]
我的身份、经历、交付和资源条件：[填写]

请区分 confirmed、hypothesis 和 unknown；信息不足时只问最少问题。
```

## 这个发行包包含什么

每个课程能力都包含：

- `SKILL.md`：执行工作流与能力边界
- `references/course-rules.md`：编译后的课程规则
- `references/source-map.json`：不含私有路径和哈希的来源边界证明
- `schemas/`：输入、输出、成果约束与脱敏后的运行合同
- `examples/`：不泄露黄金题答案的中性示例
- `tests/`：不含题目、答案、Rubric、私有 ID 或哈希的评测通过证明
- `BUNDLE_MANIFEST.json`：该 Skill 的文件哈希
- `scripts/validate-bundle.py`：安装后完整性校验

## 不包含什么

公开安装包不包含：

- 14 份原始课程 DOCX/PDF
- 课程文件名、来源编号、内部路径、源文件哈希与逐条证据行号
- 内部审批记录、RCA、外审包、私有合同路径和过程报告
- 黄金题、expected、Rubric、评分答案、测试 ID 和绑定哈希
- 任何真实客户项目、真实业务数据或发布内容
- 任何本机绝对路径依赖

原始课程文件仍保留在私有编译项目中。公开包只携带经过冻结、评测和边界处理的运行时能力。

## 公开验证摘要

- 七个课程能力已在私有评测环境完成双次独立评测，汇总结果 70 / 70 通过；题目、答案和评分细则不公开
- 接口、主链和端到端课程案例回放均已通过
- 公开包额外执行 8 / 8 Skill 完整性检查和隔离安装验证
- G7 真实项目影子运行不包含在本发行包中

详细证据见 [发行证据说明](docs/release-evidence.md)。

隔离安装结果见 [安装测试报告](docs/installation-test.md)：skills CLI `1.5.19` 成功发现并安装 8 / 8 Skill，安装后逐包完整性校验 8 / 8 PASS。

## 本地验证与构建

```bash
python3 tools/validate-package.py
python3 tools/build-release.py
```

构建结果：

- `dist/lead-acquisition-4-skills-v1.0.0.zip`：完整仓库发行包
- `dist/skills/*.zip`：8 个可单独上传的 Skill ZIP
- `dist/SHA256SUMS.txt`：发行文件哈希

## 更新

重新运行安装命令即可更新：

```bash
npx -y skills add wyz2025168-byte/lead-acquisition-4-skills -g --all
```

长期维护只改本仓库 `skills/` 真源，再重新构建即可。

## 发布状态

当前是 `v1.0.0-rc1` 公开测试版，发布于 `wyz2025168-byte/lead-acquisition-4-skills`。仓库采用 [Restricted Evaluation License 1.0](LICENSE.md)：允许个人学习、非商业测试和组织内部评估，禁止未经书面许可的商业化、再分发与修改发布。

发布决策与边界见 [GitHub 发布记录](docs/publication-checklist.md)。
