---
name: jw-grow
description: 按新版课程提炼本人长期认同的理念、表达方向与一致性规则，形成可追溯理念基线。用于用户要塑造个人独特理念、制作理念型内容或检查理念与定位交付是否冲突时。
---

# 线索生客

## 目标

回答“如何用统一理念引领需求，形成长期心智与复利？”，并严格按冻结合同生成 `idea_baseline`。保持原始输入、事实状态、来源、审批、版本和哈希；信息不足时只追问最小缺口。

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

1. 执行 `C40-D01`：从账号起步同时考虑长期竞争、流量变化与内容资产终局
2. 执行 `C40-D02`：从创始人真实认同与长期践行中找到问题解决方向和价值锚点，不把方法当理念
3. 执行 `C40-D03`：检查复杂内容是否最终沉淀为用户可复述的同一简单感觉
4. 执行 `C40-D04`：检查理念是否为目标人指向更好的价值方向，而非只被动回答具体问题
5. 执行 `C40-D05`：用认同或反对的现象、底层逻辑和生活/行业案例解释同一理念
6. 执行 `C40-D06`：理念型表达按已批准解释停在方向和价值判断，不默认展开具体解决方法
7. 执行 `C40-D07`：检查故事、经历、观点、行为与内容是否持续回到同一理念内核
8. 执行 `C40-D08`：仅在不替代理念本体时把理念压缩为可记忆口号，口号不是必填
9. 执行 `C40-D09`：用三至五条内容能否让用户复述一贯相信和推崇什么检查理念成型，不把它当播放量指标
10. 执行 `C40-D10`：检查长期内容与行为能否不断强化同一心智，不用短期爆款替代积累

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

- 不修改 C00 定位、C10 人群/阶段或 C30 即时购买理由与旅程角色
- 不把方法、模型、产品功能、临时人设或口号当理念
- 不策划创始人本人不认同或不能长期践行的立场
- 不创建 C50 拍摄、场景、设备、妆造或灯光方案
- 不把 已批准解释 的派生解释伪装成无冲突的 COURSE_NEW 课程规则
- 不使用案例数字或短期爆款替代理念一致性

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
