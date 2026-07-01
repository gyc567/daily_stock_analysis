/**
 * 共享 PDF 下载 helper（按 docs/pdf-download-filename-plan.md §前端方案）。
 *
 * 职责：
 * 1. 从 `Content-Disposition` 解析 `filename*=UTF-8''...` / `filename="..."` / `filename=...`
 * 2. 支持中文 decode（`decodeURIComponent`）
 * 3. 解析失败时使用 fallback 文件名
 * 4. 统一 Blob URL 创建、点击下载和 revoke
 *
 * 三个 API wrapper（deepResearch / policyMinesweeper / supplyChainReports）改为复用，
 * 不再各自硬编码 `<a download>`。
 */

const FILENAME_FALLBACK_PREFIX = 'report'; // reserved for future fallback builder
void FILENAME_FALLBACK_PREFIX;

/**
 * 从 `Content-Disposition` header 解析出业务文件名。
 *
 * 兼容：
 * - `attachment; filename="中文名.pdf"`（ASCII，含中文时丢失）
 * - `attachment; filename*=UTF-8''%E4%B8%AD%E6%96%87.pdf`（RFC 5987）
 * - `attachment; filename="ascii.pdf"; filename*=UTF-8''...`（两个都有时优先 *）
 * - 无 header（fetch 异常或后端没设）
 */
export function parseContentDisposition(
  header: string | null | undefined,
  fallback: string,
): string {
  if (!header) {
    return fallback;
  }

  // RFC 5987: filename*=UTF-8''<percent-encoded>
  const starMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (starMatch) {
    try {
      return decodeURIComponent(starMatch[1].trim());
    } catch {
      // fall through to plain filename
    }
  }

  // Standard: filename="..." or filename=...
  const quotedMatch = header.match(/filename="([^"]+)"/i);
  if (quotedMatch) {
    return quotedMatch[1].trim();
  }
  const bareMatch = header.match(/filename=([^;]+)/i);
  if (bareMatch) {
    return bareMatch[1].trim();
  }

  return fallback;
}

/**
 * 触发浏览器下载 blob。
 *
 * @param blob 服务端响应的 PDF blob
 * @param preferredName 业务文件名（后端 Content-Disposition 解析得到，或 fallback）
 */
export function downloadBlob(blob: Blob, preferredName: string): void {
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = preferredName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}

/**
 * 通用 PDF 下载：从 URL fetch blob，解析业务文件名，触发下载。
 *
 * @param url PDF 下载端点
 * @param reportType 用于 fallback 文件名前缀（`deep_research` / `policy_minesweeper` / `supply_chain`）
 * @param reportId 用于 fallback 文件名主体
 */
export async function downloadPdfFromUrl(
  url: string,
  reportType: 'deep_research' | 'policy_minesweeper' | 'supply_chain',
  reportId: string,
): Promise<void> {
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    let backendDetail = '';
    try {
      const body = await response.json();
      const msg = body?.message ?? body?.detail;
      backendDetail = msg ? `: ${String(msg)}` : '';
    } catch {
      // 非 JSON 响应，忽略
    }
    throw new Error(
      `PDF 下载失败（${response.status}）${backendDetail}，请检查日志或稍后重试`,
    );
  }

  const blob = await response.blob();
  const fallback = `${reportType}_${reportId}.pdf`;
  const filename = parseContentDisposition(
    response.headers.get('content-disposition'),
    fallback,
  );
  downloadBlob(blob, filename);
}
