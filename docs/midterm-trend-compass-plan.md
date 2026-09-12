# 日线中期趋势罗盘：产品实现方案 v2

> 仓库：`https://github.com/gyc567/daily_stock_analysis`
>
> 产品原则一句话：**用周线和日线决定这轮趋势还在不在、仓位该有多重；用 60 分钟决定今天这笔分批做不做；不要用 4 小时或 8 小时决定千万仓位的方向。**
>
> 本方案把「千万级波段资金 + A 股 T+1 + EMA20/50/100/200 与 RSI(14，Wilder)」做成可上线的后台产品，不是再做一套短线信号机。
>
> **本文为审计 + 优化版 v2**。原方案的产品决策、产品定位、阶段合成、动作改写表、千万级仓位纪律、分期交付等核心内容保留；与现有 `decision_action` / `InvestmentConclusion` / `phase_decision_guardrail` / `daily_market_context_guardrail` / `AnalysisContextPack` / `trading_calendar` / `backtest_engine` 等模块的衔接边界被补齐；三层防御（Pydantic v2 + icontract + mypy）显式落到字段契约；作者单方面追加的两条默认被回退到「待确认项」。

---

## 0. 审计纪要

### 0.1 与现有系统的关键冲突

| # | 冲突点 | 原方案位置 | 现有实现 | v2 处理 |
|---|---|---|---|---|
| 1 | **决策档位不兼容** | 第 4.5 节 三档「买入/观望/卖出」 | `src/schemas/decision_action.py` 已有 8 档 `buy/add/hold/reduce/sell/watch/avoid/alert`；`InvestmentConclusion.action` 是 6 档中文「建仓/加仓/持有/减仓/止损/观察」 | 显式建立映射表，新增 `CompassAction` 枚举，禁用 `add`/`reduce`/`hold`/`avoid`/`alert` |
| 2 | **改写器与现有 Guardrail 顺序未定义** | 第 4.5 节 改写表 | `daily_market_context_guardrail.py` 已在保守语境下软化买入；`phase_decision_guardrail.py` 已在盘前/非交易日压制 | 明确执行顺序为 `phase_guardrail → market_context_guardrail → compass_rewriter`；三者输出合并到同一 `decision_type` |
| 3 | **指标体系与默认基线不一致** | 第 4.2 节 EMA20/50/100/200 + RSI(14) | `bull_trend.yaml` 与 `CORE_TRADING_SKILL_POLICY_ZH` 用 MA5/10/20 | 不替换默认；新增独立策略文件 `strategies/midterm_compass.yaml`，默认 `default_active=false`，仅在用户开启时启用 |
| 4 | **未挂入现有 AnalysisContextPack** | 第 6 节架构 | `src/schemas/analysis_context_pack.py` 已定义 envelope + `ContextFieldStatus`（`available/missing/fallback/stale/estimated/partial/fetch_failed/not_supported`） | 罗盘输出以 `block_key="midtrend_compass"` 注入 `AnalysisContextPack.blocks`；字段质量走 `ContextFieldStatus` |
| 5 | **未与 DecisionSignal / Backtest / Portfolio 集成** | 第 9 节接入清单 | `decision_signal_extractor.py` + `decision_signal_service.py`、`core/backtest_engine.py`、`services/portfolio_service.py` 已存在 | 显式标注三种集成路径与隔离边界；Backtest 留作 P5 验证通道 |
| 6 | **停牌 / 陈旧数据无规则** | 第 7 节数据与质量 | `pipeline.py` 已用 `is_stale` / `stale_seconds` 字段 | 罗盘新增 `bar_status ∈ {closed, intraday_unconfirmed, stale, suspended}`；stale 视为 watch，不输出 L1 |
| 7 | **作者单方面锁两条默认** | 第 2 节末尾 | AGENTS.md §1 强调"未经明确确认不执行 git commit/push"；本仓库 PR/Issue 工作流默认走 reviewer 共识 | v2 把这两条移到 §13「待确认项」，必须由 maintainer 显式确认 |

### 0.2 主要优化清单

1. 字段契约升级为 Pydantic v2 + Literal 枚举 + `validate_assignment=True`，冻结 schema 版本与迁移路径。
2. 阶段合成表补充平局裁决、缺 L3 时的退化规则、phase → action 的中间映射。
3. 改写器表补充 reason code（结构化）+ 与现有 Guardrail 的合并语义。
4. 短卡格式从示例升级为正式 spec（列宽、排序、缺失字段、rendering fallback）。
5. 多语言：阶段/动作/原因全部提供中英文 `i18n`。
6. 时区纪律：`as_of_trade_date` 强制走 `MARKET_TIMEZONE["cn"] = Asia/Shanghai`。
7. CI 接入：`scripts/ci_gate.sh` + `.github/workflows/type-safety.yml` 必须覆盖新模块；新增 icontract 慢速契约测试。
8. 观测与回滚：每次改写必须输出 `action_reason`，落 `analysis_history.context_snapshot.midtrend_compass`，便于回溯与回放。
9. 风险与失败模式：列出 6 类已知失败模式（数据缺失、周线样本不足、改写器过保守、改写器与 Guardrail 冲突、phase 抖动、改写后未与 LLM 同步）。

### 0.3 与仓库治理的契约

- 遵循 `AGENTS.md` §1 目录边界；罗盘核心代码落在 `src/services/compass/`、`src/schemas/compass.py`，策略描述落在 `strategies/midterm_compass.yaml`。
- 遵循 §1.2 Ponytail：不引入工具函数库、不引入仅 1 个使用者的抽象基类、不为单次使用做包装。
- 遵循 §1.4 三层防御（详见 §14）。
- 任何用户可见变化（CLI、Web、Bot、推送摘要、报告结构）必须同步 `docs/CHANGELOG.md` 与相关 `docs/*.md`，新增配置同步 `.env.example`。
- 报告 / 渲染改动按 §1 强制要求附 PR 前后截图或可视证据。
- PR 标题遵循 §1.1 推荐格式（不阻断）。

---

## 一、产品定位

### 1.1 给谁用

- 可交易权益约 1000 万到几千万人民币
- 持有窗口按 **2 周到 3 个月** 管理，一周只用来把计划做成成交
- 标的是 A 股股票、ETF，大盘指数只做环境过滤
- 每天收盘复盘，盘中也可手动点开看，但盘中结论不得比收盘更激进

### 1.2 解决什么问题

每天真正要回答的不是「明天涨不涨」，而是：

1. 现在是不是处在一轮已经形成的中期趋势里
2. 这轮趋势的时间量级是数周、1–3 个月，还是只剩年度背景
3. 当前该 **买入 / 观望 / 卖出**（由罗盘约束或改写最终动作）
4. 相对昨天，阶段有没有变坏

### 1.3 明确不做什么

- 不预测未来 1 周涨跌幅或高低点
- 8 小时不作为独立系统
- 4 小时不作为主策略，一期甚至不算 4 小时指标
- 不和下单通道耦合
- 不与缠论、波浪互改结论，只并列
- 不做港股美股（一期冻结为纯 A 股）
- 不替换现有 `bull_trend` 默认技能基线

### 1.4 周期在产品里的角色

| 周期 | 产品角色 | 一期是否实现 |
|---|---|---|
| 周线 | 大方向过滤器，只决定仓位上限语义，不决定今天买卖点 | **要实现**：周线 EMA50/200 过滤层 |
| 日线 | 主战场，L1/L2/L3 全套 | **主交付** |
| 60 分钟 | 执行层，回答今天能否分批 | 二期 |
| 4 小时 | A 股上与日线高度重叠，仅作可选执行参考 | 不做独立系统 |
| 8 小时 | 无独立价值 | 永不做 |

这是资金能执行的周期，不是「哪个图更好看」。

---

## 二、已冻结的产品决策

1. 纯 A 股；股票 / ETF 启用；指数和大盘复盘各出一份罗盘
2. 收盘日更 + 盘中 Web/API 都出；用到未完成日 K 则标 `bar_status = intraday_unconfirmed`
3. 允许改写最终「买入 / 观望 / 卖出」
4. 短卡进推送摘要
5. 落收盘快照，做出「较昨日」
6. 日线、周线均用**前复权**（与现有 `data_provider` `adjust="qfq"` 一致）
7. 次新 / 样本不足：开 L2/L3，关 L1
8. 与缠论等完全独立、并列展示

> 注：作者在原方案第 2 节末尾追加的两条默认（周线过滤偏空时个股最高「观望」/L1+L2 空头默认卖出、L3 exhausted 则观望）已**移到 §13 待确认项**，本节不视为冻结决策。

---

## 三、用户能看到什么

### 3.1 每日摘要短卡（通知主界面）

每票一行，指数区在个股前。短卡 schema（v2 正式化）：

```
[name ≤ 8字] | [phase_icon phase_text] | [L2_text] | [action_text] | [vs_prev_arrow] | [bar_text] | [L0_text]
```

- `phase_icon`：🟢 扩张 / 🟡 持有 / 🟠 动能先弱 / ⚪ 收口 / 🔴 切换（仅视觉辅助；渲染端可改为彩色文字避免无障碍问题）
- `L2_text`：持主段 / 休整 / 收口 / 破坏（与 L2 枚举一一对应）
- `action_text`：买入 / 观望 / 卖出
- `vs_prev_arrow`：↑ / ↓ / →（与昨日 `closed` 快照的 phase 对比）
- `bar_text`：已收 / 盘中 / 陈旧
- `L0_text`：周多 / 周空 / 周转 / —

阶段对外中文（同时维护英文 i18n）：

| key | zh | en |
|---|---|---|
| `trend_expanding` | 趋势扩张 | Expanding |
| `trend_holding` | 同轮持有/休整 | Holding |
| `trend_tiring` | 动能先弱 | Tiring |
| `coiling` | 收口震荡 | Coiling |
| `transitioning` | 结构切换 | Transitioning |

动作对外（zh/en 同字段）：

- 买入 / Buy
- 观望 / Watch
- 卖出 / Sell

指数动作不用买入/卖出，只用：偏多观察 / 中性 / 偏空观察（Bullish Watch / Neutral / Bearish Watch）。

盘中短卡必须带「盘中未确认」。`bar_status ∈ {intraday_unconfirmed, stale, suspended}` 时不允许短卡出现「买入」。

### 3.2 完整报告长卡

顺序固定：

1. 周线过滤（仓位上限语义）
2. 日线阶段 + 观察量级
3. L1 / L2 / L3
4. 失效条件
5. 系统动作 + 改写理由（reason code + 中文一句话）
6. 较昨日（vs_previous 块：phase 变化、L2 变化、L0 变化）
7. 风险与数据限制（数据样本、停牌/陈旧说明）
8. 其它模块（缠论等）标题写明「独立并列」

禁止出现的句子：

- 未来一周看涨 / 看跌
- 未来两周一定延续
- 大趋势还有半年（当 phase 已是 tiring/coiling/transitioning 时）
- 因 4 小时死叉建议清仓

### 3.3 Web / API 手动分析

与日更同一计算核。返回多一个 `bar_status` 和 `phase` / `action` / `action_reason` 三个顶层字段。盘中可以把当日未完成 K 纳入计算，但：

- 标记 `intraday_unconfirmed`
- 动作不得新开「买入」
- 快照**不覆盖**当日 `closed` 快照（仅 cron 收盘任务能覆盖 `closed`）

收盘任务重算后，以 `closed` 覆盖当天同 code 的 `intraday_unconfirmed` 快照；同一交易日多次 `closed` 写入以最新为准，但 version 字段必须单调递增。

---

## 四、核心逻辑（产品规则，不是预测）

### 4.1 周线过滤层（L0）

输入：前复权周线，至少约 60 根周 K，否则 L0 = `weekly_disabled`。

规则尽量少：

- 价在周线 EMA200 上方，且周线 EMA50 在 EMA200 上方 → `weekly_bull`
- 价在周线 EMA200 下方，且周线 EMA50 在 EMA200 下方 → `weekly_bear`
- 其余 → `weekly_transition`

产品含义：

- `weekly_bull`：允许日线把波段仓做重（只是上限许可，不自动买入）
- `weekly_transition`：日线结果保留，但买入降为观望
- `weekly_bear`：禁止系统买入；日线若仍偏多，报告写「逆大结构，过滤器不允许加仓」
- `weekly_disabled`：周线不参与动作改写，只注明样本不足

周线不输出买卖点，不参与 L2/L3 计算。

### 4.2 日线三层（主罗盘）

指标：EMA20/50/100/200 + RSI(14, Wilder)，前复权日线。

斜率窗口与时间量级对齐：

- EMA20 斜 10 日 ≈ 2 周节奏
- EMA50 斜 20 日 ≈ 1 个月主段
- EMA200 斜 40 日 ≈ 大结构是否还开口

**L1 半年到一年（过滤器）**

- 枚举：`annual_bull / annual_bear / annual_transition / annual_disabled`
- 根数 < 220 则 `annual_disabled`，禁止出现 `trend_expanding`

**L2 1–3 个月（大仓位核心）**

- 枚举：`alive / resting / flattening / broken`
- 回踩或反抽日线 EMA20/50 且结构未坏 = `resting`，视为同一轮休整，不是新周期

**L3 2–6 周（节奏，只管加减）**

- 枚举：`healthy / cooling / exhausted / noisy`
- 不回答大趋势反没反转

### 4.3 阶段合成（优先级锁死 + 平局裁决）

按以下顺序**短路求值**，首条命中即返回；后续不再评估：

1. L1 关闭（`annual_disabled`） → 最高 `trend_holding`
2. L1 切换（`annual_transition`）且 L2 ∈ {`flattening`, `broken`} → `transitioning`
3. L2 = `flattening`，或 (L2 非 `alive` 且 L3 ∈ {`exhausted`, `noisy`}) → `coiling`
4. L2 ∈ {`alive`, `resting`}（即「同一轮」）且 L3 = `exhausted` → `trend_tiring`
5. L2 = `resting` 或 L3 = `cooling` → `trend_holding`
6. L0 ∈ {`weekly_bull`, `weekly_transition`, `weekly_disabled`}（即"非 bear"）且 L1 = `annual_bull` 且 L2 = `alive` 且 L3 = `healthy` → `trend_expanding`
7. 其它（含 L3 = `noisy` 但 L2 = `alive` 的未覆盖情形）→ `transitioning`

**v2 显式澄清**：

- 规则 4 要求 L3 严格 `exhausted`；L3 = `noisy` 但 L2 = `alive` 不进入 tiring，归入规则 7 的 `transitioning`。
- L3 缺失（数据无效导致 `noisy` 但含义实为缺失）走规则 7，并在 `limitations` 中标注 `l3_missing`。
- L2 = `broken` 一律只产出 `coiling` / `transitioning` / `broken` 阶段相关动作，不允许产出 `trend_expanding`。

### 4.4 三个时间窗怎么对外说

| 窗口 | 对应层 | 系统允许说 | 系统禁止说 |
|---|---|---|---|
| 未来 1 周 | 执行窗 | 本周检查失效、按计划分批 | 未来一周看多/看空 |
| 未来 2 周 | L3 | 节奏健康/降温/失配 | 未来两周必然延续 |
| 未来 1 个月 | L2 | 主趋势段仍在/休整/收口/破坏 | 还能涨几个点 |

### 4.5 最终动作改写

个股/ETF 仅三档：`buy / watch / sell`。

#### 4.5.1 改写器在 Guardrail 链中的位置

```
phase_decision_guardrail
        │  压制盘前/非交易/未知阶段；不会新增买入
        ▼
daily_market_context_guardrail
        │  在保守语境下软化 buy
        ▼
midtrend_compass_rewriter
        │  按本表硬约束改写；与上述两者不冲突时透传
        ▼
final decision_type / operation_advice / dashboard.action
```

三者任一压制都生效；最终 `decision_type` 取三者最保守的结果（buy → watch → sell 单调降级）。

#### 4.5.2 硬约束改写表（结构化 reason code）

| 条件（任一命中即改写） | 原动作 | 改写后 | reason code |
|---|---|---|---|
| 数据 missing / fetch_failed / 连续 ≥5 个交易日 stale | 任意 | watch | `data_missing` |
| `bar_status ∈ {intraday_unconfirmed, stale, suspended}` 且初稿 = buy | buy | watch | `intraday_unconfirmed_buy_blocked` |
| L0 = `weekly_bear` 且初稿 = buy | buy | watch | `weekly_bear_buy_blocked` |
| L0 = `weekly_transition` 且初稿 = buy | buy | watch | `weekly_transition_buy_blocked` |
| L1 = `annual_disabled` 且初稿 = buy | buy | watch | `l1_disabled_buy_blocked` |
| phase ∈ {`coiling`, `transitioning`} 且初稿 = buy | buy | watch | `coiling_transitioning_buy_downgraded` |
| phase = `trend_tiring` 且初稿 = buy | buy | watch | `tiring_buy_downgraded` |
| L2 = `resting` 且初稿 = sell | sell | watch | `resting_sell_blocked`（禁止把休整当反转）|
| L2 = `broken` 且 L1 偏空、`bar_status=closed` | watch/buy | sell | `l2_broken_bear_allow_sell` |
| L2 = `broken` 但 L1 偏多（多头段坏）且初稿 = sell | sell | watch | `l2_broken_bull_sell_blocked` |
| L1 = `annual_bear` 且 L2 = `alive` 且 `bar_status=closed`（双空头 alive） | watch | sell | `l1_l2_bear_sell_default`；但 L3 = `exhausted` 降级为 watch（reason code 替换为 `l3_exhausted_sell_downgraded`） |
| L1 = `annual_bull` 且 L2 = `alive` 且 L3 = `healthy` 且 L0 非 `weekly_bear` 且 `bar_status=closed` 且初稿 = sell | sell | watch | `l1_l2_l3_healthy_buy_allowed`（说明：此条不是"允许 buy"而是"屏蔽与多头段冲突的 sell"） |
| 与 `daily_market_context_guardrail` 输出的 buy→watch 不冲突 | buy | watch | `market_guardrail_softened`（透传 reason） |
| 与 `phase_decision_guardrail` 输出的压制不冲突 | 任意 | watch | `phase_guardrail_suppressed`（透传 reason） |

#### 4.5.3 弱倾向（与硬约束叠加使用，不冲突）

- 扩张偏多 → 允许 buy；持有段 → 默认 watch；收口/切换 → 默认 watch。
- `trend_holding` **不自动升级成 buy**，避免在回踩里追。

#### 4.5.4 流水线顺序

```
读日线 / 周线 → 算 L0/L1/L2/L3 → 算 phase
        │
        ▼
LLM 初稿（可选）
        │
        ▼
compass_rewriter.rewrite(initial_draft, l0, l1, l2, l3, phase, bar_status)
        │
        ▼
final_action + action_reason_codes[]
```

#### 4.5.5 与 DecisionAction / InvestmentConclusion 的映射

| CompassAction | DecisionAction（8 档） | InvestmentConclusion.action | 备注 |
|---|---|---|---|
| `buy` | `buy` | `建仓` | 严禁 `add` / `hold` / `reduce` |
| `watch` | `watch` | `观察` | 不允许降为 `hold` |
| `sell` | `sell` | `止损` | 严禁 `reduce` |

映射由 `src/services/compass/action_mapper.py` 单一函数维护，禁止散落写入。

---

## 五、和「千万仓位纪律」如何产品化

1. **降频**  
   phase 为扩张或持有时，短卡不给「今日必须交易」类提示。只有 L2 broken、周线转空、失效条件触发，才强调大动仓。

2. **分批是二期能力**  
   一期只给方向与是否允许开/平，不给「今天买 200 万」。报告可固定一句操作提示：「若执行，按 3–6 个交易日分批，而不是当日一口吃满。」

3. **流动性不在计算核里一票否决，但要提示**  
   若项目已有成交额字段，长卡加风险：「日成交偏低时，大额进出可能自己破坏均线。」无数据则不做假过滤。

4. **T+1**  
   盘中买入一律降级，产品上承认没有盘中纠错权。

5. **4 小时噪声隔离**  
   一期接口和报告不出现 4 小时/8 小时结论，避免用户拿短周期否决日线主段。

6. **v2 新增：动作改写必须可解释**  
   每条改写都带 reason code（见 §4.5.2），并落到 `analysis_history.context_snapshot.midtrend_compass.action_reason_codes`，便于事后审计与回放，避免用户对「为什么没买」无据可查。

---

## 六、系统架构（与现有模块的对接）

```text
前复权日线 / 周线        前置：trading_calendar + data_provider (qfq)
        │
        ▼
┌───────────────────┐
│ Compass Engine    │  纯计算，无 LLM
│  L0 周线过滤      │   ↘
│  L1/L2/L3 日线    │    → AnalysisContextPack.blocks["midtrend_compass"]
│  phase 合成       │    （含 bar_status / sample_size / quality status）
└─────────┬─────────┘
          │
          ▼
 phase_decision_guardrail → daily_market_context_guardrail → compass_rewriter
                                              │
                                              ▼
                              AnalysisResult.decision_type / operation_advice / dashboard.action
                                              │
                              ┌───────────────┼────────────────┐
                              ▼               ▼                ▼
                       notification      report render    analysis_history
                       (短卡 + 长卡)     (markdown/pdf)    (context_snapshot)
```

### 6.1 与现有模块的关系（v2 显式化）

| 模块 | 罗盘与它的关系 |
|---|---|
| `src/core/pipeline.py` | 罗盘计算发生在「日线已取到、LLM 未写报告」之前，注入到 `AnalysisContextPack`。 |
| `AnalysisContextPack` | 罗盘以 `block_key="midtrend_compass"` 注入 `blocks`，受 `ContextFieldStatus` 质量约束。 |
| `phase_decision_guardrail` | 在盘前 / 非交易日 / 未知阶段压制；先于罗盘改写器运行。 |
| `daily_market_context_guardrail` | 在保守语境下软化 buy；先于罗盘改写器运行。 |
| `decision_signal_extractor` | 仅在罗盘给出 `CompassAction` 后提取；若罗盘 disable 或 fetch_failed，跳过提取。 |
| `src/services/compass/` | 新建目录：`engine.py`（纯计算）、`rewriter.py`、`action_mapper.py`、`snapshot.py`、`i18n.py`。 |
| `src/schemas/compass.py` | 新建：Pydantic v2 模型 + Literal 枚举 + icontract 契约。 |
| `strategies/midterm_compass.yaml` | 新建：策略描述、`default_active=false`、`core_rules=[1,2,3]`、`market_regimes=["trending_up","transitioning"]`。 |
| `market_analyzer.py` / `market_review.py` | 大盘复盘复用同一罗盘引擎；动作档位换为「偏多观察 / 中性 / 偏空观察」。 |
| `bot/` | 短卡复用 `notification_capabilities` 与 `notification_routing`；不新增通道。 |
| `backtest_engine.py` | P5 提供回放通道：一期不启用，二期可作为改写器反向验证。 |
| `apps/dsa-web/` | 手动分析返回 `phase`/`action`/`action_reason`；不写 history。 |
| `apps/dsa-desktop/` | 与 Web 同 schema；Electron 渲染层直接消费 `phase`/`action`/`action_reason`。 |
| `data_provider` | 周线若现有 fetcher 不支持，**先扩展现有 fetcher**（优 `akshare_fetcher` / `baostock_fetcher` 已支持前复权周线），不引入新数据源平行业务。 |

### 6.2 失败隔离

- 单票失败则该票 `fetch_failed` + 强制 watch；不阻断其它票。
- L0/L1/L2/L3 任一层失败：写入 `limitations`，phase 仍按可用层合成（按 §4.3 退化路径）。
- LLM 失败：罗盘输出仍可独立生效，不依赖 LLM 初稿。

---

## 七、数据与质量

| 项目 | v2 规则 |
|---|---|
| 市场 | 仅 CN（`market=cn`，指数走同一引擎但 action 三档不同） |
| 复权 | 前复权，与现有日线源同一条（`adjust="qfq"`） |
| 日线门槛 | <30 missing；30–219 partial（关 L1，开 L2/L3）；≥220 全开 |
| 周线门槛 | <60 则 `weekly_disabled` |
| 停牌 | 用最近可用日；`bar_status="stale"` + `stale_since` 字段记录停牌日期 |
| 盘中 K | 可用；必须标 `bar_status="intraday_unconfirmed"` |
| 收盘任务 | 必须重算 `closed`，覆盖当日 `intraday_unconfirmed` 快照；同 `trade_date` 多版本用 `version` 字段去重 |
| 指数 | 同一状态机；动作档位为「观察三档」；不进入改写表 buy 路径 |
| 时区 | `as_of_trade_date` 走 `MARKET_TIMEZONE["cn"] = "Asia/Shanghai"`；其他时区一律按市场时区解释，禁止用 server local time |
| 周线来源 | 复用 `data_provider` 周线 fetcher；缺失时不允许 mock 静默降级，必须 `weekly_disabled` |
| 数据源失败 | 走现有 fallback 链；罗盘不引入新数据源优先级；超时策略沿用 `data_provider/base.py` 默认 |

### 7.1 字段质量状态对齐

罗盘块内每个字段沿用 `src/schemas/analysis_context_pack.py:ContextFieldStatus`：

- `available` / `missing` / `not_supported` / `fallback` / `stale` / `estimated` / `partial` / `fetch_failed`

`status` 字段级状态用于：

- Prompt 注入时只取 `available`/`estimated` 字段
- 仪表盘 / Web / 桌面端展示时全部保留但降级提示
- 改写器在 `fetch_failed` / `stale` / `partial` 时直接产出 watch（reason=`data_missing`）

---

## 八、字段契约（v2）

### 8.1 顶层 schema（草案，需在 `src/schemas/compass.py` 落地）

```python
from typing import Annotated, Literal, Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

SubjectType = Literal["stock", "etf", "index"]
BarStatus = Literal["closed", "intraday_unconfirmed", "stale", "suspended"]

L0Status = Literal["weekly_bull", "weekly_bear", "weekly_transition", "weekly_disabled"]
L1Status = Literal["annual_bull", "annual_bear", "annual_transition", "annual_disabled"]
L2Status = Literal["alive", "resting", "flattening", "broken"]
L3Status = Literal["healthy", "cooling", "exhausted", "noisy"]
Phase = Literal["trend_expanding", "trend_holding", "trend_tiring", "coiling", "transitioning"]
CompassAction = Literal["buy", "watch", "sell"]

# 与 §4.5.2 reason 表一一对应；扩展时追加并同步 i18n
ActionReasonCode = Literal[
    "data_missing",
    "intraday_unconfirmed_buy_blocked",
    "weekly_bear_buy_blocked",
    "weekly_transition_buy_blocked",
    "l1_disabled_buy_blocked",
    "coiling_transitioning_buy_downgraded",
    "tiring_buy_downgraded",
    "resting_sell_blocked",
    "l2_broken_bear_allow_sell",
    "l2_broken_bull_sell_blocked",
    "l1_l2_bear_sell_default",
    "l3_exhausted_sell_downgraded",
    "l1_l2_l3_healthy_buy_allowed",
    "market_guardrail_softened",
    "phase_guardrail_suppressed",
]

class IndicatorsBlock(BaseModel):
    model_config = ConfigDict(validate_assignment=True, frozen=True, strict=True)
    price: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema100: Optional[float] = None
    ema200: Optional[float] = None
    rsi14: Annotated[Optional[float], Field(default=None, ge=0.0, le=100.0)] = None
    slope_ema20_10d: Optional[float] = None
    slope_ema50_20d: Optional[float] = None
    slope_ema200_40d: Optional[float] = None
    cross_ema20_ema50: Optional[Literal["above", "below", "touched"]] = None

class WeeklyIndicators(BaseModel):
    model_config = ConfigDict(validate_assignment=True, frozen=True, strict=True)
    weekly_ema50: Optional[float] = None
    weekly_ema200: Optional[float] = None
    sample_size: Annotated[int, Field(ge=0, le=520)] = 0

class QualityBlock(BaseModel):
    model_config = ConfigDict(validate_assignment=True, frozen=True, strict=True)
    sample_size: Annotated[int, Field(ge=0)] = 0
    weekly_sample_size: Annotated[int, Field(ge=0, le=520)] = 0
    l0_available: bool = False
    l1_available: bool = False
    status: Literal["ok", "degraded"] = "ok"
    limitations: list[str] = Field(default_factory=list)

class MidtrendCompass(BaseModel):
    """midterm trend compass v1 contract."""
    model_config = ConfigDict(validate_assignment=True, frozen=True, strict=True)

    # 身份
    compass_version: Literal["1.0"] = "1.0"
    code: Annotated[str, Field(min_length=1, max_length=16)]
    name: Optional[str] = None
    market: Literal["cn"] = "cn"
    subject_type: SubjectType
    as_of_trade_date: date
    calculated_at: datetime
    bar_status: BarStatus
    stale_since: Optional[date] = None   # 仅在 bar_status="stale"/"suspended" 时填
    adjust: Literal["qfq"] = "qfq"

    # 质量
    quality: QualityBlock

    # 指标
    indicators: IndicatorsBlock
    weekly_indicators: WeeklyIndicators

    # 结构
    weekly: L0Status
    annual: L1Status
    segment: L2Status
    rhythm: L3Status
    phase: Phase
    observe_horizon: Literal["1w", "2w", "1m"]   # 与 phase 派生，不允许外部覆盖
    position_filter: Literal["full", "half", "none"]  # L0 派生日仓位上限语义

    # 动作
    action_bias: CompassAction
    action_reason: list[ActionReasonCode] = Field(default_factory=list)

    # 较昨日
    vs_previous: Optional["VsPrevious"] = None

    # 风险与免责声明
    risks: list[str] = Field(default_factory=list)
    disclaimer: str = "本模块不预测短期价格；分批与执行窗不在本模块范围。"
```

### 8.2 `VsPrevious`

```python
class VsPrevious(BaseModel):
    model_config = ConfigDict(validate_assignment=True, frozen=True, strict=True)
    previous_trade_date: date
    previous_phase: Phase
    previous_action: CompassAction
    phase_change: Literal["up", "down", "flat"]
    l2_change: Literal["up", "down", "flat"]
    l0_change: Literal["up", "down", "flat"]
```

仅与最近一次 `closed` 快照对比；缺失则 `vs_previous=null`，短卡「较昨日」字段渲染为 `—`。

### 8.3 快照键

- 主键：`(code, as_of_trade_date, bar_status)`
- 同一 `(code, trade_date)` 多次写入：`closed` 覆盖 `intraday_unconfirmed`；其它以 `version` 自增并存，仅供回溯不参与改写。
- 存储落 `analysis_history.context_snapshot.midtrend_compass`（与现有 context snapshot 同位置，**不**新建独立表）。

### 8.4 schema 迁移策略

- `compass_version: Literal["1.0"]` 锁版本；新增字段时升 `1.1`，旧记录保留但 `dashboard` 标注 `compass_version=1.0`。
- 任何破坏性变更（L0/L1/L2/L3 枚举值、phase 优先级、改写表）必须升 major 并写迁移说明，旧快照不再驱动改写，仅做历史回溯。

---

## 九、接入现有项目的落地清单

| 位置 | v2 工作 |
|---|---|
| 新建 `src/schemas/compass.py` | Pydantic v2 模型（§8.1） |
| 新建 `src/services/compass/engine.py` | 纯计算：EMA / RSI Wilder / L0/L1/L2/L3 / phase 合成 |
| 新建 `src/services/compass/rewriter.py` | 改写器（§4.5.2），含与现有 Guardrail 的合并语义 |
| 新建 `src/services/compass/action_mapper.py` | CompassAction → DecisionAction / InvestmentConclusion.action 映射 |
| 新建 `src/services/compass/snapshot.py` | 与 `analysis_history.context_snapshot` 集成；读取最近 `closed` 快照 |
| 新建 `src/services/compass/i18n.py` | 中英文标签；与 `src/report_language.py` 同源 |
| 新建 `src/services/compass/formatter_short.py` | 短卡渲染（§3.1） |
| 新建 `src/services/compass/formatter_long.py` | 长卡渲染（§3.2） |
| 新建 `strategies/midterm_compass.yaml` | `default_active=false`、`market_regimes=["trending_up","transitioning"]`、`core_rules=[1,2,3]`、`required_tools=[get_daily_history, get_weekly_history]` |
| 修改 `src/core/pipeline.py` | 在 `AnalysisContextPack` 组装阶段调用 `compass.engine.compute()`；在改写阶段调用 `compass.rewriter.rewrite()` |
| 修改 `src/analyzer.py` Prompt | 增加罗盘字段段；引用 `phase` / `l2` / `l0`；禁止模型覆盖改写后的 `action_bias` |
| 修改 `src/notification.py` | 短卡渲染走 `compass.formatter_short`；长卡走 `compass.formatter_long`；index 区在个股前 |
| 修改 `src/storage.py` | `analysis_history.context_snapshot` 透传 `midtrend_compass`；`save_*` 兼容旧字段 |
| 修改 `apps/dsa-web/` | 手动分析返回 `phase` / `action` / `action_reason`；不写 history（cron 独享） |
| 修改 `apps/dsa-desktop/` | 与 Web 同 schema |
| 修改 `bot/` | 短卡命令复用 `notification_routing` |
| 修改 `src/core/market_review.py` | 大盘复盘走同一罗盘引擎；动作档位换为「观察三档」 |
| 修改 `src/core/market_analyzer.py` | 不动数据获取，只在最后阶段注入罗盘块 |
| 修改 `src/scheduler.py` | 不引入新任务；罗盘跟随现有 `WATCHLIST_ANALYSIS_TIME` / `MARKET_REVIEW_TIME` |
| 新增 `tests/test_compass_engine.py` | 阶段合成表、缺层退化、平局裁决 |
| 新增 `tests/test_compass_rewriter.py` | 改写表全量覆盖 + Guardrail 合并 |
| 新增 `tests/test_compass_action_mapper.py` | 三档 → 8 档 / 6 档映射 |
| 新增 `tests/test_compass_snapshot.py` | 同日 `closed` 覆盖 `intraday_unconfirmed`；缺昨日处理 |
| 新增 `tests/test_compass_i18n.py` | zh/en 标签一致性 |
| 修改 `scripts/ci_gate.sh` | 增加 `pytest -k compass`（含 icontract 慢速契约测试） |
| 修改 `.github/workflows/type-safety.yml` | `mypy --strict-equality` / `pyright` 覆盖 `src/services/compass/`、`src/schemas/compass.py` |
| 修改 `.env.example` | 若引入新配置项（如 `COMPASS_ENABLED=true`、`COMPASS_LIVE_BATCH_ENABLED=false`），同步更新 |

---

## 十、分期交付

### P1 可运行的日线核（最小可用）

- 日线三层 + 阶段 + 次新规则 + 单测
- 命令行能打出一只 A 股股票 / ETF / 指数
- 不接 Web / Bot / 通知
- CI 通过；`scripts/ci_gate.sh` 含新测试

### P2 周线过滤 + 动作改写 + Guardrail 合并

- 周线 fetcher 复用 / 扩展现有实现，不引入新源
- 改写表（§4.5.2）全量覆盖
- 与 `phase_decision_guardrail` / `daily_market_context_guardrail` 合并语义落地
- `action_reason` 结构化 reason code

### P3 接入日更 + 通知

- `AnalysisContextPack` 注入 `midtrend_compass`
- 收盘快照 + 较昨日
- 摘要短卡 + 完整长卡
- 大盘复盘复用同一引擎

### P4 盘中 Web/API + Agent skill + 护栏禁词

- `bar_status=closed/intraday_unconfirmed` 区分
- Web 手动分析返回罗盘
- Bot 短卡命令
- 桌面端渲染

### P5 不做进本期

- 60 分钟分批建议
- 流动性硬过滤
- 4 小时执行层
- Backtest 反向验证通道（保留 `src/core/backtest_engine.py` 接入位，但不实现）
- 跨市场（港股 / 美股）
- 跨策略（替换 `bull_trend` 默认基线）

> 若以后做执行层，**先读日线 L2**：L2 未坏，短周期反向不当反转。

---

## 十一、验收标准

通过不看「是否猜中未来一周」，看下面这些：

### 11.1 功能验收（手工 + 单测）

1. 你认为仍在 1–3 个月波段里的重仓股，L2 不应无故变成 `broken`
2. 均线缠绕票不应标成 `trend_expanding`
3. 回踩日线 EMA50 应是 `resting` + watch，不应是 sell
4. 次新股没有 buy 终态，也没有 `trend_expanding`
5. 盘中结果带 `bar_status=intraday_unconfirmed`，且无 buy
6. 周线大结构偏空时，摘要不得出现 buy
7. 缠论段落与罗盘数字可以并存，但互不改写
8. 推送短卡一行能读完：阶段、主段、动作、较昨日、确认状态
9. `vs_previous` 与最近 `closed` 快照对比；缺失渲染为 `—`
10. 多语言：相同输入下 zh / en 标签对照一致

### 11.2 防御层验收（CI 阻断）

11. `mypy` / `pyright` 在 `src/services/compass/` 与 `src/schemas/compass.py` 严格模式通过
12. `icontract` 契约测试在 `ICONTRACT_SLOW=true` 下通过，覆盖：
    - EMA 公式、RSI Wilder 公式
    - 阶段优先级表（§4.3）7 条规则全量
    - 改写表（§4.5.2）14 条
    - 字段质量退化路径
13. Pydantic v2 schema 在 I/O 边界校验通过；畸形输入解析期 422
14. `scripts/ci_gate.sh` 增量测试通过

### 11.3 集成验收

15. `phase_decision_guardrail` + `daily_market_context_guardrail` + `compass_rewriter` 三者叠加，最保守结果生效
16. 罗盘输出可独立生效（不依赖 LLM 初稿）
17. 同 `(code, trade_date)` 多次写入：`closed` 覆盖 `intraday_unconfirmed`
18. `analysis_history.context_snapshot.midtrend_compass` 在历史详情可回看

### 11.4 文档与变更

19. `docs/CHANGELOG.md` `[Unreleased]` 扁平条目覆盖本次变更
20. `.env.example` 与 `docs/*.md` 与实际一致
21. 报告 / Web / Desktop 变更附 PR 前后截图

---

## 十二、工作定义（写进文档首页）

> 本模块是 A 股千万级波段资金的中期趋势罗盘。
> 周线过滤仓位上限，日线判断趋势是否仍在、量级是数周到数月。
> 系统可以改写买入/观望/卖出，但改写目的是降频、挡住不该买、避免休整被洗出，不是加密交易。
> 1 周不是预测窗，只是执行窗；1 个月才是主观察窗。
> 4 小时和 8 小时不决定方向。
> 本模块不替换 `bull_trend` 默认基线；启用由用户在策略设置中显式选择。

---

## 十三、待确认项（2026-09-11 maintainer 决策已冻结，除第 8 条外全部确认）

下列规则在原方案里被作者单方面锁为默认，本方案 v2 把它们回退为**待确认**，需要 maintainer 在 PR review 中显式确认或修改后才能进入冻结。2026-09-11 maintainer 逐条答复如下，除第 8 条外已冻结为 P2 实施基准；改写实现不得偏离以下决策：

1. **周线过滤偏空时，个股终态上限 —— 🔧 分级（已确认）**  
   - 仅 L0=`weekly_bear` 时禁用 buy；L0=`weekly_transition` 仅降级 confidence，不封顶终态。

2. **L1 空头 + L2 空头 alive 时的默认动作 —— ✅ 采纳（已确认）**  
   - 默认「卖出」；L3 已 exhausted 时降为「观望」。

3. **大盘复盘复用同一罗盘引擎 —— 🔧 部分复用（已确认）**  
   - 复用 L0 + 日线 phase；动作档位换为「观察三档」，不输出建仓/止损语义。

4. **罗盘默认启用策略 —— ✅ 默认关（已确认）**  
   - `default_active=false`，用户在策略设置中自行开启。

5. **新配置项命名（已确认）**  
   - `COMPASS_ENABLED=true|false`、`COMPASS_LIVE_BATCH_ENABLED=false`、`COMPASS_BLOCK_BUY_ON_WEEKLY_BEAR=true`。  
   - 确认后方可写入 `.env.example` 与 `src/core/config_registry.py`。

6. **i18n 语种范围 —— 一期仅 zh / en（已确认）**  
   - 繁中在 P3 通知渠道落地时再评估。

7. **Web 手动分析是否写 history —— ❌ 仅 cron 写（已确认）**  
   - Web 手动分析不落地罗盘快照，避免试错调参污染回溯数据。

8. **Backtest 接入时间点 —— 待定（非 P2 阻塞）**  
   - 一期不做；建议窗口为 P3 通知渠道上线后、P4 盘中接入前启动，样本与 KPI 沿用 `tests/scoring/` 现有回测框架口径。

### 13.8 日线 L4 择时信号（2026-09-12 maintainer 决策已冻结）

一期在罗盘上叠加日线级择时信号，冻结决策如下：

1. **章程改写**：本模块不提供无约束的短期价格预测；择时信号 = 条件触发的交易计划（触发价 + 失效价 + 条件说明），受趋势结构门控。免责声明同步更新。
2. **数据源**：`fetcher.fetch_daily_ohlcv` 直接取 OHLCV（零额外成本），不复用 closes 序列再拼接。
3. **缠论信号**：一期不做，罗盘自算指标独立出信号（`engine.derive_l4`，`compute()` 签名不变）。
4. **抄底定义**：RSI 超卖（<30）+ 底背离（确认分形或候选低点，RSI 抬升 > 0.5）+ 止跌（收阳且收盘 ≥ (high+low)/2）；`weekly_bear` 下可出明确买入信号，但仓位提示固定为「轻仓」，属逆势博弈仓，与趋势仓位分离；reason codes 携带 `bottom_fishing_time_stop`（5 个交易日时间止损）+ `weekly_bear_bottom_fishing_pass`（rewriter §13.1 修正案：weekly_bear 仅放行 bottom_fishing 的 buy，其余买入照常否决；放行只解除 L0 周线否决，row 5/6/7 等其余硬约束（年线样本不足/收敛/疲惫阶段）照常生效，即「放行 ≠ 保证买入」）。
5. **一期仅展示**：信号渲染在长卡第 9 节与 Web 择时卡片，不进 pipeline 改写链、不落盘快照。
6. **信号形态**：确认接受「触发价 + 失效价 + 条件说明」；armed 状态无触发/失效价，仅展示条件。
7. **信号类型**：`pullback_entry`（顺势回踩：近 5 日 low 触及 EMA20±1% 且 RSI 复位 40-55 且收复 EMA20 且斜率 > 0；仓位上限 full(bull)/medium）、`bottom_fishing`（见第 4 条）、`top_escape`（RSI>75+斜率<0 / RSI>70+顶背离 / 跌破 EMA20+斜率<0；全多头 shielded 结构下不输出）。
8. **开关**：`COMPASS_TIMING_ENABLED`（默认 false，仅 cron/手动演示启用）；schema 增量字段 `MidtrendCompass.timing: list[TimingSignal]`（`compass_version` 不变，追加字段兼容）。切换后需重启 API 进程当日生效（罗盘结果按标的当日缓存）；`derive_l4(timing_enabled=...)` 函数级默认值亦为 false，调用方必须显式开启。top_escape 触发时按命中路径输出变体 reason code（`top_escape_exhaustion` / `top_escape_divergence` / `top_escape_ema_loss`，可并存）。

---

## 十四、三层防御契约要点（强制）

本模块按 `docs/type-contract-data-defense.md` 落地三层防御。

### 14.1 Layer 1 类型（mypy / pyright）

- 所有公开函数必须加类型注解；禁止裸 `tuple`/`dict`/`list`；`Any` 必须收窄。
- 跨模块循环引用用 `TYPE_CHECKING` + 字符串注解。
- `src/schemas/compass.py` 与 `src/services/compass/*.py` 在 `pyrightconfig.json` / `pyproject.toml` 注册为严格模块。
- 数值统一 `Decimal`（金融场景，参见 defense 文档示例）。

### 14.2 Layer 2 契约（icontract）

下列函数必须加 `@require` / `@ensure`：

- `compute_ema(closes, period)`：输入非空、长度 ≥ period、period ≥ 1
- `compute_rsi_wilder(closes, period=14)`：输入非空、长度 ≥ period+1、结果 ∈ [0, 100]
- `derive_l0(weekly_closes, ema50, ema200)`：输入单调递增日期、长度 ≥ 30
- `derive_l1(daily_closes, ema200, slope_40d)`：长度 ≥ 220 时 L1 必为非 disabled
- `compose_phase(l0, l1, l2, l3)`：按 §4.3 七条短路求值；缺层走退化路径
- `rewrite_action(compass_state, llm_draft)`：返回 `final_action ∈ {buy, watch, sell}`、`reason_codes` 与状态一致
- `action_mapper(compass_action)`：返回映射三元组一一对应

契约测试文件 `tests/test_compass_contracts.py`，CI 用 `ICONTRACT_SLOW=true` 跑。

### 14.3 Layer 3 数据（Pydantic v2）

- 所有罗盘 I/O 边界走 `src/schemas/compass.py` 模型；`model_config = ConfigDict(strict=True, frozen=True, validate_assignment=True)`。
- `Literal` 枚举强约束；`Annotated[..., Field(ge=..., le=..., pattern=...)]` 字段级约束。
- 畸形输入解析期直接 422；不允许默默 `default=None`。
- §8.1 的 schema 是冻结契约；扩展字段必须升 `compass_version`。

---

## 十五、观测、回滚与失败模式

### 15.1 观测

- 每次改写必须输出 `action_reason_codes[]`，落到 `analysis_history.context_snapshot.midtrend_compass`。
- 日志统一结构：`compass.compute(code, trade_date, bar_status) → phase=..., action=..., reason=[...]`。
- 推荐加 dashboard 统计：阶段分布、改写占比、最常触发的 reason code Top 5。

### 15.2 回滚

- 代码层：常规 git revert；本模块不修改数据库 schema，所有快照都在 `analysis_history.context_snapshot` JSON 字段里。
- 配置层：`COMPASS_ENABLED=false` 全局关闭；策略层 `default_active=false` 默认不启用。
- 数据层：若 schema 升级失败，旧快照保留 `compass_version=1.0`，dashboard 标注「旧版本，不参与改写」。

### 15.3 已知失败模式

| 模式 | 描述 | 缓解 |
|---|---|---|
| 数据缺失 / fetch_failed | 单源失败后 fallback 仍失败 | `data_missing` reason，强制 watch |
| 周线样本不足 | < 60 根周 K | `weekly_disabled`，L0 不参与改写 |
| 改写器过保守 | `weekly_transition` 屏蔽所有 buy，错过右侧 | 收集 90 天改写 vs 实际收益报告；review 后再放宽 |
| 改写器与 Guardrail 冲突 | 大盘保守 + 罗盘买入 | `daily_market_context_guardrail` 先于罗盘改写器；最保守结果生效 |
| phase 抖动 | 短期均线上穿下穿导致 phase 在 `trend_tiring` 与 `trend_holding` 反复 | `phase` 仅在 `closed` 快照更新；盘中只显示不写入 |
| 改写后未与 LLM 同步 | LLM 输出仍写「建议买入」 | Prompt guardrail 强制模型读 `action_bias`，禁止覆盖 |

---

## 十六、参考与索引

- 三层防御：`docs/type-contract-data-defense.md`
- AnalysisContextPack：`docs/analysis-context-pack.md`、`src/schemas/analysis_context_pack.py`
- 决策档位：`src/schemas/decision_action.py`、`src/schemas/investment_conclusion.py`
- Guardrail：`src/daily_market_context_guardrail.py`、`src/phase_decision_guardrail.py`
- 交易日历：`src/core/trading_calendar.py`
- 通知路由：`src/notification_capabilities.py`、`src/notification_routing.py`
- 调度与锁：`docs/scheduled-watchlist-market-review-plan.md`、`src/core/scheduled_task_lock.py`
- 现有默认策略：`strategies/bull_trend.yaml`、`src/agent/skills/defaults.py`
- AI 协作治理：`AGENTS.md`、`scripts/check_ai_assets.py`
