# -*- coding: utf-8 -*-
"""供应链分析功能 E2E 集成测试。

分两层（均确定性、不烧 LLM token）：

- **Layer A · 全栈 API 契约**：用 ``TestClient(create_app())`` 挂真实路由，
  patch 掉 auth + ``_build_executor``（桩 executor），验证端点契约、会话前缀隔离、
  前缀去除往返（F-bug 修复）、SSE 事件协议与工具中文 display_name 注入。
- **Layer B · 真实 executor 装配**：调用 ``build_supply_chain_executor`` 验证工具集
  组合（问股工具 + 供应链打分工具）与长任务边界，以及 system prompt 组装无残留占位符。

真实的 LLM 端到端冒烟（受 token/时长约束）以独立脚本方式验证，不进此确定性套件。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.config import Config
from src.storage import DatabaseManager


def teardown_function() -> None:
    DatabaseManager.reset_instance()
    Config.reset_instance()


def _fresh_db(tmp_path: Path) -> DatabaseManager:
    DatabaseManager.reset_instance()
    Config.reset_instance()
    return DatabaseManager(db_url=f"sqlite:///{tmp_path / 'sc.db'}")


def _client(tmp_path: Path, *, config=None, executor=None):
    patches = [
        patch("api.middlewares.auth.is_auth_enabled", return_value=False),
    ]
    if config is not None:
        patches.append(patch("api.v1.endpoints.supply_chain.get_config", return_value=config))
    if executor is not None:
        patches.append(patch("api.v1.endpoints.supply_chain._build_executor", return_value=executor))
    for p in patches:
        p.start()

    def _stop():
        for p in patches:
            p.stop()

    client = TestClient(create_app(static_dir=tmp_path / "static"))
    return client, _stop


# ============================================================
# Layer A · 全栈 API 契约
# ============================================================

class TestSupplyChainApiContract:
    def test_route_registered_sessions_empty(self, tmp_path):
        _fresh_db(tmp_path)
        client, stop = _client(tmp_path)
        try:
            resp = client.get("/api/v1/supply-chain/chat/sessions")
            assert resp.status_code == 200
            assert resp.json() == {"sessions": []}
        finally:
            stop()

    def test_agent_gate_returns_400_when_agent_unavailable(self, tmp_path):
        _fresh_db(tmp_path)
        config = SimpleNamespace(is_agent_available=lambda: False)
        client, stop = _client(tmp_path, config=config)
        try:
            resp = client.post(
                "/api/v1/supply-chain/chat",
                json={"message": "x"},
            )
            assert resp.status_code == 400
        finally:
            stop()

    def test_nonstream_chat_forwards_and_responds(self, tmp_path):
        _fresh_db(tmp_path)
        executor = SimpleNamespace(
            chat=lambda message, session_id, context=None, progress_callback=None: SimpleNamespace(
                success=True, content="# 报告 ok", error=None
            )
        )
        config = SimpleNamespace(is_agent_available=lambda: True)
        client, stop = _client(tmp_path, config=config, executor=executor)
        try:
            resp = client.post(
                "/api/v1/supply-chain/chat",
                json={"message": "光模块瓶颈", "session_id": "abc", "context": {"k": "v"}},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["content"] == "# 报告 ok"
            # 返回的 session_id 带 supply_chain: 前缀（非流式端点不去前缀，与郑希一致）
            assert body["session_id"].startswith("supply_chain:")
            assert body["error"] is None
        finally:
            stop()

    def test_session_prefix_isolation(self, tmp_path):
        db = _fresh_db(tmp_path)
        # 三路会话各种一条
        db.save_conversation_message("supply_chain:sc1", "user", "q1")
        db.save_conversation_message("supply_chain:sc1", "assistant", "a1")
        db.save_conversation_message("zhengxi:zx1", "user", "qz")
        db.save_conversation_message("zhengxi:zx1", "assistant", "az")
        db.save_conversation_message("wengu1", "user", "qw")

        client, stop = _client(tmp_path)
        try:
            resp = client.get("/api/v1/supply-chain/chat/sessions")
            assert resp.status_code == 200
            sessions = resp.json()["sessions"]
            ids = {s["session_id"] for s in sessions}
            # 只能看到供应链会话，且返回的 id 已去掉前缀（与前端 localStorage 一致）
            assert ids == {"sc1"}
            assert all(not sid.startswith("supply_chain:") for sid in ids)
        finally:
            stop()

    def test_prefix_strip_roundtrip_get_and_delete(self, tmp_path):
        db = _fresh_db(tmp_path)
        db.save_conversation_message("supply_chain:rt1", "user", "hi")
        db.save_conversation_message("supply_chain:rt1", "assistant", "yo")

        client, stop = _client(tmp_path)
        try:
            # GET 用无前缀 id（前端传的就是 list 返回的无前缀 id）
            get_resp = client.get("/api/v1/supply-chain/chat/sessions/rt1")
            assert get_resp.status_code == 200
            payload = get_resp.json()
            assert payload["session_id"] == "rt1"  # 返回也去前缀
            roles = [(m["role"], m["content"]) for m in payload["messages"]]
            assert roles == [("user", "hi"), ("assistant", "yo")]

            # DELETE 用无前缀 id
            del_resp = client.delete("/api/v1/supply-chain/chat/sessions/rt1")
            assert del_resp.status_code == 200
            assert del_resp.json()["deleted"] >= 1

            # 删后再 GET 应空
            assert client.get("/api/v1/supply-chain/chat/sessions/rt1").json()["messages"] == []
        finally:
            stop()

    def test_sse_stream_protocol_and_tool_display_name(self, tmp_path):
        _fresh_db(tmp_path)

        def fake_chat(message, session_id, context=None, progress_callback=None):
            # 模拟 ReAct 调用打分工具，触发 display_name 注入
            if progress_callback:
                progress_callback({"type": "thinking", "step": 1, "message": "分析中"})
                progress_callback({"type": "tool_start", "tool": "score_supply_chain_bottleneck"})
                progress_callback({
                    "type": "tool_done",
                    "tool": "score_supply_chain_bottleneck",
                    "success": True,
                    "duration": 0.4,
                })
            return SimpleNamespace(success=True, content="# 完整报告", error=None, total_steps=2)

        executor = SimpleNamespace(chat=fake_chat)
        config = SimpleNamespace(is_agent_available=lambda: True)
        client, stop = _client(tmp_path, config=config, executor=executor)
        try:
            resp = client.post(
                "/api/v1/supply-chain/chat/stream",
                json={"message": "给中际旭创打瓶颈分", "session_id": "s1"},
            )
            assert resp.status_code == 200
            text = resp.text
            # SSE 事件序列齐全
            assert '"type": "thinking"' in text
            assert '"type": "tool_start"' in text
            assert '"type": "tool_done"' in text
            assert '"type": "done"' in text
            # 打分工具的中文名被注入（SUPPLY_CHAIN_TOOL_DISPLAY_NAMES）
            assert "瓶颈打分" in text
        finally:
            stop()


# ============================================================
# Layer B · 真实 executor 装配（不依赖 LLM）
# ============================================================

class TestSupplyChainExecutorWiring:
    def test_factory_builds_registry_and_bounds(self):
        from src.agent.factory import build_supply_chain_executor

        executor = build_supply_chain_executor()
        tool_names = {t.name for t in executor.tool_registry.list_tools()}

        # 供应链打分工具已注册
        assert "score_supply_chain_bottleneck" in tool_names
        # 复用了问股工具集（至少包含行情/基本面代表工具）
        assert {"get_realtime_quote", "get_daily_history"} <= tool_names
        # 长任务边界（方案 A：硬编码，不读 config.agent_max_steps）
        assert executor.max_steps == 40
        assert executor.timeout_seconds == 1200.0

    def test_system_prompt_assembles_without_leftover_placeholders(self):
        from src.agent.supply_chain_executor import build_supply_chain_system_prompt

        prompt = build_supply_chain_system_prompt()
        # 占位符已全部替换
        assert "{{SKILL}}" not in prompt
        assert "{{REFERENCES}}" not in prompt
        # 核心方法论与打分工具指令注入成功
        assert "Serenity" in prompt
        assert "score_supply_chain_bottleneck" in prompt
        # 5 个核心 references 至少有内容（非加载失败占位）
        assert "加载失败" not in prompt


# ============================================================
# Layer B+ · executor 持久化闭环（确定性，patch run_agent_loop，不烧 token）
# ============================================================

class TestSupplyChainExecutorPersistence:
    def test_executor_persists_user_and_assistant_then_endpoint_reads_back(self, tmp_path):
        """executor.chat() 的 user/assistant 消息落库，GET 端点能原样读回。

        用真实 build_supply_chain_executor + patch run_agent_loop 返回固定结果，
        驱动 chat() 的真实持久化路径（conversation_manager → get_db），不调用真 LLM。
        """
        from src.agent.runner import RunLoopResult

        db = _fresh_db(tmp_path)

        def fake_run_agent_loop(*, messages, **kwargs):
            return RunLoopResult(success=True, content="# 持久化报告", total_steps=1)

        with patch("src.agent.runner.run_agent_loop", side_effect=fake_run_agent_loop):
            from src.agent.factory import build_supply_chain_executor

            executor = build_supply_chain_executor()
            executor.chat(
                message="给中际旭创打瓶颈分",
                session_id="supply_chain:persist1",
            )

        # 1) 直读 DB：user + assistant 两条
        msgs = db.get_conversation_messages("supply_chain:persist1")
        roles = [(m["role"], m["content"]) for m in msgs]
        assert roles == [("user", "给中际旭创打瓶颈分"), ("assistant", "# 持久化报告")]

        # 2) 经 GET 端点读回（端点用无前缀 id，返回去前缀 id）
        client, stop = _client(tmp_path)
        try:
            resp = client.get("/api/v1/supply-chain/chat/sessions/persist1")
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["session_id"] == "persist1"
            assert [(m["role"], m["content"]) for m in payload["messages"]] == roles
        finally:
            stop()
