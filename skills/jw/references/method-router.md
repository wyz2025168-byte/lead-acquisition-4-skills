# 方法路由与跨阶段调用

阶段决定当前业务任务，方法提供判断程序。不得让方法编号或课程章节决定推进顺序；先定位最早瓶颈，再加载最少充分方法。

| 阶段 | 主方法 | 条件调用 | 典型输入 | 典型输出 |
|---|---|---|---|---|
| `POSITIONING` | `positioning-competition`、`audience-stage` | `conversion-journey` 用于购买角色和正价交易链校验；`orchestration-control` 始终调用 | 产品、价格、利润、历史交易、替代、人物、容量 | 候选定位比较、客群矩阵、排除人群、最小验证 |
| `CONTENT` | `audience-continuity`、`conversion-journey` | `belief-mindshare` 规划长期心智；必要时回查前两方法 | 已批准目标人与阶段、真实语言、人物事实、关卡 | 选题、完整脚本、CTA、承接、验证内容 |
| `PRODUCTION` | `production-presentation` | 继承 `audience-continuity`、`conversion-journey`、理念语义 | 脚本、人物、场地、设备、预算、产能、合规 | 拍摄形式、分镜、动作、布光、声音、排期 |
| `PORTFOLIO` | `conversion-journey`、`belief-mindshare` | `audience-continuity` 查同一人；`production-presentation` 查库存可实现性 | 关卡、内容角色、计划与实拍库存 | 计划/实际配比、旅程缺口、重剪/补拍 |
| `OPERATIONS` | `conversion-journey`、`orchestration-control` | 按异常回调任一上游方法；研究和反证始终可用 | 发布资产、渠道、承接、指标、真实反馈 | 发布实验、归因、30天动作、90天情景、局部失效 |

## 高影响判断的共同输入

- 当前业务目标与最早瓶颈；
- 已确认事实、冲突、未知、限制和历史反证；
- 上游决定、版本、依赖和审批范围；
- 利润、时间、人员、内容产能、咨询与交付容量；
- 目标地域、平台、合规与数据时效。

## 共同输出契约

每项高影响决定必须携带：`business_stage`、`method_refs`、`evidence_refs`、`counterevidence`、`alternatives`、`selected_path`、`depends_on`、`upstream_impacts`、`downstream_impacts`、`horizon_30d`、`horizon_90d`、`approval_state`、`status`。

## 路由失败条件

- 上游事实或批准版本失效；
- 当前方法缺必需输入，却能通过更上游方法或最小研究解决；
- 目标要求跨越生产批准、隐私、医疗、平台或法律边界；
- 方法注册表将该项标为 `RETIRED` 或其适用状态为 `REJECTED_FOR_PROJECT`。

失败时返回最早可修复节点，不整库重写。
