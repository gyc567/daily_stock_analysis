# -*- coding: utf-8 -*-
"""Request/response schemas for the midterm trend compass API."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.decision_action import DecisionAction


class CompassAnalyzeRequest(BaseModel):
    """POST /compass/analyze body (Layer 3: strict + frozen)."""

    model_config = ConfigDict(strict=True, frozen=True)

    code: Annotated[str, Field(min_length=4, max_length=16, pattern=r"^[A-Za-z0-9.]+$")]
    stock_name: Optional[Annotated[str, Field(max_length=64)]] = None
    subject_type: Literal["stock", "etf", "index"] = "stock"
    draft_action: Optional[Literal["buy", "watch", "sell"]] = None
    lang: Literal["zh", "en"] = "zh"


class RewriteStepView(BaseModel):
    """One fired constraint in evaluation order (causal chain rendering)."""

    model_config = ConfigDict(strict=True, frozen=True)

    reason_code: str
    action_after: Literal["buy", "watch", "sell"]


class CompassRewriteView(BaseModel):
    """Rewriter outcome for a user-supplied draft action (P2 PR-B2/B1)."""

    model_config = ConfigDict(strict=True, frozen=True)

    initial_action: Literal["buy", "watch", "sell"]
    final_action: Literal["buy", "watch", "sell"]
    reason_codes: List[str]
    steps: List[RewriteStepView] = Field(default_factory=list)
    decision_action: DecisionAction
    investment_action: Literal["建仓", "观察", "止损"]


class CompassAnalyzeResponse(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    compass: Dict[str, Any]
    short_card: str
    long_card: str
    rewrite: Optional[CompassRewriteView] = None
