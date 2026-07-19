# 全案编排器｜公开运行规则

- Capability: `C90`
- Public release: `v1.0.0-rc1`
- Provenance: 由私有课程真源编译并完成独立评测；公开版省略来源编号、路径、哈希和内部审批记录。

只把 `origin=COURSE_NEW` 的判断当作课程规则。把 `COURSE_INTERPRETATION` 保留为已批准解释，把 `AI_ENGINEERING` 只用于结构、路由、版本、审批和失败控制。不得用验证案例改写规则。

## 决策规则

| ID | Origin | 编译判断 |
|---|---|---|
| C90-D01 | AI_ENGINEERING | 校验每个输入成果的 owner、origin、source、version、approval、payload_hash 与 stale 状态后才允许路由。 |
| C90-D02 | AI_ENGINEERING | 按冻结主链、当前闸门和已批准依赖选择唯一下一能力，不以案例或请求便利改变顺序。 |
| C90-D03 | AI_ENGINEERING | 维护批准版本与依赖；上游变化时只标记受影响下游为 stale，不整库重写。 |
| C90-D04 | AI_ENGINEERING | 发现人群、阶段、购买理由、理念或呈现版本漂移时，定位最早发生偏差的 owner 并定点退回。 |
| C90-D05 | AI_ENGINEERING | 按当前闸门 Definition of Done、质量结果和审批状态给出 Go、No-Go 或 Awaiting Approval，不跳门、不代批。 |
| C90-D06 | AI_ENGINEERING | validation-only 案例只检查既有能力的组合覆盖、顺序和漂移；不形成规则、阈值或效果承诺。 |
| C90-D07 | AI_ENGINEERING | 理念型内容进入制作时，并列路由 C30 角色指针、已批准 C40 理念和 C20 视觉 Brief 给 C50，不允许循环改写。 |

## 不变量

| ID | Origin | 必须保持 |
|---|---|---|
| C90-I01 | AI_ENGINEERING | C90 所有状态、版本、路由、失败、失效和审批判断均为 AI_ENGINEERING，不冒充课程方法。 |
| C90-I02 | AI_ENGINEERING | 主链顺序证据只约束调用顺序，不定义工程状态机、失败码、审批或闸门。 |
| C90-I03 | AI_ENGINEERING | validation-only 案例只用于回放验证，案例动作与数字不得进入 rule_refs、阈值、行业基准或承诺。 |
| C90-I04 | AI_ENGINEERING | C90 不创建、不修改、不批准 C00-C50 的课程内容判断，只路由回原 owner。 |
| C90-I05 | AI_ENGINEERING | 任一成果缺少 owner、origin、source、version、approval、payload_hash 或 stale 状态时不得向下游发送。 |
| C90-I06 | AI_ENGINEERING | 发现漂移时必须定位最早偏差 owner 并只传播受影响 stale_targets，不整库重写。 |
| C90-I07 | AI_ENGINEERING | 没有满足当前闸门 Definition of Done 和所需用户批准时，下一闸门保持阻断。 |

## 边界

- 不创建、补写或修改 C00-C50 的任何课程方法或业务判断
- 不把 validation-only 案例提升为规则、阈值、行业基准或结果承诺
- 不替代用户做不可逆方向、重大规则升级或最终发布审批
- 不跳过当前闸门或在 G9 前发布
- 不因一个下游错误整库重写未受影响成果
