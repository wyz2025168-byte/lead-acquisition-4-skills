# R01–R15 对照表

| ID | 运行时裁决 | 自动化证据 | 结果 |
|---|---|---|---|
| R01 | 领先事件替代成交 → `E-OUTCOME-SUBSTITUTION` | `test_r01_leading_event_cannot_be_success` | PASS |
| R02 | 内部职责替代客户购买理由 → `E-PERSONA-INSIDE-OUT` | `test_r02_inside_out_persona_is_blocked` | PASS |
| R03 | B5 未批先批内容 → `E-CONTENT-BEFORE-AUDIENCE` | `test_r03_content_before_audience_is_blocked` | PASS |
| R04 | 泛研究直接排本地人群 → `E-LOCAL-RANKING-BY-GENERAL-RESEARCH` | `test_r04_external_research_cannot_rank_local_audience` | PASS |
| R05 | 无决策用途或超量索数 → `E-DATA-REQUEST-NO-DECISION` / `E-DATA-REQUEST-OVERSIZED` | `test_r05_request_without_decision_and_oversized_is_blocked` | PASS |
| R06 | 含糊“继续”不等于方向批准 → `E-APPROVAL-NO-PROVENANCE` | `test_r06_ambiguous_continue_is_not_direction_approval` | PASS |
| R07 | 未判断线上可转化便锁人 → `E-ONLINE-CONVERTIBILITY-UNKNOWN` | `test_r07_online_convertibility_unknown_blocks_audience` | PASS |
| R08 | W6 未知时带候选探索 → `W-W6-UNKNOWN`，不批准 | `test_r08_w6_candidates_allow_exploration_with_warning` | PASS |
| R09 | 上游纠正只失效真正后代 | `test_r09_upstream_correction_only_invalidates_descendants` | PASS |
| R10 | 模糊首轮停在 B0 最小定义 | `test_r10_natural_first_turn_stops_at_b0` | PASS |
| R11 | 无历史数据仍给最小验证 | `test_r11_no_history_data_uses_nonblocking_fallback` | PASS |
| R12 | 外部研究冲突不覆盖一手事实 → `W-RESEARCH-CONFLICT` | `test_r12_external_research_conflict_does_not_override_local_fact` | PASS |
| R13 | 无姓名职务后购买理由仍须成立 | `test_r13_customer_side_persona_passes_title_free_test` | PASS |
| R14 | 到店可作领先指标，不作成功 → `W-LEADING-METRIC-ONLY` | `test_r14_leading_event_is_legal_when_not_success` | PASS |
| R15 | 迁移幂等、备份不变、可非破坏回滚 | `test_r15_migration_is_idempotent_and_keeps_backup` + rollback test | PASS |

每个阻断错误在 `business-invariants.json` 中登记默认严重度和最小修复；合法场景由对应正向测试保护。
