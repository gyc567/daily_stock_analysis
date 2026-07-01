# -*- coding: utf-8 -*-
"""批量生成A股深度投研报告PDF脚本。

用法:
    python scripts/batch_deep_research.py              # 分析所有自选股
    python scripts/batch_deep_research.py --stocks 600519,000001  # 指定股票
    python scripts/batch_deep_research.py --stocks 002617 --force  # 强制重新生成

输出:
    reports/deep_research_pdf/{股票名称}（{代码}）深度投研报告.pdf
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import setup_env, get_config
from src.services.deep_research_service import DeepResearchService
from src.storage import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "reports" / "deep_research_pdf"


def _get_stock_list(config: Any, args: argparse.Namespace) -> List[str]:
    """获取要分析的股票列表。"""
    if args.stocks:
        return [s.strip() for s in args.stocks.split(",") if s.strip()]
    config.refresh_stock_list()
    return config.stock_list


def _generate_report_for_stock(
    service: DeepResearchService,
    code: str,
    name: Optional[str] = None,
    force: bool = False,
) -> Optional[Dict[str, Any]]:
    """生成单只股票的深度投研报告。"""
    logger.info(f"开始生成深度投研报告: {code}")

    progress_info = {}

    def progress_callback(info: Dict[str, Any]):
        if info.get("type") == "progress":
            step = info.get("step", "?")
            total = info.get("total", "?")
            layer = info.get("layer", "")
            progress_info["current"] = f"{step}/{total} - {layer}"
            logger.info(f"  进度: {step}/{total} - {layer}")

    try:
        result = service.generate_report(
            raw_code=code,
            raw_name=name,
            progress_callback=progress_callback,
        )

        if result.get("report_id"):
            logger.info(
                f"  报告生成成功: {result['report_id']}, 质量评分: {result.get('quality_score')}"
            )
            return result
        else:
            logger.error(f"  报告生成失败: {result.get('error', '未知错误')}")
            return None
    except Exception as e:
        logger.error(f"  生成报告异常: {e}")
        return None


def _generate_pdf_for_report(
    service: DeepResearchService,
    report_id: str,
) -> Optional[str]:
    """生成单个报告的 PDF。"""
    try:
        pdf_path = service.get_pdf_path(report_id)
        if pdf_path:
            logger.info(f"  PDF生成成功: {pdf_path}")
            return pdf_path
        else:
            logger.error("  PDF生成失败")
            return None
    except Exception as e:
        logger.error(f"  PDF生成异常: {e}")
        return None


def _rename_pdf_to_named(
    original_pdf_path: str,
    stock_name: str,
    stock_code: str,
) -> Optional[str]:
    """将 PDF 重命名为 "{股票名称}（{代码}）深度投研报告.pdf" 格式。"""
    original_path = Path(original_pdf_path)
    if not original_path.exists():
        logger.error(f"  原始PDF不存在: {original_pdf_path}")
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    new_name = f"{stock_name}（{stock_code}）深度投研报告.pdf"
    new_path = OUTPUT_DIR / new_name

    try:
        import shutil

        shutil.copy2(original_path, new_path)
        logger.info(f"  PDF已保存为: {new_path}")
        return str(new_path)
    except Exception as e:
        logger.error(f"  重命名PDF失败: {e}")
        return None


def _find_existing_report_for_stock(
    code: str,
) -> Optional[str]:
    """查找股票最近生成的报告。"""
    db = get_db()
    rows, _ = db.get_deep_research_reports(stock_code=code, limit=1)
    if rows:
        return rows[0].id  # DeepResearchReport 使用 id 字段
    return None


def run_batch_deep_research(args: argparse.Namespace) -> Dict[str, Any]:
    """批量生成深度投研报告。"""
    setup_env()
    config = get_config()
    service = DeepResearchService()

    stock_codes = _get_stock_list(config, args)
    if not stock_codes:
        logger.error("没有配置自选股，请设置 STOCK_LIST")
        return {"success": 0, "failed": 0, "skipped": 0, "results": []}

    logger.info(f"=" * 60)
    logger.info(f"批量生成深度投研报告")
    logger.info(f"股票数量: {len(stock_codes)}")
    logger.info(f"强制重新生成: {args.force}")
    logger.info(f"=" * 60)

    results = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for i, code in enumerate(stock_codes, 1):
        logger.info(f"\n[{i}/{len(stock_codes)}] 处理股票: {code}")

        existing_report_id = _find_existing_report_for_stock(code)
        if existing_report_id and not args.force:
            logger.info(
                f"  跳过（已有报告 {existing_report_id}，使用 --force 强制重新生成）"
            )
            skipped_count += 1
            results.append(
                {"code": code, "status": "skipped", "report_id": existing_report_id}
            )
            continue

        start_time = time.time()

        result = _generate_report_for_stock(
            service=service,
            code=code,
            force=args.force,
        )

        if result and result.get("report_id"):
            pdf_path = _generate_pdf_for_report(service, result["report_id"])

            if pdf_path:
                named_pdf_path = _rename_pdf_to_named(
                    original_pdf_path=pdf_path,
                    stock_name=result.get("stock_name", code),
                    stock_code=code,
                )
                result["pdf_path"] = named_pdf_path

            success_count += 1
            result["status"] = "success"
            result["duration"] = round(time.time() - start_time, 1)
        else:
            failed_count += 1
            result = {
                "code": code,
                "status": "failed",
                "duration": round(time.time() - start_time, 1),
            }

        results.append(result)

        if i < len(stock_codes):
            wait_time = args.delay
            if wait_time > 0:
                logger.info(f"  等待 {wait_time} 秒后继续...")
                time.sleep(wait_time)

    summary = {
        "total": len(stock_codes),
        "success": success_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "results": results,
        "output_dir": str(OUTPUT_DIR),
    }

    logger.info(f"\n{'=' * 60}")
    logger.info(f"批量生成完成")
    logger.info(
        f"总计: {summary['total']}, 成功: {success_count}, 失败: {failed_count}, 跳过: {skipped_count}"
    )
    logger.info(f"PDF输出目录: {OUTPUT_DIR}")
    logger.info(f"{'=' * 60}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="批量生成A股深度投研报告PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/batch_deep_research.py
  python scripts/batch_deep_research.py --stocks 600519,000001
  python scripts/batch_deep_research.py --stocks 002617 --force
        """,
    )
    parser.add_argument(
        "--stocks",
        type=str,
        help="指定要分析的股票代码，逗号分隔",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成，即使已有报告",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="每只股票分析间隔（秒），默认5秒",
    )

    args = parser.parse_args()
    run_batch_deep_research(args)


if __name__ == "__main__":
    main()
