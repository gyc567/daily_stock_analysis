import { expect, test, type Page } from '@playwright/test';

// ADMIN_AUTH_ENABLED=false 时无需登录，直接验证郑希投研页 UI 与端到端问答。

async function attachScreenshot(
  page: Page,
  testInfo: { outputPath: (name: string) => string },
  name: string,
) {
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: 'image/png' });
}

test.describe('郑希投研分析', () => {
  test('郑希页结构渲染正确', async ({ page }, testInfo) => {
    await page.goto('/zhengxi');
    await page.waitForLoadState('domcontentloaded');

    // 页面骨架（data-testid 与 ZhengxiChatPage 一致）
    await expect(page.getByTestId('zhengxi-workspace')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId('zhengxi-session-list-scroll')).toBeVisible();
    await expect(page.getByTestId('zhengxi-message-scroll')).toBeVisible();

    // 标题与副标题（exact 避免 "郑希投研" 子串匹配到空态 h3 "郑希投研分析"）
    await expect(page.getByRole('heading', { name: '郑希投研', exact: true })).toBeVisible();

    // 侧栏导航项存在
    await expect(page.getByRole('link', { name: '郑希投研' })).toBeVisible();

    // 输入框
    const input = page.getByPlaceholder(/郑希怎么看光通信/);
    await expect(input).toBeVisible({ timeout: 5_000 });

    // 发送按钮
    await expect(page.getByRole('button', { name: '发送' })).toBeVisible();

    await attachScreenshot(page, testInfo, 'zhengxi-empty-zh');
  });

  test('郑希页空态展示快捷问题', async ({ page }) => {
    await page.goto('/zhengxi');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByTestId('zhengxi-workspace')).toBeVisible({ timeout: 10_000 });

    // 空态标题 + 至少一个快捷问题按钮
    await expect(page.getByText('郑希投研分析')).toBeVisible();
    await expect(page.getByRole('button', { name: /光通信|持仓|打分|投资方法/ }).first()).toBeVisible();
  });

  test('发送问题后收到流式回答（真实 LLM）', async ({ page }, testInfo) => {
    await page.goto('/zhengxi');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByTestId('zhengxi-workspace')).toBeVisible({ timeout: 10_000 });

    const input = page.getByPlaceholder(/郑希怎么看光通信/);
    const prompt = '郑希怎么看光通信？请用一句话概括。';
    await input.fill(prompt);
    await page.getByRole('button', { name: '发送' }).click();

    // 用户消息立即出现
    await expect(page.locator('p').filter({ hasText: prompt }).last()).toBeVisible({ timeout: 5_000 });

    // 等待 AI 回答气泡渲染（.chat-bubble-ai 只用于 assistant 消息，区别于 loading 气泡）
    const aiBubble = page.locator('.chat-bubble-ai').first();
    await expect(aiBubble).toBeVisible({ timeout: 120_000 });
    // 验证含 AI 独有的实质回答内容（不会匹配到用户输入的"光通信"）
    await expect(aiBubble).toContainText(/中国证券报|光模块|数据传输|原话|通胀/);

    await attachScreenshot(page, testInfo, 'zhengxi-answer-zh');
  });
});
