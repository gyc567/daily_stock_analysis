# -*- coding: utf-8 -*-
"""
===================================
Agent Reach Service
===================================

底层内容 / 行情数据源服务：封装 Agent-Reach 的 web(Jina Reader) 与
xueqiu(雪球) 渠道，对外暴露统一标准化数据结构，供任意服务 / agent 复用。

agent_reach 为可选外部依赖（``pipx install agent-reach`` + ``agent-reach install``）。
未安装或渠道故障时，所有方法优雅降级（返回 None / 空列表），绝不拖垮主流程，
符合仓库「不配置也可运行，配置后增强能力」的稳定性护栏。

设计要点：
  - 真正「用」Agent-Reach：直接懒加载导入 ``agent_reach.channels.{web,xueqiu}``
    并委托调用，本服务自身不写任何 HTTP / subprocess —— 既不重复造轮子，
    又让本服务代码 0 网络依赖、天然 100% 可测。
  - 高内聚低耦合：自包含异常（不依赖 ``data_provider.base``），避免内容服务
    反向耦合行情框架。
  - 标准化输出为 frozen dataclass（满足不可变规则 + Layer1 类型注解）。

References:
  - https://github.com/Panniantong/Agent-Reach
  - agent_reach/channels/web.py     (Jina Reader, 纯 HTTP)
  - agent_reach/channels/xueqiu.py  (雪球官方 API + cookie, 纯 HTTP)
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# 可选依赖：agent_reach 渠道（导入期探测，失败优雅降级）
# --------------------------------------------------------------------------- #
try:  # pragma: no cover <- 分支由 tests/test_agent_reach_service.py 显式覆盖
    from agent_reach.channels.web import WebChannel  # type: ignore[import-not-found]
    from agent_reach.channels.xueqiu import XueqiuChannel  # type: ignore[import-not-found]

    _AVAILABLE = True
    _UNAVAILABLE_REASON: Optional[str] = None
except ImportError as exc:  # agent_reach 未安装 —— 优雅降级
    WebChannel = None  # type: ignore[assignment,misc]
    XueqiuChannel = None  # type: ignore[assignment,misc]
    _AVAILABLE = False
    _UNAVAILABLE_REASON = f"agent_reach 未安装: {exc}"


# --------------------------------------------------------------------------- #
# 自包含异常
# --------------------------------------------------------------------------- #
class AgentReachError(Exception):
    """AgentReachService 基础异常。"""


class AgentReachUnavailableError(AgentReachError):
    """agent_reach 未安装或渠道不可用。"""


# --------------------------------------------------------------------------- #
# 标准化输出结构（frozen dataclass —— 不可变 + Layer1 类型注解）
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ContentItem:
    """通用内容条目（web 正文 / 雪球热帖共用）。"""

    platform: str
    title: str
    url: str
    content: str
    snippet: str
    source: str = ""
    author: str = ""
    published_at: Optional[str] = None
    fetched_at: str = ""


@dataclass(frozen=True)
class XueqiuQuote:
    symbol: str
    name: str
    current: Optional[float]
    percent: Optional[float]
    chg: Optional[float]
    high: Optional[float]
    low: Optional[float]
    open: Optional[float]
    last_close: Optional[float]
    volume: Optional[float]
    amount: Optional[float]
    market_capital: Optional[float]
    turnover_rate: Optional[float]
    pe_ttm: Optional[float]
    timestamp: Optional[int]


@dataclass(frozen=True)
class XueqiuStock:
    symbol: str
    name: str
    exchange: str


@dataclass(frozen=True)
class XueqiuHotStock:
    symbol: str
    name: str
    current: Optional[float]
    percent: Optional[float]
    rank: int


@dataclass(frozen=True)
class ChannelStatus:
    name: str
    available: bool
    status: str
    backend: Optional[str]
    message: str


# --------------------------------------------------------------------------- #
# 工具函数（纯函数，便于单测与确定性 mock）
# --------------------------------------------------------------------------- #
def _now_utc_iso() -> str:
    """当前 UTC 时间 ISO 字符串（测试可 patch 以保证确定性）。"""
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    """宽松转 float，失败或 None 返回 None。"""
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    """宽松转 int，失败或 None 返回 None。"""
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


_TITLE_PREFIX = re.compile(r"^Title:\s*(.+?)\s*$", re.IGNORECASE)
_MD_H1 = re.compile(r"^#\s+(.+?)\s*$")
# 去掉图片 / 链接 / 强调等 Markdown 噪声，链接保留锚文本
_MARKDOWN_NOISE = re.compile(r"!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)|[*_`>#-]")


def _extract_title(markdown: str) -> str:
    """从 Jina / Markdown 文本 best-effort 提取标题。

    优先级：``Title: xxx`` 前缀行 → 首行 ``# xxx`` → 空串。
    """
    if not markdown or not markdown.strip():
        return ""
    first_line = markdown.lstrip().splitlines()[0]
    matched = _TITLE_PREFIX.match(first_line)
    if matched:
        return matched.group(1).strip()
    matched = _MD_H1.match(first_line)
    if matched:
        return matched.group(1).strip()
    return ""


def _make_snippet(text: str, limit: int = 200) -> str:
    """把 Markdown / 正文压成单行短摘要。"""
    if not text:
        return ""
    cleaned = _MARKDOWN_NOISE.sub(
        lambda m: m.group(1) if m.group(1) is not None else "", text
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


# --------------------------------------------------------------------------- #
# 服务主体
# --------------------------------------------------------------------------- #
class AgentReachService:
    """底层内容 / 行情数据源服务（web + 雪球）。

    所有公共方法在 agent_reach 未安装或渠道异常时优雅降级：
      - read_url / get_xueqiu_*  → None / []
      - health_check              → 标记不可用
    不向上层抛异常。
    """

    def __init__(self) -> None:
        self._web: Optional[object] = None
        self._xueqiu: Optional[object] = None

    # ----------------------------- 可用性 ----------------------------- #
    def is_available(self) -> bool:
        """agent_reach 是否已安装可导入。"""
        return _AVAILABLE

    def unavailable_reason(self) -> Optional[str]:
        """不可用原因（可用时为 None）。"""
        return _UNAVAILABLE_REASON

    def _ensure_channels(self) -> None:
        """懒加载实例化两个渠道；未安装时抛 AgentReachUnavailableError。"""
        if not _AVAILABLE:
            raise AgentReachUnavailableError(_UNAVAILABLE_REASON or "agent_reach 不可用")
        if self._web is None:
            self._web = WebChannel()  # type: ignore[misc]
        if self._xueqiu is None:
            self._xueqiu = XueqiuChannel()  # type: ignore[misc]

    # ------------------------------- web ------------------------------- #
    def read_url(self, url: str) -> Optional[ContentItem]:
        """通过 Jina Reader 读取网页，返回标准化 ContentItem；失败 / 未装返回 None。"""
        if not _AVAILABLE:
            logger.debug("AgentReachService.read_url 跳过: %s", _UNAVAILABLE_REASON)
            return None
        try:
            self._ensure_channels()
            markdown = self._web.read(url)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 —— 渠道任意错误统一降级
            logger.warning("read_url(%s) 失败: %s", url, exc)
            return None
        return self._normalize_web(url, markdown)

    # ------------------------------ 雪球 ------------------------------ #
    def get_xueqiu_hot_posts(self, limit: int = 20) -> list[ContentItem]:
        """雪球热门帖子 → ContentItem 列表。"""
        if not _AVAILABLE:
            logger.debug("get_xueqiu_hot_posts 跳过: %s", _UNAVAILABLE_REASON)
            return []
        try:
            self._ensure_channels()
            posts = self._xueqiu.get_hot_posts(limit)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_xueqiu_hot_posts 失败: %s", exc)
            return []
        return self._normalize_hot_posts(posts)

    def get_xueqiu_stock_quote(self, symbol: str) -> Optional[XueqiuQuote]:
        """雪球实时行情 → XueqiuQuote。"""
        if not _AVAILABLE:
            logger.debug("get_xueqiu_stock_quote 跳过: %s", _UNAVAILABLE_REASON)
            return None
        try:
            self._ensure_channels()
            data = self._xueqiu.get_stock_quote(symbol)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_xueqiu_stock_quote(%s) 失败: %s", symbol, exc)
            return None
        return self._normalize_quote(data, symbol)

    def search_xueqiu_stocks(self, query: str, limit: int = 10) -> list[XueqiuStock]:
        """雪球搜索股票 → XueqiuStock 列表。"""
        if not _AVAILABLE:
            logger.debug("search_xueqiu_stocks 跳过: %s", _UNAVAILABLE_REASON)
            return []
        try:
            self._ensure_channels()
            stocks = self._xueqiu.search_stock(query, limit)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("search_xueqiu_stocks(%s) 失败: %s", query, exc)
            return []
        return self._normalize_stocks(stocks)

    def get_xueqiu_hot_stocks(self, limit: int = 10) -> list[XueqiuHotStock]:
        """雪球热门股票排行 → XueqiuHotStock 列表。"""
        if not _AVAILABLE:
            logger.debug("get_xueqiu_hot_stocks 跳过: %s", _UNAVAILABLE_REASON)
            return []
        try:
            self._ensure_channels()
            stocks = self._xueqiu.get_hot_stocks(limit)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_xueqiu_hot_stocks 失败: %s", exc)
            return []
        return self._normalize_hot_stocks(stocks)

    # ---------------------------- 健康检查 ---------------------------- #
    def health_check(self) -> dict[str, ChannelStatus]:
        """探测 web / xueqiu 渠道当前可用性与后端。"""
        if not _AVAILABLE:
            msg = _UNAVAILABLE_REASON or "agent_reach 不可用"
            return {
                "web": ChannelStatus("web", False, "off", None, msg),
                "xueqiu": ChannelStatus("xueqiu", False, "off", None, msg),
            }
        try:
            self._ensure_channels()
        except Exception as exc:  # noqa: BLE001 —— 实例化失败也优雅降级
            logger.warning("health_check 渠道实例化失败: %s", exc)
            err = "渠道实例化失败"
            return {
                "web": ChannelStatus("web", False, "error", None, err),
                "xueqiu": ChannelStatus("xueqiu", False, "error", None, err),
            }
        return {
            "web": self._probe("web", self._web, "Jina Reader"),
            "xueqiu": self._probe("xueqiu", self._xueqiu, "Xueqiu API (需要登录 Cookie)"),
        }

    @staticmethod
    def _probe(name: str, channel: object, fallback_backend: str) -> ChannelStatus:
        """对单个渠道执行 check() 并归一化为 ChannelStatus。"""
        check = getattr(channel, "check", None)
        if check is None:
            return ChannelStatus(name, False, "error", None, "channel 缺少 check 方法")
        try:
            status, message = check()
            backend = getattr(channel, "active_backend", None) or fallback_backend
            return ChannelStatus(name, status == "ok", status, backend, message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("health_check(%s) 探测失败: %s", name, exc)
            return ChannelStatus(name, False, "error", None, str(exc))

    # --------------------------- 归一化（纯函数） --------------------------- #
    @staticmethod
    def _normalize_web(url: str, markdown: object) -> ContentItem:
        text = markdown if isinstance(markdown, str) else ""
        return ContentItem(
            platform="web",
            title=_extract_title(text),
            url=url,
            content=text,
            snippet=_make_snippet(text),
            source="Jina Reader",
            fetched_at=_now_utc_iso(),
        )

    @staticmethod
    def _normalize_hot_posts(posts: object) -> list[ContentItem]:
        if not isinstance(posts, list):
            return []
        fetched_at = _now_utc_iso()
        items: list[ContentItem] = []
        for post in posts:
            if not isinstance(post, dict):
                continue
            text = str(post.get("text") or "")
            items.append(
                ContentItem(
                    platform="xueqiu",
                    title=str(post.get("title") or ""),
                    url=str(post.get("url") or ""),
                    content=text,
                    snippet=text[:200],
                    source="雪球热帖",
                    author=str(post.get("author") or ""),
                    fetched_at=fetched_at,
                )
            )
        return items

    @staticmethod
    def _normalize_quote(data: object, symbol: str) -> Optional[XueqiuQuote]:
        if not isinstance(data, dict):
            return None
        return XueqiuQuote(
            symbol=str(data.get("symbol") or symbol),
            name=str(data.get("name") or ""),
            current=_to_float(data.get("current")),
            percent=_to_float(data.get("percent")),
            chg=_to_float(data.get("chg")),
            high=_to_float(data.get("high")),
            low=_to_float(data.get("low")),
            open=_to_float(data.get("open")),
            last_close=_to_float(data.get("last_close")),
            volume=_to_float(data.get("volume")),
            amount=_to_float(data.get("amount")),
            market_capital=_to_float(data.get("market_capital")),
            turnover_rate=_to_float(data.get("turnover_rate")),
            pe_ttm=_to_float(data.get("pe_ttm")),
            timestamp=_to_int(data.get("timestamp")),
        )

    @staticmethod
    def _normalize_stocks(stocks: object) -> list[XueqiuStock]:
        if not isinstance(stocks, list):
            return []
        result: list[XueqiuStock] = []
        for item in stocks:
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol")
            name = item.get("name")
            if not symbol and not name:
                continue
            result.append(
                XueqiuStock(
                    symbol=str(symbol or ""),
                    name=str(name or ""),
                    exchange=str(item.get("exchange") or ""),
                )
            )
        return result

    @staticmethod
    def _normalize_hot_stocks(stocks: object) -> list[XueqiuHotStock]:
        if not isinstance(stocks, list):
            return []
        result: list[XueqiuHotStock] = []
        for item in stocks:
            if not isinstance(item, dict):
                continue
            result.append(
                XueqiuHotStock(
                    symbol=str(item.get("symbol") or ""),
                    name=str(item.get("name") or ""),
                    current=_to_float(item.get("current")),
                    percent=_to_float(item.get("percent")),
                    rank=_to_int(item.get("rank")) or 0,
                )
            )
        return result
