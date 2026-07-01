# -*- coding: utf-8 -*-
"""Markdown 转 PDF 工具（深度投研 / 政策与公告排雷 / 供应链分析 三处报告共用）。

用 **WeasyPrint**（HTML/CSS → PDF，基于 Pango/Cairo）渲染。相比旧 xhtml2pdf +
reportlab CID 字体方案，正确处理：
- ``<ul><li>`` 项目符号（修复旧方案 bullet 渲染成 "煉" 的 CID CMap 错位）
- ``<pre>`` 代码块（修复旧方案 CJK 代码块整片黑条的 ``<pre>`` 元素级 bug）
- emoji / 箭头 / 表格（标准 CSS 兼容，旧方案多变为方框或错位汉字）

依赖：
- ``pip install weasyprint``
- 系统库：pango / cairo / glib / gdk-pixbuf
  - macOS：``brew install pango cairo gdk-pixbuf glib``（本模块自动探测 brew lib 路径，
    用户无需手动配置 ``DYLD_FALLBACK_LIBRARY_PATH``）
  - Linux/Debian：``apt-get install libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libglib2.0-0 fonts-noto-cjk``

设计要点：
1. **接口契约不变**：``markdown_to_pdf_file(markdown_text, output_path) -> Optional[str]``，
   成功返回 ``output_path``，失败/依赖缺失返回 ``None``（不抛异常），由 service 层降级为
   HTTP 404，不影响报告生成主流程。
2. **CJK 字体回退链**：跨平台 CSS font-family（macOS 苹方 / Linux Noto / 文泉 / 雅黑）。
3. **模块级 ``threading.Semaphore(1)``** 限并发（WeasyPrint 渲染 CPU/内存密集），保留防 OOM 语义。
4. **静态 HTML 模板**：不再复用 ``formatters.markdown_to_html_document``（该 formatter 面向
   web/邮件，含 ``table { display: block; overflow-x: auto }``、``:hover``、
   ``max-width: 900px`` 等不适合分页 PDF 的 CSS）。本模块直接用 ``markdown2.markdown`` 生成
   body，再自构含 PDF 专用 CSS 的完整 HTML 模板。
5. **共享 emoji 剥离**：``strip_emoji_for_pdf`` 由本模块统一提供，深度投研 / 排雷 / 供应链
   三处报告自动受益，避免单点补丁式修复。

用法（endpoint）：
    path = await asyncio.to_thread(markdown_to_pdf_file, markdown_text, output_path)
    if path:
        return FileResponse(path, ...)

Security note: 输入为系统生成的投研报告 markdown，经 markdown2 → HTML → WeasyPrint 渲染，
不执行外部脚本；构造 HTML 时不传 base_url，不加载远程资源。

INVARIANT（不可变约束，参见 docs/pdf-generation-unification-plan.md §6）：
- ``markdown_to_pdf_file`` 签名与 ``return None`` 失败语义保持不变
- ``_prepare_weasyprint_env`` / ``_pdf_lock`` / ``_PDF_LOCK_TIMEOUT`` 三个底层
  weasyprint 基础设施不删除（macOS brew glib 路径注入是已验证修复）
- 不引入新 HTML 模板引擎（继续用 markdown2 + f-string）
- 不传 base_url，不加载远程资源，输入仅系统生成 markdown
"""

from __future__ import annotations

import logging
import os
import platform
import re
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# 单进程并发限流（WeasyPrint 渲染 CPU/内存密集，同进程串行避免 OOM）。
# 注：同一时刻只有 1 个 PDF 在生成；其他请求排队。
_pdf_lock = threading.Semaphore(1)

# Semaphore 获取超时秒数（提为常量，便于测试注入小值覆盖超时分支）。
_PDF_LOCK_TIMEOUT = 5.0

# macOS Homebrew glib 动态库候选路径（Apple Silicon / Intel）。
_BREW_LIB_CANDIDATES = ("/opt/homebrew/lib", "/usr/local/lib")
# 判定 brew glib 是否存在的标记文件（WeasyPrint 经 cffi 加载 libgobject）。
_GOBJECT_MARKER = "libgobject-2.0.0.dylib"

# CJK 字体回退链：macOS PingFang/Hiragino，Linux Noto/Source Han/文泉/雅黑，最后 sans-serif。
# 保证不同平台都能正确渲染中文；PDF 嵌入字体子集后外观稳定。
_PDF_FONT_STACK = (
    '"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", '
    '"Source Han Sans SC", "WenQuanYi Micro Hei", "Microsoft YaHei", sans-serif'
)

# ---------------------------------------------------------------------------
# 共享 emoji 剥离（从 supply_chain_report_service 迁来，供三处报告共用）。
# WeasyPrint 无法把彩色 emoji 位图（sbix/CBDT）嵌入 PDF，路由到
# Apple-Color-Emoji 字体时渲染成豆腐块。仅剥装饰性 emoji，保留
# CJK / ①②③ / ≤ / μ / • / → / —— 等信息性字符。**PDF 渲染专用，不改 .md 原文**。
# ---------------------------------------------------------------------------
_EMOJI_STRIP_RE = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"  # 区域指示符（旗帜）
    "\U0001f300-\U0001faff"  # 补充平面 emoji / 象形（📈🔥✅🎯…）
    "☀-➿"  # 杂项符号 & 丁巴符（⚠ ✂ ✏ ✅ …）
    "⬀-⯿"  # 补充符号象形 A
    "︀-️"  # 变体选择符 VS1-VS16
    "‍"  # 零宽连接符 ZWJ
    "]+"
)


def strip_emoji_for_pdf(text: Optional[str]) -> str:
    """剥掉 PDF 渲染时无法呈现的彩色 emoji / 变体选择符（保留 CJK 与常用符号）。

    信息性字符（中文、①②③、≤、μm、•、→、—— 等）WeasyPrint 经 PingFang SC 能正常渲染，
    故保留；仅剥装饰性 emoji（警告语义由周围文字承担）。``None`` / 空串安全返回空串。

    这是 PDF 渲染专用函数。``markdown_to_pdf_file`` 内部自动调用，业务代码（service / endpoint）
    无需重复处理。
    """
    return _EMOJI_STRIP_RE.sub("", text or "")


# ---------------------------------------------------------------------------
# PDF 专用 CSS（按 docs/pdf-generation-unification-plan.md §6.3 重写）
# 纯 CSS 字符串（不含 <style> 标签），由 HTML 模板的 <style>{}</style> 包裹。
# CSS 的 { } 需转义为 {{ }} 以走 str.format（_PDF_FONT_STACK 注入用）。
# ---------------------------------------------------------------------------
_PDF_CSS = """
@page {{ margin: 20mm 18mm; }}
body {{
  font-family: {fonts};
  font-size: 11pt;
  line-height: 1.6;
  color: #222;
}}
/* 标题层级（机构研报风格，h5/h6 不小于正文 11pt） */
h1 {{ font-size: 18pt; font-weight: bold; margin: 12pt 0 6pt 0; line-height: 1.3; }}
h2 {{ font-size: 15pt; font-weight: bold; margin: 10pt 0 5pt 0; line-height: 1.3; }}
h3 {{ font-size: 13pt; font-weight: bold; margin: 8pt 0 4pt 0; line-height: 1.3; }}
h4 {{ font-size: 12pt; font-weight: bold; margin: 6pt 0 3pt 0; }}
h5 {{ font-size: 11pt; font-weight: bold; margin: 4pt 0 2pt 0; }}
h6 {{ font-size: 11pt; font-weight: bold; color: #555; margin: 4pt 0 2pt 0; }}
/* 表格（默认 auto 列宽；不使用 formatters 的 display:block/overflow-x:auto） */
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  table-layout: auto;
}}
td, th {{
  border: 1px solid #999;
  padding: 5px 8px;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
  word-break: break-word;
}}
th {{ background-color: #f0f0f0; font-weight: bold; }}
/* 代码 / 引用 / 列表 */
pre {{
  background-color: #f6f8fa;
  padding: 8px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}}
code {{ font-family: {fonts}; }}
blockquote {{ border-left: 3px solid #ccc; padding-left: 10px; color: #555; }}
ul, ol {{ padding-left: 22px; }}
a {{ color: #0645ad; text-decoration: none; }}
""".format(fonts=_PDF_FONT_STACK)


def _build_pdf_html(markdown_text: str) -> str:
    """构造 PDF 用完整 HTML 模板（静态模板 + markdown2 body + PDF 专用 CSS）。

    安全：markdown2 不解析外链图片；不传 base_url 给 WeasyPrint。
    """
    body = _strip_emoji_then_render_body(markdown_text)
    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <style>{_PDF_CSS}</style>\n"
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def _strip_emoji_then_render_body(markdown_text: str) -> str:
    """先剥 emoji（PDF 渲染专用），再用 markdown2 生成 body 片段。"""
    import markdown2  # lazy import：仅在 PDF 渲染路径才需要

    cleaned = strip_emoji_for_pdf(markdown_text)
    return markdown2.markdown(
        cleaned,
        extras=["tables", "fenced-code-blocks", "break-on-newline", "cuddled-lists"],
    )


def _prepare_weasyprint_env() -> None:
    """macOS 下自动把 Homebrew 的 glib 动态库路径加入 dyld 搜索路径。

    WeasyPrint 经 cffi 加载 ``libgobject-2.0-0``；macOS 上 brew 安装的库不在系统
    dyld 默认搜索路径内，需 ``DYLD_FALLBACK_LIBRARY_PATH`` 指向 ``/opt/homebrew/lib``
    （Apple Silicon）或 ``/usr/local/lib``（Intel），否则报
    ``cannot load library 'libgobject-2.0-0'``。本函数幂等探测并设置，让用户免手动
    配置环境变量；非 macOS 无副作用；找不到 brew 路径时静默返回（后续 import 给出明确错误）。
    """
    if platform.system() != "Darwin":
        return
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    existing = current.split(":") if current else []
    for candidate in _BREW_LIB_CANDIDATES:
        if not os.path.exists(os.path.join(candidate, _GOBJECT_MARKER)):
            continue
        if candidate in existing:
            return
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            f"{candidate}:{current}" if current else candidate
        )
        return


def markdown_to_pdf_file(markdown_text: str, output_path: str) -> Optional[str]:
    """将 Markdown 转为 PDF 文件（WeasyPrint 渲染）。

    Args:
        markdown_text: Markdown 原文（utf-8）。
        output_path: PDF 输出文件路径（完整路径；父目录不存在时自动创建）。

    Returns:
        ``output_path``（成功）或 ``None``（空输入 / 依赖缺失 / 渲染失败）。
        失败时不抛异常，调用方（service 层）处理降级为 HTTP 404。
    """
    if not markdown_text or not markdown_text.strip():
        logger.warning("[md2pdf] 空 Markdown，跳过")
        return None

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    # ---------- Semaphore 限流 ----------
    acquired = _pdf_lock.acquire(timeout=_PDF_LOCK_TIMEOUT)
    if not acquired:
        logger.warning("[md2pdf] Semaphore 获取超时（PDF 生成队列满），跳过")
        return None

    try:
        # ---------- macOS 环境自适应 + lazy import weasyprint ----------
        _prepare_weasyprint_env()
        try:
            from weasyprint import HTML
        except Exception as exc:  # ImportError / cffi 加载 libgobject 失败的 OSError 等
            logger.warning("[md2pdf] weasyprint 未就绪（%s），PDF 生成跳过", exc)
            return None

        # ---------- Markdown → 静态 HTML 模板（含 PDF 专用 CSS）----------
        # 不传 base_url，不加载远程资源。
        html = _build_pdf_html(markdown_text)

        # ---------- 渲染 ----------
        HTML(string=html).write_pdf(output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(
                "[md2pdf] 生成成功: %s (%.1f KB)",
                output_path,
                os.path.getsize(output_path) / 1024,
            )
            return output_path

        logger.warning("[md2pdf] WeasyPrint 渲染输出无效（空文件）")
        return None

    except Exception as exc:
        logger.warning("[md2pdf] PDF 生成失败: %s", exc)
        return None

    finally:
        _pdf_lock.release()
