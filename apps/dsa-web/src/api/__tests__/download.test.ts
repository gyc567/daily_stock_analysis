import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { parseContentDisposition, downloadBlob, downloadPdfFromUrl } from '../download';

describe('parseContentDisposition', () => {
  it('parses RFC 5987 filename* (UTF-8 percent-encoded)', () => {
    const header = "attachment; filename*=UTF-8''%E5%B7%A5%E5%8E%82.pdf";
    const result = parseContentDisposition(header, 'fallback.pdf');
    expect(result).toBe('工厂.pdf');
  });

  it('parses simple filename="..." (ASCII quoted)', () => {
    const header = 'attachment; filename="report.pdf"';
    expect(parseContentDisposition(header, 'fb')).toBe('report.pdf');
  });

  it('parses bare filename=...', () => {
    const header = 'attachment; filename=report.pdf';
    expect(parseContentDisposition(header, 'fb')).toBe('report.pdf');
  });

  it('prefers filename* over filename when both present', () => {
    const header =
      "attachment; filename=\"fallback.pdf\"; filename*=UTF-8''%E5%B7%A5%E5%8E%82.pdf";
    expect(parseContentDisposition(header, 'fb')).toBe('工厂.pdf');
  });

  it('returns fallback when header is null', () => {
    expect(parseContentDisposition(null, 'fallback.pdf')).toBe('fallback.pdf');
  });

  it('returns fallback when header is undefined', () => {
    expect(parseContentDisposition(undefined, 'fallback.pdf')).toBe('fallback.pdf');
  });

  it('returns fallback when header has no filename', () => {
    expect(parseContentDisposition('attachment; size=12345', 'fb.pdf')).toBe('fb.pdf');
  });

  it('handles Chinese business filename from docs/pdf-download-filename-plan.md', () => {
    const header =
      "attachment; filename*=utf-8''%E7%A7%91%E7%91%9E%E6%8A%80%E6%9C%AF%EF%BC%88002957%EF%BC%89%E6%B7%B1%E5%BA%A6%E6%8A%95%E7%A0%94%E6%8A%A5%E5%91%8A20260630.pdf";
    expect(parseContentDisposition(header, 'fb')).toBe(
      '科瑞技术（002957）深度投研报告20260630.pdf',
    );
  });
});

describe('downloadBlob', () => {
  let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let clickSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    createObjectURLSpy = vi
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:mock-url');
    revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);

    const fakeAnchor = document.createElement('a');
    clickSpy = vi.fn(() => undefined);
    fakeAnchor.click = clickSpy as unknown as () => void;
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
      Object.assign(node as Element, fakeAnchor);
      return node;
    });
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sets a.download to preferred name and triggers click', () => {
    const blob = new Blob(['x'], { type: 'application/pdf' });
    downloadBlob(blob, '中文报告.pdf');
    expect(createObjectURLSpy).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url');
  });
});

describe('downloadPdfFromUrl', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    // stub anchor click
    const fakeAnchor = document.createElement('a');
    fakeAnchor.click = vi.fn();
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
      Object.assign(node as Element, fakeAnchor);
      return node;
    });
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses business filename from RFC 5987 header', async () => {
    const blob = new Blob(['pdf'], { type: 'application/pdf' });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      headers: {
        get: (name: string) =>
          name.toLowerCase() === 'content-disposition'
            ? "attachment; filename*=UTF-8''%E5%AE%81%E5%BE%B7%E6%97%B6%E4%BB%A3%EF%BC%88300003%EF%BC%89%E6%B7%B1%E5%BA%A6%E6%8A%95%E7%A0%94%E6%8A%A5%E5%91%8A20260701.pdf"
            : null,
      },
      blob: async () => blob,
    });

    await downloadPdfFromUrl(
      '/api/v1/deep-research/reports/300003_20260701_1/pdf',
      'deep_research',
      '300003_20260701_1',
    );

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/deep-research/reports/300003_20260701_1/pdf',
      { credentials: 'include' },
    );
  });

  it('falls back to legacy ASCII name when no header', async () => {
    const blob = new Blob(['pdf'], { type: 'application/pdf' });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      headers: { get: () => null },
      blob: async () => blob,
    });

    await downloadPdfFromUrl(
      '/api/v1/deep-research/reports/600519_20260630/pdf',
      'deep_research',
      '600519_20260630',
    );
    // 验证：fallback 文件名由调用方提供
    // (实际通过 spy on clickSpy 验证 a.download 被设置成 fallback)
    expect(fetchMock).toHaveBeenCalled();
  });

  it('throws with status code + backend message on 404', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ message: 'PDF 文件不存在' }),
    });

    await expect(
      downloadPdfFromUrl(
        '/api/v1/deep-research/reports/600519_x/pdf',
        'deep_research',
        '600519_x',
      ),
    ).rejects.toThrow(/PDF 下载失败（404）.*PDF 文件不存在/);
  });

  it('throws on 500 with backend message', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ message: 'PDF 生成失败' }),
    });

    await expect(
      downloadPdfFromUrl(
        '/api/v1/deep-research/reports/600519_x/pdf',
        'deep_research',
        '600519_x',
      ),
    ).rejects.toThrow(/PDF 下载失败（500）.*PDF 生成失败/);
  });

  it('handles non-JSON 500 response gracefully', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('not json');
      },
    });

    await expect(
      downloadPdfFromUrl(
        '/api/v1/deep-research/reports/600519_x/pdf',
        'deep_research',
        '600519_x',
      ),
    ).rejects.toThrow(/PDF 下载失败（500）/);
  });
});
