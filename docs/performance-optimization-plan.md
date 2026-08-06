# 性能优化方案（实测驱动 · 单股 dry-run 场景）

> 状态：方案草案，待评审
> 采样日期：2026-06-23
> 语言：中文（英文版按需后续同步）
> 关联模块：`main.py`、`src/core/market_review.py`、`src/market_analyzer.py`、`data_provider/base.py`、`data_provider/akshare_fetcher.py`、`src/search_service.py`
> 采样方法：`cProfile` + `pstats`（`py-spy` 在 macOS SIP 下需 root，已用 `cProfile` 等价替代）
> 采样样本：`python main.py --stocks 600519 --dry-run`（未配置 `TUSHARE_TOKEN` / `TAVILY_API_KEYS` / LLM Key，单股）

本文档是基于 **2026-06-23 实测采样**的性能优化设计真源。所有优先级判断来自 `cProfile` 数据，不是代码模式推断。实现时每阶段需同步更新 `docs/CHANGELOG.md` 的 `[Unreleased]` 段（扁平格式）与本文件。

> **方向变更说明**：本方案经历一次根本性收敛——从「凭代码模式猜热点（搜索并发、pandas copy、df.copy 等）」转向「以实测为准」。第一版清单中的 10 项里，在本次采样场景下有 **4 项明确不是热点**，被标记为不做项；真正热点集中在大盘分析链路与全市场快照。

---

## 1. 概述

### 1.1 背景

历史性能评估基于代码阅读 + 启发式判断（如「串行变并发」、「减少 df.copy」、「加缓存」），未做测量。2026-06-23 对单股 dry-run 做了首次 `cProfile` 采样，结论与此前推断差距显著，需要据此重写优化方案。

### 1.2 核心原则

1. **Measure first**：任何性能改动前，必须先有 `cProfile` 或等价采样证据。不基于代码模式推断热点。
2. **场景化**：不同场景（单股 dry-run / 单股完整 / 多股全量 / `/analyze` API / 告警轮询）热点不同。方案必须标注适用场景，不混淆。
3. **最小改动**：优先选择「改动小、收益大、风险低」的项；大改动（如全链路 async 改造）暂缓。
4. **不破坏契约**：所有方案需评估对 CLI 行为、API 行为、报告结构、数据源 fallback、通知链路的影响，保证向前兼容。

### 1.3 目标

本次采样场景（单股 dry-run，无 Key）下：

| 指标 | 当前 | 目标 |
|---|---|---|
| 单股 dry-run 总耗时 | 79.7s | < 10s |
| 大盘分析在单股命令中的占比 | 89%（71/79.7s） | 0%（默认不跑）或可配置 |
| 重复全市场快照次数 | N 次（多流程各自抓） | 1 次后内存共享 |

### 1.4 范围

- **P0~P4**：本方案覆盖单股 dry-run 场景的全部实测热点。
- **不在范围**：完整 LLM 分析、多股全量、API 同步模式、告警 / 组合快照路径的实测——需另起采样任务。

---

## 2. 实测证据（2026-06-23）

### 2.1 整体耗时分布

总耗时 **79.7s**（wall clock），其中 CPU 时间仅 8s，其余为 IO 等待与主动 sleep。

| 路径 | cumtime | 占比 |
|---|---:|---:|
| `run_market_review` | 71.1s | **89%** |
| ├─ `_get_market_statistics` → `akshare.get_market_stats` | 37.0s | 46% |
| │  └─ `akshare.stock_zh_a_spot`（全市场快照） | 24.3s | 30% |
| │  └─ `_enforce_rate_limit` × 2 | 6.4s | 8% |
| ├─ `_get_sector_rankings` | 17.2s | 22% |
| ├─ `_get_main_indices` | 8.7s | 11% |
| └─ `search_market_news` + LLM + 渲染 | ~8s | 10% |
| `pipeline.run`（单股数据拉取 + 指标计算） | **3.76s** | 5% |
| 模块 import + 初始化 | ~5s | 6% |

### 2.2 自身耗时 Top 5（tottime，不含子调用）

| 函数 | tottime | 占比 | 说明 |
|---|---:|---:|---|
| `time.sleep`（rate-limit + random_sleep） | **36.3s** | 46% | `random_sleep` 25s + `_enforce_rate_limit` 18s |
| `socket.recv_into` | 10.8s | 14% | 网络读取响应 |
| `_thread.lock.acquire` | 5.8s | 7% | 线程锁等待 |
| `SSL.do_handshake` | 5.8s | 7% | TLS 握手 |
| `akshare/utils/demjson.*` | ~5s | 6% | akshare 内部纯 Python JSON 解析，被调 1000 万+ 次 |

### 2.3 关键观察

1. **单股 dry-run 本身只要 3.76s**——`pipeline.run` 完整链路（行情、筹码、基本面、指标计算、历史补齐）合计 3.76 秒。
2. **89% 的耗时来自被顺带触发的大盘分析**——`--stocks 600519` 命令默认会跑完整 `run_market_review`，与「单股」语义错位。
3. **`_calc_market_stats` 自身只用 40ms**——37 秒全部花在「抓全市场快照」上，本地计算可忽略。
4. **主动 sleep 占 46%**——rate-limit 参数可能过保守，或触发条件可优化。

---

## 3. 第一版清单事后核对

第一版基于代码模式列出的 10 项「问题」，本次采样后核对如下：

| # | 第一版方案 | 实测结论 | 处理 |
|---:|---|---|---|
| 1 | 搜索维度串行执行 | 未配 Tavily，搜索路径整块跳过 | **待测**（需配 Key 重采） |
| 2 | 单股 4 路并发 | 单股总共 3.76s，并发收益 < 2s | **不做** |
| 3 | 主循环 sleep | `analysis_delay` 默认 0，未触发 | **待测**（多股全量场景） |
| 4 | 组合快照 N+1 | 不在 CLI 路径 | **待测**（API 场景） |
| 5 | 告警 worker N+1 | 不在 CLI 路径 | **待测**（bot 路径） |
| 6 | pandas df.copy × 3 | `_calc_market_stats` 自身 40ms | **不做** |
| 7 | `_augment_historical_with_realtime` | 未进 top-30 | **不做** |
| 8 | `_select_best_bars` 重复查库 | 未进 top-30 | **不做** |
| 9 | API `/analyze` 缓存 | 不在 CLI 路径 | **待测**（API 场景） |
| 10 | 搜索排序链路无缓存 | 搜索未跑 | **待测** |

**结论**：10 项中 **4 项明确不做**（#2、#6、#7、#8），**5 项需另场景采样**（#1、#3、#4、#5、#9、#10），**0 项是当前场景热点**。第一版判断方向跑偏，本次方案据此重写。

---

## 4. 修正后的优先级清单

### P0 — `--stocks` 单股命令默认不触发完整大盘分析

**问题**
`main.py --stocks 600519 --dry-run` 触发了完整 `run_market_review`（71.1s），占 89% 耗时。单股命令的语义是「分析这一只股票」，顺带跑完整大盘复盘属于超出意图。

**证据**
- `main.py:607(run_full_analysis)` → `main.py:429(_run_market_review_with_shared_lock)` → `src/core/market_review.py:132(run_market_review)` cumtime 71.1s
- 用户意图与实际行为错位：CLI 里 `--stocks` 与 `--market-review` 是两个独立 flag，但前者默认触发后者。

**设计**
1. 调研：确认 `run_full_analysis` 里触发 `run_market_review` 的条件（默认 True？还是 config 驱动？）。
2. 改造：`--stocks` 单股命令下，默认 `skip_market_review=True`；需要大盘数据时显式 `--with-market-review` 或走 `--market-review` 命令。
3. 兼容：保留现有 `--market-review`、`--schedule`、Web API 触发路径不变；只改 `--stocks` 默认。
4. 日志：启动时打印当前模式（`mode=stock_only` / `mode=stock_with_market_review`），便于排障。

**预期收益**
单股 dry-run 从 79.7s → ~8s（**~10x**）。

**验证**
- `python main.py --stocks 600519 --dry-run` 耗时 < 10s
- `python main.py --stocks 600519 --dry-run --with-market-review` 仍跑完整大盘
- `python main.py --market-review` 行为不变
- 现有测试（`tests/`）+ CI `backend-gate` 通过

**风险**
- 若有用户依赖「单股命令顺带出大盘报告」的旧契约，会感知到变化。
- 缓解：在 `docs/CHANGELOG.md` 标注为「改进」，并在 CLI `--help` 文案里说明 flag 含义。

**回滚**
还原 `run_full_analysis` 里对 `skip_market_review` 的默认取值即可。

---

### P1 — 全市场快照内存共享缓存

**问题**
`akshare.stock_zh_a_spot()` 单次抓取全市场 5000+ 股票快照耗时 24.3s。该快照被 `get_market_stats` 消费，但多流程（大盘分析、组合快照、告警评估）可能各自抓取，重复浪费。

**证据**
- `data_provider/akshare_fetcher.py:1752(get_market_stats)` cumtime 37.0s
- 其中 `akshare.stock_zh_a_spot` 24.3s（自身 0.007s + 网络 + akshare 内部 demjson 解析）
- `_calc_market_stats` 仅 0.04s（纯本地计算）

**设计**
1. 在 `DataFetcherManager` 或 `AkshareFetcher` 内增加 `_market_snapshot_cache: Optional[pd.DataFrame]` + `_market_snapshot_ts: float`。
2. `get_market_stats` 调用前先检查缓存：
   - 缓存有效（TTL 内）：直接返回缓存快照
   - 缓存失效或为空：抓取后写入缓存
3. TTL 默认 60 秒（可配置：`MARKET_SNAPSHOT_CACHE_TTL_SEC`），新增项需同步 `.env.example`。
4. 缓存粒度：**整张全市场快照**，不是单股；所有下游消费方共享。
5. 线程安全：用 `threading.Lock` 保护缓存读写，避免多 worker 并发时重复抓取。

**预期收益**
- 大盘分析路径：单次调用省 24s 后续重复
- 多股全量场景：N 股各自调用 `get_realtime_quote`，若走快照路径可共享同一份数据
- 组合快照 + 告警：共享缓存后 N+1 → 1

**验证**
- 单元测试：连续两次 `get_market_stats`，第二次应命中缓存（mock `stock_zh_a_spot`，断言只调一次）
- TTL 过期后应重新抓取
- 多线程并发调用下不重复抓取（用 `threading.Barrier` 触发并发）

**风险**
- TTL 过长会导致数据陈旧（盘中用户期望实时价）。
  - 缓解：TTL 设为可配置；盘中 vs 盘后用不同 TTL（如盘中 30s，盘后 300s）。
- akshare 接口字段变化时缓存内 DataFrame 可能过期。
  - 缓解：缓存层只存原始 DataFrame，字段解析放在消费侧。

**回滚**
关闭缓存配置项（TTL=0）即回退到每次抓取。

---

### P2 — rate-limit sleep 参数评估与令牌桶化

**问题**
`random_sleep`（25s）+ `_enforce_rate_limit`（18s）合计 **43 秒主动 sleep**，占总耗时 46%。这些是防数据源限流的保护性 sleep，但参数可能过保守。

**证据**
- `data_provider/base.py:549(random_sleep)` 被调 8 次，合计 25.06s
- `data_provider/akshare_fetcher.py:422(_enforce_rate_limit)` 被调 5 次，合计 17.99s
- 平均每次 sleep ~3s

**设计**
1. **先调研**（P2-1）：读 `akshare_fetcher.py:422` 与 `base.py:549`，确认：
   - `min_interval` / `max_jitter` 的当前取值
   - 触发条件（无条件 sleep？还是仅失败重试？）
   - 是否区分数据源（akshare / efinance / tushare 应有不同策略）
2. **参数调优**（P2-2）：基于调研结果，把过保守的参数下调。
3. **令牌桶化**（P2-3，可选）：把固定 sleep 改为令牌桶——
   - 单位时间（如 1 秒）最多 N 次请求
   - 超出时排队等待，而不是每次都 sleep
   - 仅在真实收到 429 / 限流响应时触发指数退避

**预期收益**
- 若能把 43s 砍到 20s，大盘分析从 71s → ~48s（P0 不做时的收益）
- 与 P0 叠加后，大盘分析场景整体提速

**验证**
- 调研阶段产出文档：当前参数表 + 触发条件
- 改造后对比：同样 5 次调用，sleep 总耗时下降，且不触发 429
- 长时间运行稳定性测试（`pytest -m network`）

**风险**
- 参数过激进会触发数据源 ban（akshare/eastmoney 反爬）。
  - 缓解：保留 `random_sleep` 的随机性（不要改成固定间隔），并保留失败退避机制。
- 令牌桶改造范围大，先评估，不立即实施。

**回滚**
参数类改动可直接还原；令牌桶若实施，通过开关 `RATE_LIMIT_MODE=fixed_sleep|token_bucket` 控制。

---

### P3 — `get_market_stats` 与 `get_sector_rankings` 并发

**问题**
这两个 API 端点独立，但顺序调用，各自还带 rate-limit sleep。在 P0 不做（仍保留大盘分析）的场景下，这是大盘分析的次大头。

**证据**
- `src/market_analyzer.py:396(_get_market_statistics)` 39.9s
- `src/market_analyzer.py:428(_get_sector_rankings)` 17.2s
- 两者串行，合计 57s

**设计**
1. 前置验证：`AkshareFetcher` 的线程安全性（`_enforce_rate_limit` 是否用了共享计数器？session 是否线程安全？）
2. 用 `concurrent.futures.ThreadPoolExecutor(max_workers=2)` 并发拉 stats 和 rankings
3. 失败语义不变：一个失败不影响另一个（现有 fallback 链路保留）
4. 仅在 P0 未做或用户显式开启大盘分析时生效

**预期收益**
大盘分析 -17s（从 71s → ~54s）。

**验证**
- 单元测试：并发调用下两个结果的正确性
- 实测对比：采样前后 `run_market_review` cumtime
- 线程安全验证：并发下无竞态（共享状态用锁保护）

**风险**
- **前置硬伤**：若 `AkshareFetcher` 非线程安全，并发会引入竞态。
  - 缓解：**先验证**，不验证清楚不动手。
- rate-limit 计数器在并发下可能错乱（两个线程同时抓 → 突破 QPS 限制）。
  - 缓解：rate-limit 用进程级锁保护。

**回滚**
改回串行调用即可。

---

### P4 — SearXNG 公共实例探测失败后短期标记不可用

**问题**
未配置 SearXNG / Tavily 时，仍然尝试拉取公共 SearXNG 实例 3 次，合计 5s。每次都失败（无可用实例）。

**证据**
- `src/search_service.py:3842(SearXNG 搜索失败)` 被记录 3 次
- `search_market_news` cumtime 5.01s

**设计**
1. `SearXNGSearchProvider.is_available` 在首次探测失败后，TTL 内（如 300s）标记为不可用
2. TTL 过期后再次探测，避免永久不可用
3. 仅针对「公共实例探测失败」场景，不影响用户显式配置的私有 SearXNG 实例

**预期收益**
- 大盘分析 -5s
- 未配 Tavily 的部署环境普遍受益

**验证**
- 单元测试：首次失败后 TTL 内不再探测
- TTL 过期后恢复探测
- 配置了私有实例时行为不变

**风险**
- TTL 过长导致短暂网络抖动期间搜索能力被误关。
  - 缓解：TTL 设为 300s，且只针对「无可用实例」错误，其他错误（如超时）不标记。

**回滚**
关闭探测失败缓存即可。

---

## 5. 明确不做项（放弃清单）

以下在第一版方案中列出的项，在本次采样场景下**明确不是热点**，不做：

| # | 放弃项 | 放弃理由 |
|---:|---|---|
| 不做-1 | 单股 4 路数据并发（第一版 #2） | 单股 `pipeline.run` 总共 3.76s，并发后收益 < 2s，且引入嵌套线程池复杂度 |
| 不做-2 | pandas MA/MACD/RSI 合并 copy（第一版 #6） | `_calc_market_stats` 自身 40ms，全市场快照抓取才是瓶颈 |
| 不做-3 | `_augment_historical_with_realtime` pandas 反模式（第一版 #7） | 未进 top-30，单股路径总耗时已很小 |
| 不做-4 | `_select_best_bars` 多候选查库（第一版 #8） | 未进 top-30，Agent 模式下才触发，本次场景不涉及 |
| 不做-5 | 全链路 async 改造 | 改动量过大，且当前瓶颈是 sleep 与网络 IO，async 收益有限 |

这些项如果未来在**其他场景**（完整 LLM 分析、多股全量、API）被采样证明是热点，再单独起方案，不在本方案范围内。

---

## 6. 待测场景与后续采样计划

本方案结论严格只对「单股 dry-run，无 Key」场景成立。以下场景需另起采样任务：

| 场景 | 命令 / 路径 | 关注点 | 对应第一版方案 |
|---|---|---|---|
| 单股完整分析 | `python main.py --stocks 600519`（带 LLM Key） | LLM 调用、prompt 拼装、报告生成 | #1（搜索）、新增（LLM） |
| 多股全量 dry-run | `python main.py --stocks 600519,000001,... --dry-run`（5~20 股） | 并发池行为、`analysis_delay` sleep、N+1 | #3（主循环 sleep） |
| 配了 Tavily 的单股 | 同上 + `TAVILY_API_KEYS` | 搜索维度并发、排序链路 | #1、#10 |
| `/analyze` API 同步模式 | `POST /api/v1/analyze` | HTTP 缓存、结果复用、并发模型 | #9 |
| 告警 / 组合快照轮询 | bot worker 长跑 | N+1、manager 复用 | #4、#5 |

**后续采样输出要求**：每次采样产出独立的 `cProfile` `.prof` 文件 + 对应分析报告，按 `docs/perf-sample-<场景>-<日期>.md` 命名，积累成实测证据库。

---

## 7. 实施次序与里程碑

| 阶段 | 内容 | 预估工作量 | 阻塞关系 |
|---|---|---|---|
| M1 | P0 调研 + 改造 + 测试 | 0.5 ~ 1 天 | 无 |
| M2 | P1 设计 + 缓存层 + 单测 | 1 ~ 2 天 | 无 |
| M3 | P2-1 调研（不动手改） | 0.5 天 | 无 |
| M4 | P3 前置验证（线程安全） | 0.5 天 | M4 通过才做 P3 |
| M5 | P3 并发改造 | 1 天 | 依赖 M4 |
| M6 | P4 SearXNG 探测缓存 | 0.5 天 | 无 |
| M7 | P2-2 / P2-3 参数调优（可选） | 1 天 | 依赖 M3 调研结果 |

**M1 先做**：收益最大、改动最小、风险最低。

---

## 8. 验证矩阵

按 `AGENTS.md` 第 6 节，本方案涉及的改动面与验证要求：

| 改动面 | 验证 | 阻断等级 |
|---|---|---|
| Python 后端（`main.py`、`data_provider/`、`src/core/`、`src/market_analyzer.py`、`src/search_service.py`） | `./scripts/ci_gate.sh` + `python -m py_compile <changed>` + `python -m pytest -m "not network"` | 阻断 |
| CLI 行为（`--stocks` 默认不跑大盘） | 手动跑 `--stocks` / `--market-review` / `--with-market-review`，确认行为与日志 | 阻断 |
| 新增配置项（`MARKET_SNAPSHOT_CACHE_TTL_SEC` 等） | 同步 `.env.example`；说明文档同步更新 | 阻断 |
| 数据源 fallback | `pytest -m network` 验证 rate-limit 调整后不触发 ban | 观测 |
| 线程并发改造（P3） | 单测覆盖并发场景；采样对比前后耗时 | 阻断 |

---

## 9. 风险与回滚（总体）

| 风险 | 缓解 | 回滚 |
|---|---|---|
| 用户依赖「单股命令顺带出大盘」的旧契约 | `CHANGELOG.md` 标注；CLI `--help` 文案；保留 `--with-market-review` 兜底 | 还原 `skip_market_review` 默认值 |
| 全市场快照缓存导致盘中数据陈旧 | TTL 可配置；盘中 / 盘后差异化 TTL | TTL=0 关闭缓存 |
| rate-limit 调优触发数据源 ban | 保留随机性；保留失败退避；网络测试观测 | 还原参数 |
| 并发改造引入线程竞态 | 前置验证线程安全；单测覆盖并发 | 改回串行 |

---

## 10. 交付与发布

- **分阶段合入**：每个里程碑（M1~M7）独立 PR，不打包。
- **PR 描述**：必须附采样前后对比（`.prof` 文件 + 关键 cumtime 数字），证明改动有效。
- **`CHANGELOG.md`**：每项改动在 `[Unreleased]` 段按扁平格式追加（`- [改进] ...` / `- [修复] ...`）。
- **文档同步**：本方案文档（`docs/performance-optimization-plan.md`）在每次合入后更新状态；完成项标注「已实现 + 合入 PR 链接」。
- **不发版**：本方案所有改动属于改进，不触发自动 tag（commit title 不带 `#patch` / `#minor` / `#major`），由 maintainer 统一安排发版。

---

## 附录 A — 采样复现步骤

```bash
# 1. 准备环境
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 准备 .env（从 .env.example 复制，可留空 Key）
cp .env.example .env

# 3. 预热（填充数据源缓存，避免首次冷启动噪音）
.venv/bin/python main.py --stocks 600519 --dry-run

# 4. 正式采样
.venv/bin/python -c "
import cProfile, runpy, sys, os
os.chdir('$(pwd)')
sys.path.insert(0, '$(pwd)')
sys.argv = ['main.py', '--stocks', '600519', '--dry-run']
pr = cProfile.Profile()
pr.enable()
try:
    runpy.run_path('main.py', run_name='__main__')
except SystemExit:
    pass
pr.disable()
pr.dump_stats('/tmp/profile_600519_dryrun.prof')
print('Profile saved.')
"

# 5. 可视化（可选）
.venv/bin/pip install snakeviz
.venv/bin/snakeviz /tmp/profile_600519_dryrun.prof
```

## 附录 B — 采样原始数据关键数字

- 总耗时：**79.705s**（wall clock）
- 函数调用总数：81,841,212（其中 primitive calls: 81,274,565）
- `time.sleep` 自身耗时：**36.268s**（12 次调用，平均 3.02s/次）
- `pipeline.run` cumtime：**3.761s**
- `run_market_review` cumtime：**71.094s**
- `akshare.stock_zh_a_spot` cumtime：**24.263s**（1 次调用）
- `_calc_market_stats` cumtime：**0.038s**（真实本地计算）
