import type { UiLanguage } from '../i18n/uiText';

export type SettingsChannelProtocol =
  | 'openai'
  | 'deepseek'
  | 'gemini'
  | 'anthropic'
  | 'vertex_ai'
  | 'ollama'
  | string;

export type NotificationTestErrorCode =
  | 'config_missing'
  | 'config_invalid'
  | 'network_error'
  | 'timeout'
  | 'http_error'
  | 'auth_error'
  | string;

const PROTOCOL_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    openai: 'OpenAI 兼容协议',
    deepseek: 'DeepSeek',
    gemini: 'Gemini',
    anthropic: 'Anthropic',
    vertex_ai: 'Vertex AI',
    ollama: 'Ollama',
  },
  en: {
    openai: 'OpenAI Compatible',
    deepseek: 'DeepSeek',
    gemini: 'Gemini',
    anthropic: 'Anthropic',
    vertex_ai: 'Vertex AI',
    ollama: 'Ollama',
  },
};

const CAPABILITY_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    json: 'JSON 输出',
    tools: '工具调用',
    stream: '流式输出',
    vision: '视觉能力',
  },
  en: {
    json: 'JSON output',
    tools: 'Tool calling',
    stream: 'Streaming',
    vision: 'Vision',
  },
};

const CAPABILITY_HINTS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    json: '检测 JSON 格式输出（response_format）是否可用。',
    tools: '检测函数调用（function/tool calling）是否可用。',
    stream: '检测流式输出是否能返回有效数据块。',
    vision: '检测当前模型是否接受 image_url 输入。',
  },
  en: {
    json: 'Checks whether JSON output (response_format) is available.',
    tools: 'Checks whether function/tool calling is available.',
    stream: 'Checks whether streaming returns usable chunks.',
    vision: 'Checks whether the model accepts image_url input.',
  },
};

const STAGE_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    model_discovery: '模型列表获取',
    chat_completion: '模型调用',
    response_parse: '响应解析',
    capability_json: 'JSON 能力',
    capability_tools: '工具调用能力',
    capability_stream: '流式输出能力',
    capability_vision: '视觉能力',
  },
  en: {
    model_discovery: 'Model discovery',
    chat_completion: 'Chat completion',
    response_parse: 'Response parse',
    capability_json: 'JSON capability',
    capability_tools: 'Tools capability',
    capability_stream: 'Stream capability',
    capability_vision: 'Vision capability',
  },
};

const CHANNEL_STATUS_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    connected: '连接正常',
    failed: '连接失败',
    testing: '测试中',
    missing_key: '未填写 API Key',
  },
  en: {
    connected: 'Connected',
    failed: 'Connection failed',
    testing: 'Testing',
    missing_key: 'API key missing',
  },
};

const NOTIFICATION_ERROR_CODE_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    config_missing: '配置不完整',
    config_invalid: '配置无效',
    network_error: '网络异常',
    timeout: '请求超时',
    http_error: 'HTTP 错误',
    auth_error: '鉴权失败',
    http_500: 'HTTP 错误',
    http_502: 'HTTP 错误',
    http_503: 'HTTP 错误',
    http_504: 'HTTP 错误',
  },
  en: {
    config_missing: 'Configuration missing',
    config_invalid: 'Configuration invalid',
    network_error: 'Network error',
    timeout: 'Request timeout',
    http_error: 'HTTP error',
    auth_error: 'Authentication failed',
    http_500: 'HTTP error',
    http_502: 'HTTP error',
    http_503: 'HTTP error',
    http_504: 'HTTP error',
  },
};

const CHANNEL_LABEL_OVERRIDES: Record<UiLanguage, Record<string, string>> = {
  zh: {
    wechat: '企业微信',
    feishu: '飞书 Webhook',
    email: '邮件',
    custom: '自定义 Webhook',
    serverchan3: 'Server酱 3',
  },
  en: {
    wechat: 'WeCom',
    feishu: 'Feishu Webhook',
    email: 'Email',
    custom: 'Custom Webhook',
    serverchan3: 'ServerChan 3',
  },
};

export const SETTINGS_TEXT = {
  zh: {
    unknownOption: '未知选项',
    unknownValue: '未知值',
    rawValueSuffix: '（原始值：{value}）',
    keyTooltip: 'API 密钥（Key）',
    channelDeleteTooltip: '删除渠道',
    channelKeyMissing: '未填写 Key',
    modelsConfigured: '已配置 {count} 个模型',
    noModelsConfigured: '尚未配置模型',
    save: '保存',
    saving: '保存中…',
    fetchModelsHint: '支持 /models 接口的 OpenAI 兼容渠道可自动拉取模型列表。',
    modelDiscoveryUnsupported: '当前仅对 OpenAI 兼容协议和 DeepSeek 渠道提供自动模型发现功能。',
    modelProviderMismatch: '模型服务商前缀与当前渠道不匹配。',
    saveChannel: '保存渠道配置',
    saveAi: '保存 AI 配置',
    testModelPrefix: '本次测试模型：{model}。',
    testDefaultScope: '基础连接测试默认只测试模型列表中的第一个模型。',
    capabilitySummary: '能力检测完成：通过 {passed} 项，失败 {failed} 项，跳过 {skipped} 项',
    rawErrorPrefix: '原始错误',
    rawMessagePrefix: '原始摘要',
    yamlRoutingHint: '检测到已配置高级模型路由 YAML：此处仅管理渠道条目和基础连接信息；运行时主模型、备用模型、视觉模型和采样温度仍由下方通用字段决定。如果 YAML 解析成功，则以其中的路由和可用模型声明为准，本配置不会修改 YAML 文件本身。',
    capabilityCheckHint: '多选检测可能需要 20 至 40 秒，并可能消耗服务商额度。',
    capabilityCheckTrigger: '检测',
    openaiCompatibleModelDiscovery: '支持 /models 接口的 OpenAI 兼容渠道可自动拉取模型。',
    testNotifications: {
      attemptPrefix: '第 {index} 次尝试',
      httpStatus: 'HTTP 状态码 {code}',
      durationMs: '耗时 {ms} 毫秒',
      detailLabel: '详细错误',
      errorCodePrefix: '错误类型',
      targetFallback: '通知渠道：{channel}',
    },
  },
  en: {
    unknownOption: 'Unknown option',
    unknownValue: 'Unknown value',
    rawValueSuffix: '(raw: {value})',
    keyTooltip: 'API key',
    channelDeleteTooltip: 'Delete channel',
    channelKeyMissing: 'API key missing',
    modelsConfigured: '{count} models configured',
    noModelsConfigured: 'No models configured',
    save: 'Save',
    saving: 'Saving…',
    fetchModelsHint: 'OpenAI-compatible channels that expose /models can auto-discover their model list.',
    modelDiscoveryUnsupported: 'Auto model discovery is only available for OpenAI-compatible and DeepSeek channels.',
    modelProviderMismatch: 'The model provider prefix does not match the current channel.',
    saveChannel: 'Save channel configuration',
    saveAi: 'Save AI configuration',
    testModelPrefix: 'Tested model: {model}.',
    testDefaultScope: 'Basic connection tests run against the first model in the list by default.',
    capabilitySummary: 'Capability check done: {passed} passed, {failed} failed, {skipped} skipped',
    rawErrorPrefix: 'Raw error',
    rawMessagePrefix: 'Raw summary',
    yamlRoutingHint: 'Advanced model routing YAML detected: this editor only manages channel entries and basic connection details. Runtime primary, fallback, vision models, and temperature are governed by the general fields below. If the YAML parses successfully, its routing and model declarations take precedence. This UI does not modify the YAML file itself.',
    capabilityCheckHint: 'Selecting multiple capabilities may take 20 to 40 seconds and consume provider quota.',
    capabilityCheckTrigger: 'Check',
    openaiCompatibleModelDiscovery: 'OpenAI-compatible channels exposing /models can auto-fetch their model list.',
    testNotifications: {
      attemptPrefix: 'Attempt {index}',
      httpStatus: 'HTTP status {code}',
      durationMs: 'Took {ms} ms',
      detailLabel: 'Detail',
      errorCodePrefix: 'Error type',
      targetFallback: 'Channel: {channel}',
    },
  },
} as const;

export function getSettingsProtocolLabel(protocol: string, language: UiLanguage): string {
  const normalized = protocol.trim().toLowerCase();
  const map = PROTOCOL_LABELS[language];
  return map[normalized] ?? protocol;
}

export function getSettingsCapabilityLabel(capability: string, language: UiLanguage): string {
  const map = CAPABILITY_LABELS[language];
  return map[capability] ?? capability;
}

export function getSettingsCapabilityHint(capability: string, language: UiLanguage): string {
  const map = CAPABILITY_HINTS[language];
  return map[capability] ?? '';
}

export function getSettingsStageLabel(stage: string, language: UiLanguage): string {
  const map = STAGE_LABELS[language];
  return map[stage] ?? stage;
}

export function getSettingsChannelStatusLabel(status: string, language: UiLanguage): string {
  const map = CHANNEL_STATUS_LABELS[language];
  return map[status] ?? status;
}

export function getNotificationErrorCodeLabel(code: string, language: UiLanguage): string {
  const normalized = code.trim().toLowerCase();
  const map = NOTIFICATION_ERROR_CODE_LABELS[language];
  return map[normalized] ?? code;
}

export function getNotificationChannelDisplayName(channel: string, language: UiLanguage): string {
  const normalized = channel.trim().toLowerCase();
  const map = CHANNEL_LABEL_OVERRIDES[language];
  return map[normalized] ?? channel;
}

export function formatSettingsText(
  template: string,
  values: Record<string, string | number> = {},
): string {
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    const value = values[key];
    return value === undefined || value === null ? '' : String(value);
  });
}
