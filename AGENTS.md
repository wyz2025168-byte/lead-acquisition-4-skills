# 线索获客 4.0 Skills 仓库规则

## 真源

- `skills/` 是公开运行时唯一真源。
- 七个 `jw-*` 是课程能力；`jw` 只是 `AI_ENGINEERING` 路由入口，不得创建课程规则。
- 每个 Skill 必须自包含，不得依赖安装者本机的原始编译项目。

## 永久边界

- 不把原始课程 DOCX/PDF、内部审批、RCA、黄金题 expected、评分答案或真实客户数据加入公开发行包。
- 不在公开元数据中保留课程文件名、私有目录、源文件哈希、内部审批号、题库/Rubric ID 或逐条证据行号。
- `source-map.json` 只提供公开来源边界证明，不提供私有工程追溯。
- 不创建跨行业统一阈值、效果承诺或未经用户确认的真实事实。
- 不替用户发布内容或执行不可逆业务动作。
- 修改课程方法时必须有受控真源依据；工程便携性修改只能放在发行层。

## 发布前

1. 运行 `python3 tools/validate-package.py`。
2. 运行 `python3 tools/build-release.py`。
3. 在隔离目录用 `npx -y skills add <repo-or-local-path> -g --all` 验证发现和安装。
4. 校验 `dist/SHA256SUMS.txt`。
5. 确认许可证、仓库可见性、GitHub 所有者和脱敏检查结果后再公开推送。
