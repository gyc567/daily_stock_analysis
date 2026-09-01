# -*- coding: utf-8 -*-
"""
Annual Report Data Provider.

Fetches annual report text from cninfo (巨潮资讯网).
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AnnualReportProvider:
    """Provider for annual report data from cninfo"""

    def __init__(self):
        self._cache: Dict[str, str] = {}

    def get_annual_report_text(
        self, stock_code: str, year: Optional[int] = None
    ) -> Optional[str]:
        """
        Get annual report text for a stock.

        Args:
            stock_code: Stock code (e.g., 600519)
            year: Report year

        Returns:
            Annual report text or None
        """
        if year is None:
            from data_provider.supply_chain import latest_fiscal_year

            fiscal_year = latest_fiscal_year()
        else:
            fiscal_year = year
        cache_key = f"{stock_code}_{fiscal_year}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        text = self._fetch_from_cninfo(stock_code, fiscal_year)
        if text:
            self._cache[cache_key] = text

        return text

    def _fetch_from_cninfo(self, stock_code: str, year: int) -> Optional[str]:
        """Fetch annual report from cninfo"""
        try:
            import requests

            ts_code = self._normalize_ts_code(stock_code)
            url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {
                "stockCode": ts_code.replace(".SH", "").replace(".SZ", ""),
                "orgId": "",
                "isHLtitle": "true",
                "pageSize": 30,
                "pageNum": 1,
                "tabName": "fulltext",
                "secid": "",
                "category": "category_ndbg_bg;",
                "plate": "",
                "seDate": f"{year}-01-01 ~ {year}-12-31",
                "sortName": "",
                "sortType": "",
                "isHL": "true",
            }

            response = requests.post(url, data=data, headers=headers, timeout=10)
            if response.status_code != 200:
                return None

            result = response.json()
            announcements = result.get("announcements", [])

            for ann in announcements:
                if "年度报告" in ann.get("announcementTitle", ""):
                    return self._extract_report_content(ann)

            logger.info(
                f"[AnnualReportProvider] No annual report found for {stock_code} {year}"
            )
            return None

        except Exception as e:
            logger.warning(f"[AnnualReportProvider] Failed to fetch: {e}")
            return None

    def _extract_report_content(self, announcement: Dict[str, Any]) -> Optional[str]:
        """Extract text content from announcement"""
        try:
            pdf_url = announcement.get("adjunctUrl", "")
            if not pdf_url:
                return None

            full_url = f"https://www.cninfo.com.cn{pdf_url}"

            import requests

            response = requests.get(full_url, timeout=15)
            if response.status_code != 200:
                return None

            content = response.content

            if pdf_url.endswith(".pdf"):
                text = self._extract_pdf_text(content)
            else:
                text = content.decode("utf-8", errors="ignore")

            return self._clean_text(text)

        except Exception as e:
            logger.warning(f"[AnnualReportProvider] Failed to extract content: {e}")
            return None

    def _extract_pdf_text(self, content: bytes, max_pages: int = 50) -> str:
        """Extract text from PDF bytes.

        Args:
            content: PDF file bytes
            max_pages: Maximum pages to scan (default 50, enough for 经营情况讨论与分析 section)
        """
        try:
            import io
            from pypdf import PdfReader  # type: ignore[import-not-found]

            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            total_pages = len(reader.pages)
            pages_to_scan = min(max_pages, total_pages)
            for page in reader.pages[:pages_to_scan]:
                text_parts.append(page.extract_text())
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("[AnnualReportProvider] pypdf not installed")
            return ""
        except Exception as e:
            logger.warning(f"[AnnualReportProvider] PDF extraction failed: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        return text.strip()

    def _normalize_ts_code(self, stock_code: str) -> str:
        """Convert stock code to TS format"""
        code = stock_code.strip().upper()
        if "." in code:
            return code
        if code.startswith("60") or code.startswith("688"):
            return f"{code}.SH"
        return f"{code}.SZ"


def extract_capacity_disclosures(text: str) -> list[dict[str, Any]]:
    """从年报正文中提取产能相关段落。

    用于 §10.b 产能展望功能。

    Args:
        text: 年报正文文本

    Returns:
        产能披露段落列表，每项包含 keyword 和 content
    """
    if not text:
        return []

    # 产能相关关键词模式
    capacity_patterns = [
        r"产能利用率[：:][^\n]{10,200}",
        r"设计产能[：:][^\n]{10,200}",
        r"实际产量[：:][^\n]{10,200}",
        r"扩产[^\n]{10,200}",
        r"在建工程[^\n]{10,200}",
        r"产销率[：:][^\n]{10,200}",
        r"产能爬坡[^\n]{10,200}",
        r"新增产能[^\n]{10,200}",
    ]

    disclosures = []
    for pattern in capacity_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # 清理空白
            cleaned = re.sub(r"\s+", " ", match).strip()
            if len(cleaned) >= 10:
                disclosures.append({
                    "keyword": cleaned[:30],
                    "content": cleaned[:500],  # 截断避免过长
                })

    return disclosures
