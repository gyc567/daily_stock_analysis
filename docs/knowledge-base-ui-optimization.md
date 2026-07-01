# 知识库页面 UI 审计与优化方案

## 1. 审计结论

当前知识库页面已经具备 P0 闭环的基础能力：搜索、文档列表、手动创建、文件上传、详情查看、复制和删除。但页面信息架构仍偏“功能分区”，用户必须在搜索、列表、创建之间切换，导致知识库最核心的“资料入库 -> 检索 -> 预览引用”路径不够连续。

本次 UI 优化目标不是扩大功能面，而是把现有能力收敛成一个稳定、可验证、与后端契约一致的工作台：

- 顶部统一承载搜索和新增入口，减少 Tab 切换。
- 主区域默认展示文档与搜索结果，详情使用 Modal 或右侧面板，不覆盖上下文。
- 新增、上传、URL 入库、删除、复制都给出一致的 loading、成功和失败反馈。
- 页面组件拆分到可维护边界，但不引入独立状态库。
- 与 `docs/knowledge-base-plan.md` 的 P0 边界保持一致：先做好私有资料库、关键词检索和报告引用，不在本轮引入知识库聊天或向量 RAG。

## 2. 当前问题

### 2.1 信息架构

| 问题 | 严重度 | 影响 | 优化方向 |
| --- | --- | --- | --- |
| 搜索、列表、创建分离在三个视图中 | High | 用户创建文档后需要切回搜索或列表，流程断开 | 改为顶部统一输入区 + 快捷新增入口 |
| 左侧边栏承载 Tab 和局部内容 | Medium | 桌面端占用横向空间，移动端又变为底部 Tab，交互模型不一致 | 移除知识库页内 Tab，保留全局导航即可 |
| 详情在主区域替换列表/搜索结果 | Medium | 用户查看详情后失去原始结果上下文 | 用详情 Modal 或右侧详情面板 |
| 上传入口藏在创建表单底部 | Medium | 文件入库是高频入口，但路径过深 | 顶部放独立上传按钮 |
| URL 入库 API 已存在但页面未暴露独立入口 | Medium | 用户无法直接使用 `/documents/url` 能力 | 增加 URL 创建 Modal |

### 2.2 反馈与错误处理

| 问题 | 严重度 | 影响 | 优化方向 |
| --- | --- | --- | --- |
| `listDocuments`、`deleteDocument`、`getDocument` 失败被静默忽略 | High | 用户无法判断数据是否真实刷新或操作是否成功 | 统一 Toast + 局部错误状态 |
| 上传失败使用 `window.alert` | Medium | 反馈风格与页面不一致，移动端体验差 | 改为非阻塞 Toast |
| 复制内容没有成功/失败提示 | Low | 用户无法确认剪贴板操作是否完成 | 复制后 Toast，失败时提示权限问题 |
| 搜索失败在 API 层转换为 `available=false`，页面未展示 `message` | Medium | 用户只看到空结果，无法区分无命中和服务不可用 | 空状态区展示不可用原因 |
| 删除成功后只刷新列表，搜索结果不一定同步 | Medium | 用户可能看到已删除文档的旧搜索命中 | 删除后同步清理选中文档、列表和当前搜索结果 |

### 2.3 表单与契约

| 问题 | 严重度 | 影响 | 优化方向 |
| --- | --- | --- | --- |
| 前端未明确展示标题、内容、标签、top_k 等后端限制 | Medium | 用户提交后才收到 422，体验滞后 | 在表单侧做轻量提示和提交前校验 |
| 标签只支持逗号输入 | Low | 容易出现空格、重复标签、超过 20 个标签 | 提供标签 Chip 输入或至少预览解析结果 |
| 文件上传缺少大小、类型、解析结果提示 | Medium | 用户不知道 PDF/Markdown/text 的边界和解析状态 | 上传前展示支持类型和大小限制，上传后展示 chunk 数和 hash |
| URL 创建缺少安全边界提示 | Medium | 用户可能误以为任意地址都能抓取 | 提示仅支持 http/https，内网地址会被拒绝 |

### 2.4 可访问性与响应式

| 问题 | 严重度 | 影响 | 优化方向 |
| --- | --- | --- | --- |
| 图标按钮依赖 `title` | Medium | 键盘和屏幕阅读器体验不足 | 增加 `aria-label`，并保持可见焦点 |
| Modal 方案未定义焦点管理 | High | 键盘用户可能无法稳定关闭或返回触发按钮 | 使用焦点陷阱、Esc 关闭、关闭后恢复焦点 |
| 移动端底部 Tab 占用空间 | Medium | 与页面主操作区割裂，且容易遮挡内容 | 移动端保留顶部搜索，新增入口改为横向操作条 |
| 文档卡片 hover 才出现关键操作 | Medium | 触屏设备无法发现删除/复制等操作 | 移动端始终显示更多菜单或底部操作行 |

### 2.5 技术债务

当前 `apps/dsa-web/src/pages/KnowledgeBasePage.tsx` 约 690 行，混合了 API 调用、状态管理、搜索结果渲染、文档列表、创建表单、上传、详情和删除逻辑。继续在单文件内追加 Modal 和 URL 表单会放大维护成本。

建议拆分时保持页面级状态在容器内，不引入 Zustand 或新的全局 store。P0 组件拆分只服务于可读性和测试，不做无关抽象。

## 3. 优化原则

1. **资料入库和搜索同屏**：用户进入知识库后，第一屏就能搜索、上传、粘贴文本或输入 URL。
2. **不丢上下文**：详情、创建、URL 输入等临时任务使用 Modal 或右侧面板，不替换列表和搜索结果。
3. **错误可见但不阻断**：API 失败、搜索不可用、解析失败、复制失败都要给出明确反馈；知识库不可用时不影响其他页面。
4. **契约先行**：前端文案和校验必须对齐 Pydantic/API 限制，不在 UI 中承诺后端没有提供的能力。
5. **P0 克制**：不新增知识库聊天、不新增向量检索 UI、不新增复杂筛选器；这些放到 P1/P2。

## 4. 目标布局

### 4.1 桌面端

```text
┌────────────────────────────────────────────────────────────────┐
│ 知识库                                                         │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ 搜索知识库、股票、行业、主题...                         [搜] │ │
│ └────────────────────────────────────────────────────────────┘ │
│ [上传文件] [粘贴文本] [从 URL 创建]          状态：23 篇文档   │
├────────────────────────────────────────────────────────────────┤
│ 筛选/排序条：全部来源  全部标签  最近更新                      │
├───────────────────────────────────────┬────────────────────────┤
│ 文档/搜索结果网格或列表                 │ 详情面板（可选）        │
│ - 文档标题、来源、标签、chunk 数        │ - 标题/来源/标签        │
│ - 内容摘要或命中片段                    │ - chunks / 命中片段     │
│ - 预览、复制、删除                      │ - 复制、打开来源        │
└───────────────────────────────────────┴────────────────────────┘
```

详情面板可以先用 Modal 实现；如果后续需要高频对照搜索结果，再升级为右侧面板。

### 4.2 移动端

```text
┌──────────────────────────────┐
│ 知识库                       │
│ ┌──────────────────────────┐ │
│ │ 搜索...                  │ │
│ └──────────────────────────┘ │
│ [上传] [文本] [URL]          │
├──────────────────────────────┤
│ 文档/搜索结果单列列表         │
│ 关键操作通过更多菜单进入      │
└──────────────────────────────┘
```

移动端不再使用知识库页内底部 Tab，避免遮挡内容和引入与桌面不同的导航模型。

## 5. 核心交互

### 5.1 搜索

- 输入框支持回车和搜索按钮触发。
- 空 query 不请求后端，展示“输入关键词搜索知识库”。
- 搜索中禁用按钮并显示 loading。
- `available=false` 时展示 API 返回的 `message`，文案示例：`知识库暂不可用：{message}`。
- 搜索结果展示：
  - 文档标题
  - 命中片段
  - 相似度或相关性分数
  - 来源类型
  - 来源 URL（如果存在）
  - `validation_status` 对应的校验状态

### 5.2 上传文件

- 顶部“上传文件”按钮直接打开文件选择器。
- 支持类型与后端保持一致：`.pdf`、`.md`、`.markdown`、`.txt`。
- 上传前展示文件名、大小和可选标签。
- 上传成功后 Toast 展示：文档标题、source_type、chunk_count。
- 上传失败后 Toast 展示服务端错误信息，不使用 `window.alert`。
- 上传成功后刷新文档列表；如果当前存在搜索 query，可提示用户重新搜索，而不是自动覆盖搜索结果。

### 5.3 粘贴文本创建

使用 Modal 承载文本创建表单：

| 字段 | 要求 |
| --- | --- |
| 标题 | 必填，1-120 字符 |
| 内容类型 | `markdown` / `text` |
| 标签 | 最多 20 个，每个 1-40 字符 |
| 来源 URL | 可选，仅 http/https |
| 内容 | 必填，1-200000 字符 |

提交成功后关闭 Modal、刷新列表，并给出成功 Toast。提交失败时保留输入内容，不清空表单。

### 5.4 从 URL 创建

使用独立 URL Modal，调用 `knowledgeBaseApi.createFromUrl`，不要复用文本创建接口伪造 URL 文档。

| 字段 | 要求 |
| --- | --- |
| URL | 必填，仅 http/https |
| 标题 | 可选，未填时由后端推断或使用 URL |
| 标签 | 可选，最多 20 个 |

Modal 内需要提示：

- URL 抓取是 best-effort。
- 内网、localhost、file 协议和不可访问地址会被拒绝。
- 抓取失败时按后端返回状态展示，不把失败伪装成成功。

### 5.5 文档列表与卡片

P0 建议使用列表优先、卡片次之。知识库文档是工作台资产，用户更需要扫描标题、来源、更新时间、标签和 chunk 数，而不是大卡片浏览。

每条文档至少展示：

- 标题
- 来源类型：text / markdown / pdf / url
- chunk 数
- 更新时间或创建时间
- 标签
- 来源 URL 图标（如果存在）
- 操作：预览、复制、删除

删除需要二次确认。删除成功后：

- 从文档列表中移除。
- 如果当前详情是该文档，关闭详情。
- 如果搜索结果包含该文档，移除对应命中或提示结果已过期。

### 5.6 详情查看

详情使用 Modal 或右侧面板，展示：

- 标题、来源类型、来源 URL、标签、chunk_count、created_at、updated_at。
- chunks 列表，保留换行。
- 每个 chunk 支持复制。
- 来源 URL 使用 `target="_blank"` 和 `rel="noopener noreferrer"`。

详情加载失败必须展示错误状态，并允许重试。

## 6. 组件拆分建议

建议目录：

```text
apps/dsa-web/src/pages/KnowledgeBasePage.tsx
apps/dsa-web/src/components/knowledge/KnowledgeToolbar.tsx
apps/dsa-web/src/components/knowledge/KnowledgeDocumentList.tsx
apps/dsa-web/src/components/knowledge/KnowledgeDocumentItem.tsx
apps/dsa-web/src/components/knowledge/KnowledgeSearchResults.tsx
apps/dsa-web/src/components/knowledge/KnowledgeDocumentDetail.tsx
apps/dsa-web/src/components/knowledge/KnowledgeCreateTextModal.tsx
apps/dsa-web/src/components/knowledge/KnowledgeCreateUrlModal.tsx
apps/dsa-web/src/components/knowledge/KnowledgeUploadDialog.tsx
```

拆分边界：

| 组件 | 职责 |
| --- | --- |
| `KnowledgeBasePage` | 页面数据流、API 调用、当前 query、选中文档、Toast 状态 |
| `KnowledgeToolbar` | 搜索输入、上传/文本/URL 快捷入口 |
| `KnowledgeDocumentList` | 文档列表、空状态、列表 loading |
| `KnowledgeSearchResults` | 搜索结果、不可用状态、无命中状态 |
| `KnowledgeDocumentDetail` | 文档详情、chunk 展示、复制 |
| `KnowledgeCreateTextModal` | 文本文档表单和前端轻量校验 |
| `KnowledgeCreateUrlModal` | URL 创建表单和安全边界提示 |
| `KnowledgeUploadDialog` | 文件选择、标签、上传确认 |

公共 Modal/Toast 组件如仓库已有可复用实现，应优先复用；没有再新增通用组件。不要在优化中引入独立 UI 框架。

## 7. 状态管理

P0 继续使用 `useState` 和 `useCallback` 即可。建议把状态按语义分组，避免继续扩散：

```typescript
type KnowledgeViewState = {
  query: string;
  selectedDocumentId: string | null;
  activeDialog: 'text' | 'url' | 'upload' | null;
};

type KnowledgeAsyncState = {
  documentsLoading: boolean;
  searchLoading: boolean;
  detailLoading: boolean;
  creating: boolean;
  uploading: boolean;
  deletingId: string | null;
};
```

状态规则：

- 列表数据和搜索结果分开存储，不互相覆盖。
- 搜索 query 为空时展示文档列表；有搜索结果时展示搜索结果。
- 删除、上传、创建成功后刷新列表。
- 搜索失败不清空最后一次成功结果，除非用户清空 query；同时展示错误提示。
- `navigator.clipboard` 失败要捕获并提示。

## 8. 可访问性要求

- 所有图标按钮必须有 `aria-label`。
- Modal 打开后焦点进入 Modal，Esc 关闭，关闭后焦点回到触发按钮。
- 删除确认按钮文案必须明确包含文档标题或“删除文档”。
- loading 按钮使用 `disabled`，避免重复提交。
- 表单错误靠近字段展示，并同步在 Toast 或 Modal 顶部总结。
- 操作菜单不能只依赖 hover；移动端必须可点击发现。

## 9. 视觉与响应式要求

- 页面是工作台，不做营销式 Hero。
- 避免嵌套卡片；列表容器可以是一个面板，列表项只做轻量分隔。
- 保持与现有深色主题、`cyan` 强调色、`bg-card/82`、`border-white/8` 等视觉语言一致。
- 桌面端内容宽度优先给列表和详情，不保留知识库页内 256px 左侧栏。
- 移动端按钮文本要避免溢出，必要时使用图标 + 短文本。
- 文档标题、标签、URL 都要处理长文本截断。

## 10. 实施优先级

| 阶段 | 范围 | 说明 |
| --- | --- | --- |
| P0.1 | 统一顶部工具栏 | 搜索框 + 上传/文本/URL 三个入口，移除页内 Tab |
| P0.2 | 反馈统一 | Toast、错误展示、复制反馈、删除反馈 |
| P0.3 | URL Modal | 接入 `createFromUrl`，展示安全边界和失败原因 |
| P0.4 | 详情 Modal/面板 | 查看详情不覆盖列表/搜索结果 |
| P0.5 | 组件拆分 | 控制 `KnowledgeBasePage.tsx` 复杂度，保持页面容器清晰 |
| P1 | 筛选与排序 | 来源类型、标签、最近更新；仅在 P0 稳定后做 |
| P1 | 召回质量展示 | validation_status、引用状态、报告关联入口 |

## 11. 验收标准

- [ ] 进入页面后不需要切换 Tab 即可搜索、上传、粘贴文本、从 URL 创建。
- [ ] 搜索成功、无结果、服务不可用、请求失败四种状态可区分。
- [ ] 文档创建成功后关闭创建 Modal，列表刷新，输入状态被正确清理。
- [ ] 文档创建失败后保留用户输入，并展示字段级或表单级错误。
- [ ] 文件上传成功展示 chunk 数和 source_type，失败不使用 `window.alert`。
- [ ] URL 创建调用 `/documents/url`，不是走文本创建接口。
- [ ] 删除有二次确认，成功后列表、详情和搜索结果状态一致。
- [ ] 复制成功/失败都有反馈。
- [ ] 详情查看不丢失原列表或搜索上下文。
- [ ] 移动端无底部 Tab 遮挡，主要操作在顶部可达。
- [ ] 所有图标按钮具备 `aria-label`，Modal 支持 Esc 关闭和焦点恢复。

## 12. 验证矩阵

### 12.1 前端本地验证

```bash
cd apps/dsa-web
npm run lint
npm run build
```

### 12.2 关键人工验收路径

1. 打开 `/knowledge-base`。
2. 输入关键词搜索，确认 loading、命中、无命中状态。
3. 粘贴文本创建文档，确认列表刷新和详情可打开。
4. 上传 `.txt` 或 `.md` 文件，确认成功反馈包含 chunk 数。
5. 输入 URL 创建文档，确认失败时展示后端错误。
6. 复制搜索片段和详情 chunk，确认有反馈。
7. 删除文档，确认列表、详情、搜索结果一致。
8. 在移动端宽度检查顶部操作区、列表项、Modal 和长标题截断。

### 12.3 回归关注点

- API 路径仍使用 `apps/dsa-web/src/api/knowledgeBase.ts` 中的封装。
- 不改变后端 Pydantic schema 和路由契约。
- 不影响供应链分析、深度投研等报告集成路径。
- 不新增 `.env` 配置；若后续 UI 需要新配置，必须同步 `.env.example` 和相关文档。

## 13. 回滚方案

- UI 优化应集中在 `apps/dsa-web/src/pages/KnowledgeBasePage.tsx` 和 `components/knowledge/`，回滚时可恢复原页面入口。
- API 封装不做破坏性重命名，避免影响后续报告集成。
- 如果 URL Modal 或上传 Dialog 出现问题，可以先隐藏对应按钮，保留搜索和文档列表。
- 知识库后端保持 fail-open；前端不可用只展示错误状态，不影响其他页面。
