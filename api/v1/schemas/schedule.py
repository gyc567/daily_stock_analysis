# -*- coding: utf-8 -*-
"""Schedule API response schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class ScheduleTriggerAccepted(BaseModel):
    """Manual schedule trigger accepted response (202, async execution)."""

    status: str = Field("accepted", description="提交状态")
    message: str = Field(..., description="提示信息")
    task: str = Field(..., description="任务名：watchlist 或 market_review")
    task_id: Optional[str] = Field(
        None,
        description="后台任务 ID（仅当任务实际提交时返回）",
    )
    trace_id: Optional[str] = Field(
        None,
        description="本次后台任务的诊断 trace ID",
    )
    triggered_at: str = Field(..., description="触发时间（ISO 格式）")
