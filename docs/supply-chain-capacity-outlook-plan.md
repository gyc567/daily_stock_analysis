# 供应链产能展望功能实现方案

**状态**：已审计优化
**日期**：2026-09-01
**版本**：v2（优化版）

---

## 一、背景与目标

在供应链深度报告（SupplyChainDeepDiveV3）中新增 **§10.b 产能展望与预测** 功能，实现：

- 今年产能统计（历史数据聚合）
- 未来三个月月度产能预测
- 未来6-12个月中期产能展望
- 需求驱动推断 + 行业模板降级

### 用户需求确认

| 选项 | 选择 |
|-----|------|
| 数据来源 | A（财务报告）+ B（akshare/tushare） |
| 预测方法 | C（需求驱动推断） |
| 展示位置 | A（新增独立章节 §11 → 优化为 §10.b） |
| 预测粒度 | A（月度） |
| 数据缺失处理 | B（降级推断，用行业均值估算） |

---

## 二、核心设计决策

| 决策项 | 原方案 | 优化后 |
|-------|-------|--------|
| 章节编号 | §11 独立章节 | **§10.b 产能展望**（作为 §10 的子节） |
| Schema 数量 | 3个（Forecast + MidTerm + Outlook） | **1个**（统一用 `time_window` 区分期限） |
| 数据来源 | akshare API | **年报解析 + 已有 §10 数据** |
| 工具注册 | supply_chain_executor.py | **factory.py + supply_chain_tools.py** |
| 行业模板 | 新建 `_INDUSTRY_CAPACITY_TEMPLATES` | **扩展 `_INDUSTRY_INFERENCE_TEMPLATES`** |
| 数据缺失 | 硬填充行业均值 | **标记"待核验"，不静默填充** |

---

## 三、Schema 设计

### 3.1 新增 Schema

**文件**：`src/schemas/supply_chain.py`

```python
# ============================================================
# §10.b 产能展望（扩展 FinancialQualityV3）
# ============================================================

DemandSignal = Literal[
    "下游订单饱满",
    "行业出货量增长",
    "在手订单充裕",
    "季节性旺季",
    "扩产产能释放",
    "需求回落",
    "限产检修",
]

CapacityChangeFactor = Literal[
    "新建产能释放",
    "爬坡良率提升",
    "季节性检修",
    "限产政策",
    "设备升级改造",
    "外协加工",
]


class CapacityOutlookV3(BaseModel):
    """[v3 §10.b] 产能展望与预测。
    
    定位：§10 财务质量与产能跟踪的扩展子节，
    复用已有的 historical periods 数据，补充未来预测。
    """
    
    model_config = ConfigDict(
        strict=True, frozen=True, validate_assignment=True, extra="forbid"
    )
    
    ticker: str = Field(..., pattern=r"^[\w\.\-]{1,16}$")
    company: str = Field(..., min_length=1, max_length=80)
    fetched_at: Optional[datetime] = Field(default=None)
    
    industry_unit_hint: Optional[str] = Field(
        default=None, max_length=20,
        description="行业推荐产量单位（来自行业模板）"
    )
    
    historical_summary: str = Field(default="", description="历史产能利用率摘要")
    historical_data_quality: Literal["complete", "partial", "sparse", "none"] = Field(default="none")
    
    forecasts: List["CapacityForecastPeriodV3"] = Field(default_factory=list)
    
    trend: Literal["rising", "stable", "falling", "volatile", "insufficient_data"] = Field(
        default="insufficient_data"
    )
    trend_rationale: str = Field(default="", description="趋势判断依据")
    
    capacity_bottleneck_risk: Literal["high", "medium", "low", "unknown"] = Field(default="unknown")
    demand_supply_balance: Literal["tight", "balanced", "loose", "unknown"] = Field(default="unknown")
    
    expansion_plans: List["ExpansionProjectV3"] = Field(default_factory=list, max_length=5)
    
    data_source_notes: str = Field(default="")
    confidence: AggregateConfidence = Field(default="low")
    
    @model_validator(mode="after")
    def _check_forecast_consistency(self) -> "CapacityOutlookV3":
        if not self.forecasts and not self.historical_summary:
            self.trend = "insufficient_data"
        return self


class CapacityForecastPeriodV3(BaseModel):
    """[v3 §10.b] 单期产能预测（短期+中期统一Schema）。"""
    
    model_config = ConfigDict(
        strict=True, frozen=True, validate_assignment=True, extra="forbid"
    )
    
    time_window: TimeWindow = Field(...)  # 复用已有的 TimeWindow
    period_label: str = Field(..., description="人类可读标签（如'2026-10'）")
    
    predicted_utilization_pct: Optional[Decimal] = Field(
        default=None, ge=Decimal("0"), le=Decimal("200")
    )
    predicted_output_volume: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    predicted_output_unit: Optional[str] = Field(default=None, max_length=20)
    
    inference_basis: str = Field(...)
    demand_signals: List[DemandSignal] = Field(default_factory=list, max_length=5)
    capacity_change_factors: List[CapacityChangeFactor] = Field(default_factory=list, max_length=5)
    
    confidence: Literal["high", "medium", "low"] = Field(default="medium")
    evidence_strength: EvidenceStrength = Field(default="analysis")
    
    @model_validator(mode="after")
    def _check_volume_unit_consistency(self) -> "CapacityForecastPeriodV3":
        if self.predicted_output_volume is not None and self.predicted_output_unit is None:
            raise ValueError(
                "CapacityForecastPeriodV3 契约违反：predicted_output_volume 非空时 "
                "必须提供 predicted_output_unit"
            )
        return self


class ExpansionProjectV3(BaseModel):
    """[v3 §10.b] 扩产项目跟踪。"""
    
    model_config = ConfigDict(
        strict=True, frozen=True, validate_assignment=True, extra="forbid"
    )
    
    project_name: str = Field(..., min_length=1, max_length=120)
    expected_completion: Optional[str] = Field(default=None)
    expected_capacity_addition: Optional[str] = Field(default=None, max_length=80)
    progress_status: Literal["planning", "construction", "ramping", "completed"] = Field(
        default="planning"
    )
    source: str = Field(default="年报披露")
    evidence_strength: EvidenceStrength = Field(default="analysis")
```

### 3.2 扩展 FinancialQualityV3

```python
class FinancialQualityV3(BaseModel):
    # ... 现有字段 ...
    
    # 新增
    expansion_projects: List[ExpansionProjectV3] = Field(default_factory=list)
    expansion_status_notes: Optional[str] = Field(default=None, max_length=200)
```

### 3.3 扩展 SupplyChainDeepDiveV3

```python
class SupplyChainDeepDiveV3(BaseModel):
    # ... 现有字段 ...
    
    # 新增
    capacity_outlook: Optional[CapacityOutlookV3] = Field(default=None)
```

---

## 四、数据获取策略

### 4.1 数据来源优先级

| 优先级 | 来源 | 说明 |
|-------|------|------|
| 1 | §10 历史数据 | 直接复用 `FinancialQualityV3.capacity_utilization_pct` |
| 2 | 年报 PDF | 扩展 `annual_report_provider.py` 至全文扫描 |
| 3 | 知识库 | `kb_retriever` 命中含有产能披露的文档 |
| 4 | LLM 推断 | 作为最后兜底 |

### 4.2 扩展 annual_report_provider.py

```python
# 扫描页数：10 → 50
for page in reader.pages[:50]

# 新增 helper
def extract_capacity_disclosures(text: str) -> List[Dict]:
    """从年报正文中提取产能相关段落。"""
    pattern = r'(?:产能利用率|设计产能|实际产量|扩产|在建工程|产销率)[：:][^\n]{10,200}'
    matches = re.findall(pattern, text)
    return [{"keyword": m[:20], "content": m} for m in matches]
```

### 4.3 扩展 _INDUSTRY_INFERENCE_TEMPLATES

```python
# 在每个行业模板中追加
{
    "capacity_unit_hint": "万片/月",  # 或 "GWh/年" 等
    "benchmark_utilization": 85.0,
    "seasonal_pattern": "Q3>Q4>Q2>Q1",
}
```

### 4.4 降级规则

```
1. 有历史产能数据 → 正常预测
2. 无历史数据，有行业模板 → 使用行业 benchmark + 标记"行业均值填充，待核验"
3. 无历史数据，无行业模板 → trend = "insufficient_data"，不生成预测
4. 禁止静默填充数据 → 所有填充必须显式标注 source
```

---

## 五、工具设计

**新增工具**：`analyze_capacity_outlook`

**位置**：`src/agent/tools/supply_chain_tools.py`（追加到 `ALL_SUPPLY_CHAIN_TOOLS`）

**Prompt**：
```
_CAPACITY_OUTLOOK_PROMPT = """
你是一个产能展望分析师。基于以下信息，推断未来1-12个月的产能走势。

输入数据：
- 历史产能利用率：{historical_summary}
- 扩产项目：{expansion_projects}
- 下游需求信号：{demand_drivers}
- 行业产能模板：{industry_template}

输出要求：
1. 短期预测（1-3个月）：每月预测值 + 推断依据
2. 中期预测（6-12个月）：每季度趋势判断
3. 供需格局判断（tight/balanced/loose）
4. 产能瓶颈风险评估

注意：
- 历史数据不足时，使用行业均值并标注来源
- 预测值需要给出置信度（高/中/低）
- 禁止凭空捏造数据
"""
```

---

## 六、渲染器设计

**新增函数**：`render_capacity_outlook`

**位置**：`src/services/supply_chain/deep_dive_renderer.py`

**输出格式**：

```markdown
## 10.b 产能展望与预测

**数据质量**：{complete/partial/sparse/none}

### 10.b.1 历史产能跟踪
{historical_summary}

### 10.b.2 短期预测（未来3个月）
| 月份 | 预测利用率 | 推断依据 | 置信度 |

### 10.b.3 中期展望（6-12个月）
| 季度 | 预计利用率趋势 | 关键驱动因素 | 置信度 |

### 10.b.4 供需格局与风险提示
**供需格局**：🔴 偏紧 / 🟡 平衡 / 🟢 宽松
**产能瓶颈风险**：🟡 中
```

---

## 七、文件改动清单

| 文件 | 改动 | 类型 |
|-----|------|------|
| `src/schemas/supply_chain.py` | 新增 Schema；扩展 FinancialQualityV3、SupplyChainDeepDiveV3 | 追加 + 修改 |
| `src/agent/tools/supply_chain_tools.py` | 新增 analyze_capacity_outlook；追加到 ALL_SUPPLY_TOOLS | 追加 |
| `src/services/supply_chain/deep_dive_renderer.py` | 新增 render_capacity_outlook | 追加 |
| `src/services/supply_chain/supply_chain_data_service.py` | 扩展 _INDUSTRY_INFERENCE_TEMPLATES | 扩展 |
| `data_provider/supply_chain/annual_report_provider.py` | 扩展 PDF 扫描页数；新增 extract_capacity_disclosures | 扩展 |
| `src/agent/supply_chain_executor.py` | 扩展 system prompt | 扩展 prompt |
| `tests/test_supply_chain_v3_tools.py` | 断言修复（>= 10 + name-based） | 修改 |
| `tests/test_supply_chain_services.py` | 断言修复（>= 10 + name-based） | 修改 |
| `tests/test_supply_chain_capacity_outlook.py` | 新增单元测试 | 新增 |
| `docs/CHANGELOG.md` | 记录新功能 | 追加 |

---

## 八、实现顺序

```
Phase 1: Schema 定义
Phase 2: 数据获取
Phase 3: 工具
Phase 4: 渲染
Phase 5: Prompt 扩展
Phase 6: 测试
Phase 7: 文档
```

---

## 九、审计发现与优化

### 严重问题（已解决）

| # | 问题 | 解决方案 |
|---|------|---------|
| 1 | §11 编号冲突 | 改为 §10.b 子节 |
| 2 | akshare API 不存在 | 改用年报解析 + §10 历史数据 |
| 3 | 测试断言断裂 | 改为 `>= 10` + name-based |
| 4 | 与 §10 数据重叠 | §10 存历史，§10.b 存预测 |
| 5 | 缺少三层防御 | 使用 Decimal + icontract |
| 6 | 注册位置错误 | 指向 factory.py（已自动注册） |

### 主要问题（已解决）

| # | 问题 | 解决方案 |
|---|------|---------|
| 1 | 年报只读10页 | 扩展至50页 + 关键词提取 |
| 2 | 平行 Schema | 合并为单一 Schema + time_window |
| 3 | 静默填充 | 显式标注"行业均值填充，待核验" |
| 4 | 平行行业模板 | 扩展现有 `_INDUSTRY_INFERENCE_TEMPLATES` |
