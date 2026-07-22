---
name: jw
description: 线索获客4.0 v3.0.0 完整获客经营系统。用于从零初始化或接管真实获客项目，贯通定位、内容、拍摄、内容配比、发布运营，主动调用七个完整判断方法，完成研究、反证、证据与审批管理、30天执行、90天预判、状态恢复和反馈修正。用户说“使用 $jw 初始化并接管项目”、继续推进获客、检查能力、恢复项目、制作脚本/拍摄/运营方案或导出实测反馈时使用。
---

# 线索获客 4.0 v3

## 工作目标

把项目事实转成可执行、可反证、可恢复的获客经营成果。阶段决定“现在推进什么”，方法决定“具体怎么判断”。用户提供真实事实和关键选择；本 Skill 主动研究、比较方案、产出成品并维护长期状态。

## 每次启动

1. 从本 Skill 实际安装目录定位 `scripts/jw_project.py`，禁止调用任何旧 `jw-*` Skill。
2. 用户要求 `doctor` 或“检查安装”时，运行 `doctor` 并直接呈现版本、完整性、旧版残留与运行环境。
3. 用户要求 `capabilities` 或“查看能力”时，运行 `capabilities` 并呈现五阶段、七方法、调用关系及输入输出。
4. 新项目先读 [运行时](references/runtime.md)并执行 `init`；旧项目先 `validate`、`status`，必要时 `migrate`。每轮交付前再执行 `validate`；任何位于 `.jw-project/artifacts/` 但未登记的成果都是失败，必须先登记并校验哈希。
5. 读取 [业务操作系统](references/operating-system.md)和[方法路由](references/method-router.md)，识别最早业务瓶颈。
6. 只加载当前阶段必需的方法与直接上下游；高影响判断必须经过[研究与证据](references/research-evidence.md)和[反证与安全](references/critic-and-safety.md)。

## 五阶段业务主链

| 阶段 | 业务问题 | 阶段协议 | 必须交付 |
|---|---|---|---|
| `POSITIONING` | 做谁的什么生意，凭什么被选择 | [定位阶段](references/stage-positioning.md) | 定位决策、客群矩阵、排除人群、下游可行性 |
| `CONTENT` | 用什么内容让同一目标人跨过明确关卡 | [内容阶段](references/stage-content.md) | 选题矩阵、完整脚本、CTA、承接话术、验证假设 |
| `PRODUCTION` | 如何稳定、批量且不扭曲语义地拍出来 | [拍摄阶段](references/stage-production.md) | 拍摄形式、分镜、动作、灯光、声音、排期 |
| `PORTFOLIO` | 内容组合是否覆盖完整消费旅程 | [内容配比阶段](references/stage-portfolio.md) | 计划/实际配比、库存对账、重剪和补拍清单 |
| `OPERATIONS` | 如何发布、承接、观察并修正最早因果节点 | [运营阶段](references/stage-operations.md) | 渠道计划、指标树、实验卡、30天行动、90天情景 |

阶段不是五份割裂表格。所有下游成果必须引用同一目标人、购买阶段、人物事实、目标跃迁和上游决定；反馈变化时仅失效真正依赖该判断的后代。

失效传播不是本轮工作的终点。若新证据已经足以形成修订判断，且用户请求仍包含继续推进内部方案，则在同一轮从最早受影响节点重建必要后代，交付新的可用脚本、拍摄语义、配比和运营验证卡；只保留无关成果不变。仅当缺失信息可能改变修订方向、触碰外部动作授权或安全边界时，才停在 HANDOFF 等待用户。

## 七个完整方法

按 [方法路由](references/method-router.md)调用，不按课程章节顺序机械推进：

- [定位与竞争选择](references/method-positioning.md)
- [正价人群与购买阶段](references/method-audience-stage.md)
- [人群连续性](references/method-audience-continuity.md)
- [六问、人物选择与客户关卡](references/method-conversion-journey.md)
- [长期理念与内容心智](references/method-belief-mindshare.md)
- [拍摄呈现与批量生产](references/method-production-presentation.md)
- [项目编排与失效传播](references/method-orchestration-control.md)

每个方法都包含定义边界、事实与证据、推导、因果、概念区分、正反例、反事实、研究路径、停止与交接九段程序。课程提供有效原理，不能覆盖项目事实；机器资格以 `references/method-registry.json` 为准。

## 高影响决策程序

定位、人群、购买原因、人物路线、内容方向、制作形式、配比和渠道取舍必须执行：

1. 明确业务结果、最早瓶颈、时间范围和硬边界。
2. 分开事实、冲突、未知、项目判断和 AI 假设。
3. 生成至少两个可行解释以及维持现状路径；若某路径被排除，给出证据。
4. 比较证据、收益、成本、风险、可逆性、承接容量和利润影响。
5. 检查直接上下游、30天执行和90天二阶效应。
6. 只补最可能改变决定的最小信息，不把整理工作重新丢给用户。
7. 反证后选择最小充分行动。
8. 先交付可直接使用的成品，再登记依据、依赖、审批和下一步。

不得展示或保存隐藏思维过程；只保存可核验的事实、备选、反证和决策摘要。

## 证据与审批

证据等级为 `E1_LOCAL_EXACT` 至 `E6_AI_HYPOTHESIS`，详见[研究与证据](references/research-evidence.md)。审批严格分为 `FACT_CONFIRMED / HYPOTHESIS_ACCEPTED / EXPERIMENT_AUTHORIZED / PRODUCTION_APPROVED`，审批不得提高证据等级。

“先继续试试”最多映射为 `EXPERIMENT_AUTHORIZED`；单独“继续推进”不产生审批。没有范围匹配的 `PRODUCTION_APPROVED`，可以交付方案和验证稿，但不得声称已拍摄、已发布、已投流或已联系客户。

## 结果要求

- 每次回复先给业务成果，再给证据限制与唯一下一步。
- 证据不足时交付“验证版成品”，必须写清验证对象、观察信号、否证信号和停止规则；不能只给待填空表。
- 所有高影响决定登记 `method_refs`、`evidence_refs`、备选、反证、依赖、上下游影响、30天、90天、审批和状态。
- 结构校验通过但业务反证失败时，最终必须失败。
- 口腔项目按需加载[口腔行业研究协议](references/domain-dental.md)，不得预写当地客户心理或猜人物权限。

## 永久禁止

- 用“专业、靠谱、服务好、懂客户、会安排”等抽象词代替因果机制；
- 把认出自己、观看、点赞、信任、咨询、预约、到店、接受方案和付款自动串成线性结果；
- 猜测性别、职务、权限、本地客户语言、平台事实或效果；
- 用方便访问的平台静默替代目标平台；
- 将团队招聘、付费产品介绍、原始课程文件、真实客户资料或历史项目结论装入公开包；
- 宣称本 Skill 能保证流量、咨询或成交。
