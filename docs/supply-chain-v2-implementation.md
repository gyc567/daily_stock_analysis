# 供应链分析报告生成链路 · 深度优化方案 v2（已实施）

## 状态：✅ 已实施并通过 308 测试

实施切片：5 阶段全部完成
- ✅ W1 构造 fake KB fixture + 校准脚本骨架
- ✅ W2 SupplyChainKBRetriever（加权 + 衰减 + cold start）
- ✅ W3 TwoPassExtractor + FieldEnricher + ChainNodeV3
- ✅ W4 统一 SerenityScorer + 重构 fetch_all + 接入 Executor
- ✅ W5 报告骨架契约 + 数据完整度披露 + 文档 + CHANGELOG

---

## 1. 已实施内容

### 1.1 新增模块（6 个文件，约 1500 行）

| 文件 | 职责 |
|---|---|
| `src/services/supply_chain/kb_retriever.py` | 包装 KnowledgeBaseService，加权 + 衰减 + cold start 4 段策略 |
| `src/services/supply_chain/two_pass_extractor.py` | 两轮抽取（实体识别 + 属性补全），含停用词 + 后缀剥离启发式 |
| `src/services/supply_chain/field_enrichment.py` | 公开数据补全（concentration_pct / geographic_distribution），失败降级 |
| `src/services/supply_chain/graph_builder.py` | KB + LLM + 公开数据 → SupplyChainGraph + DataCompleteness |
| `src/services/supply_chain/serenity_scorer.py` | 统一 Serenity 评分（KB_DRIVEN / INDUSTRY_PRIOR 分类 + 上限加成） |

### 1.2 修改文件

| 文件 | 变更 |
|---|---|
| `src/schemas/supply_chain.py` | 新增 ChainNodeV3 / SupplyChainGraph / KBHitRef / DataCompleteness / SupplyChainV2 / SerenityScoreResult |
| `src/services/supply_chain_data_service.py` | 新增 `fetch_all_v2()` + `fetch_all_v2_legacy_compat()`，`fetch_all()` 行为不变 |
| `src/agent/tools/supply_chain_tools.py` | 新增 `search_supply_chain_kb` 工具（注册到 `ALL_SUPPLY_CHAIN_TOOLS`） |
| `src/agent/supply_chain_executor.py` | system prompt 追加「[v2] 知识库参考（第一步必做）」段 |
| `tests/test_supply_chain_services.py` | 工具数 4 → 5 |

### 1.3 新增测试（5 个文件，41 用例）

- `tests/test_supply_chain_v2/__init__.py` — fixture 工厂
- `tests/test_supply_chain_v2/test_schema.py` — Pydantic v2 strict 契约
- `tests/test_supply_chain_v2/test_kb_retriever.py` — 衰减函数 + cold start 4 段
- `tests/test_supply_chain_v2/test_extractor_and_graph.py` — 两轮抽取 + 图谱构建
- `tests/test_supply_chain_v2/test_serenity_scorer.py` — 因子分类 + KB bonus 触发条件
- `tests/test_supply_chain_v2/test_fetch_all_v2.py` — 端到端 + v1 兼容

---

## 2. 关键设计决策

### 2.1 加权公式（kb_retriever）
```
final_score = raw_norm × (tag_weight / 3.0) × stock_match × recency_decay
- tag_weight：tag 命中最高权重（产业链/卡点/瓶颈等）
- stock_match：含 stock_code +1.0，含 stock_name +0.5
- recency_decay：0.5 ** (age_days / 180)
```

### 2.2 Cold Start 4 段
| aggregate_score | tier | confidence_boost | llm_fallback |
|---|---|---|---|
| 0.0 | cold_start | 1.0 | aggressive |
| < 0.3 | sparse | 1.0 | moderate |
| 0.3~0.6 | partial | 1.2 | selective |
| ≥ 0.6 | rich | 1.5 | verify_only |

### 2.3 Serenity 因子分类
| 类别 | 因子 | 特征 |
|---|---|---|
| KB_DRIVEN | chokepoint_severity / expansion_difficulty / supplier_concentration | 文本关键词能直接驱动评分 |
| INDUSTRY_PRIOR | demand_inflection / architecture_coupling / evidence_quality / valuation_disconnect / catalyst_timing | 行业默认驱动 |

KB bonus 上限 0.2，仅在 KB_DRIVEN 因子 + kb_score ≥ 0.6 + kb_relevance ≥ 0.6 触发。

### 2.4 数据完整度披露（v2 关键创新）
报告新增字段 `data_completeness` 含：
- upstream_total / upstream_with_concentration_pct
- downstream_total / downstream_with_concentration_pct
- kb_hit_count / kb_coverage_score / aggregate_confidence

让用户能**一眼看出报告的数据完整度**，而不是只看到 LLM 自信地输出。

---

## 3. 向后兼容性

| 调用方 | 行为 |
|---|---|
| 现有 `SupplyChainDataService.fetch_all()` | **不变**，保持 v1 行为 |
| 现有 `SupplyChainExecutor`（主题报告） | system prompt 追加 KB 强制段，LLM 自动适配 |
| 现有 API 端点 | **不变**，返回结构未破坏 |
| 现有 PDF 生成 | **不变** |

新增能力通过新方法暴露：
- `fetch_all_v2()` → `SupplyChainV2`
- `fetch_all_v2_legacy_compat()` → dict（v1 + v2 字段合并）

---

## 4. 验证矩阵

| 项 | 命令 | 结果 |
|---|---|---|
| v2 测试 | `pytest tests/test_supply_chain_v2/` | **41/41 passed** |
| 旧 supply_chain 测试 | `pytest tests/test_supply_chain_*` | **267/267 passed** |
| 合并 | `pytest tests/test_supply_chain_v2/ tests/test_supply_chain_*` | **308/308 passed** |
| Syntax | `py_compile <changed files>` | OK |
| Lint | `flake8 --max-line-length=120` | 0 错误 |

---

## 5. 未验证项 / 后续 PR 建议

1. **真实 KB 数据回归**：当前 `data/knowledge_base/` 58 个文档里 22 个是 14 字节占位符，无法真实评估 KB 加权效果。建议：
   - 上传 5~10 份真实产业链纪要
   - 跑 `scripts/calibrate_kb_weights.py`（待创建）做 grid search
   - 把权重常量入代码 docstring
2. **公开数据补全的稳定性**：Tushare/Akshare 接口限速时 concentration/geo 完整度会下降，需在生产环境压测
3. **报告章节契约**：v2 让 system prompt 要求「## 7. 知识库参考」和「## 12. 数据完整性披露」章节，但 LLM 生成 Markdown 是自由文本，CI 暂无强制校验。下次 PR 可加契约测试

---

## 6. 回滚方案

每阶段独立可回滚：

| 阶段 | 回滚 |
|---|---|
| Schema | 删除 `ChainNodeV3 / SupplyChainGraph / SupplyChainV2` 等 v2 类，旧 `ChainNode / SupplyChain` 仍在 |
| kb_retriever | 删 `src/services/supply_chain/kb_retriever.py`；system prompt 删 KB 强制段 |
| two_pass_extractor / graph_builder | 删两个文件；`SupplyChainDataService.fetch_all_v2()` 移除 |
| serenity_scorer | 删文件；设 `SERENITY_SCORER_V2=false` 回退旧启发式 |
| fetch_all_v2 | 仅是新增方法，`fetch_all()` 不动 |
| Agent 工具 | 从 `ALL_SUPPLY_CHAIN_TOOLS` 移除 `search_supply_chain_kb_tool` |

最坏情况：`git revert <commit>` 单点回退。
