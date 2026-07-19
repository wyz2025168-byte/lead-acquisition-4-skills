---
name: jw-circle
description: 按新版课程把同一目标人贯穿开头圈、画面圈、内容圈与观点圈，并输出可追溯四圈 Brief。用于用户要圈对短视频受众、检查四圈连续性或修复内容中途换人时。
---

# 线索圈客

## 目标

回答“如何让看视频的人始终是 C10 要成交的那批人？”，并严格按冻结合同生成 `circle_brief`。保持原始输入、事实状态、来源、审批、版本和哈希；信息不足时只追问最小缺口。

## 可移植发行模式

- 本 Skill 可脱离原始编译项目独立安装；运行时只读取本目录内的规则、Schema、追溯绑定与示例。
- 若宿主能执行 Python，先运行 `python3 scripts/validate-bundle.py`；否则至少确认 `BUNDLE_MANIFEST.json` 中的必需文件都存在。
- `references/source-map.json` 只提供公开来源边界声明；不包含私有课程路径、哈希或内部审批记录。
- 未提供项目闸门时使用 `standalone_manual` 模式：只输出候选和追问，不写入项目、不执行发布。

## 启动顺序

1. 先校验本地发行包完整性；失败时停止，不执行课程判断。
2. 读取 `references/course-rules.md`，区分课程规则、已批准解释和工程控制。
3. 读取 `schemas/contract-binding.json` 的公开运行合同；遇到缺失、冲突、审批或版本漂移时，以其中保留的失败码、审批点和失效规则为准。
4. 用 `schemas/intake.schema.json` 接收原始输入；字段齐备后再用 `schemas/input.schema.json` 检查生产合同就绪状态。保留每个字段的 `value_origin`、`truth_status` 与 provenance，不把假设写成事实。
5. 需要确认评测边界时，只读取 `tests/gold-binding.json` 与 `tests/evaluation-binding.json` 的公开证明；私有题目、答案、Rubric、路径、ID 和哈希均不随包分发。

## 决策流程

1. 执行 `C20-D01`：从目标人关心的兴趣话题、兴趣表达、兴趣人物或兴趣观点中选择开头圈路线，使正确人继续看。
2. 执行 `C20-D02`：由目标客户对该业务的审美与信任判断定义画面圈，不用创作者个人审美或成本代替。
3. 执行 `C20-D03`：让内容每句话持续对同一类人说，并保持在目标人可理解的认知跨度内。
4. 执行 `C20-D04`：输出目标人可接受且有启发的观点，不追求脱离目标人的抽象绝对正确。
5. 执行 `C20-D05`：检查开头、画面、内容、观点与每一句表达是否始终面向同一批目标人。

## 输出流程

1. 先判定 `decision_class`、`failure_codes`、`route_to` 与 `approval_requests`。
2. 把本次允许生成的合同字段放入 `artifact`；正常完成时必须包含 `schemas/output.schema.json` 的 `x-normal-artifact-required` 全集。
3. 对信息不足、反例、边界或漂移场景，至少输出 `x-partial-artifact-minimum` 指定的合同级控制字段，并补充本次已确认的上游引用；不得读取逐题答案映射。
4. 给每个事实和判断写入字段级 provenance；显式保留 `confirmed`、`hypothesis`、`unknown`、`contradicted`。
5. 在所有其他字段稳定后生成 `version`，再按输出 Schema 的规范计算 `payload_hash`。
6. 未获得要求的用户批准前，把 `approval_state` 保持为待批准，不向下游发送批准版接口。

## 生产合同与测试夹具

- 始终以 `schemas/input.schema.json` 和冻结合同为生产字段标准；黄金题的简写只用于测试适配。
- 只映射测试夹具中显式等价的语义别名；未显式提供的字段继续标缺失，不推断事实。
- 不把测试夹具的字段粒度、答案或案例数字反向写入课程规则。

## 缺失、冲突与漂移

- 按冻结合同的 `minimum_clarification.question_order` 追问；已有可追溯事实时不要重复询问。
- 命中 block 级失败码时停止受影响分支，只路由到最早 owner。
- 上游版本变化时按 `invalidation_rules` 标记 `stale_targets`；不要整库重写。
- 多个高风险候选并存时保留差异并请求用户取舍；不要替用户批准。

## 能力边界

- 不为提高播放量、热度或泛流量扩大或更换 C10 人群
- 不更改 C10 已批准的买单前阶段、价值感与话题边界
- 不用创作者个人审美、高成本或制作便利代替目标人画面判断
- 不创建 C30 购买理由、信任机制或消费旅程
- 不创建 C50 的场景、妆造、设备、机位或灯光方案

- `references/source-map.json` 只证明来源边界；实际执行只依据本包的公开课程规则与运行合同。
- 不创建跨行业统一阈值、效果承诺或真实项目事实。
- 有项目闸门时不跳门；无项目闸门时保持 `standalone_manual`，不执行发布。

## 资源

- `references/course-rules.md`：冻结规则、证据与边界。
- `references/source-map.json`：脱敏后的公开来源边界证明。
- `schemas/contract-binding.json`：保留执行语义、失败处理、审批点和失效规则的公开运行合同。
- `schemas/intake.schema.json`、`schemas/input.schema.json`：部分接收与生产就绪输入约束。
- `schemas/artifact.schema.json`、`schemas/output.schema.json`：完整成果与运行信封约束。
- `tests/gold-binding.json`、`tests/evaluation-binding.json`：只含评测类型与通过状态的公开证明，不含题目、答案或评分细则。
- `BUNDLE_MANIFEST.json`、`scripts/validate-bundle.py`：安装后本地完整性校验。
- `examples/normal-invocation.md`：中性离线夹具示例。
