import { describe, expect, it } from 'vitest';
import {
  SETTINGS_TEXT,
  formatSettingsText,
  getNotificationChannelDisplayName,
  getNotificationErrorCodeLabel,
  getSettingsCapabilityHint,
  getSettingsCapabilityLabel,
  getSettingsChannelStatusLabel,
  getSettingsProtocolLabel,
  getSettingsStageLabel,
} from '../settingsText';

describe('settingsText localizations', () => {
  it('localizes channel protocol labels in both languages', () => {
    expect(getSettingsProtocolLabel('openai', 'zh')).toBe('OpenAI 兼容协议');
    expect(getSettingsProtocolLabel('openai', 'en')).toBe('OpenAI Compatible');
    expect(getSettingsProtocolLabel('unknown_proto', 'zh')).toBe('unknown_proto');
  });

  it('localizes capability labels and hints in both languages', () => {
    expect(getSettingsCapabilityLabel('json', 'zh')).toBe('JSON 输出');
    expect(getSettingsCapabilityLabel('vision', 'en')).toBe('Vision');
    expect(getSettingsCapabilityHint('tools', 'zh')).toMatch(/函数调用/);
    expect(getSettingsCapabilityHint('tools', 'en')).toMatch(/function\/tool calling/);
  });

  it('localizes stage labels', () => {
    expect(getSettingsStageLabel('model_discovery', 'zh')).toBe('模型列表获取');
    expect(getSettingsStageLabel('model_discovery', 'en')).toBe('Model discovery');
    expect(getSettingsStageLabel('custom_stage', 'zh')).toBe('custom_stage');
  });

  it('localizes channel status badges', () => {
    expect(getSettingsChannelStatusLabel('connected', 'zh')).toBe('连接正常');
    expect(getSettingsChannelStatusLabel('testing', 'en')).toBe('Testing');
  });

  it('localizes notification error codes and falls back to raw code', () => {
    expect(getNotificationErrorCodeLabel('http_500', 'zh')).toBe('HTTP 错误');
    expect(getNotificationErrorCodeLabel('http_500', 'en')).toBe('HTTP error');
    expect(getNotificationErrorCodeLabel('config_missing', 'zh')).toBe('配置不完整');
    expect(getNotificationErrorCodeLabel('mystery_code', 'zh')).toBe('mystery_code');
  });

  it('localizes notification channel display names', () => {
    expect(getNotificationChannelDisplayName('wechat', 'zh')).toBe('企业微信');
    expect(getNotificationChannelDisplayName('wechat', 'en')).toBe('WeCom');
    expect(getNotificationChannelDisplayName('serverchan3', 'zh')).toBe('Server酱 3');
    expect(getNotificationChannelDisplayName('discord', 'zh')).toBe('discord');
  });

  it('formats placeholder tokens in settings templates', () => {
    expect(formatSettingsText(SETTINGS_TEXT.zh.modelsConfigured, { count: 4 })).toBe('已配置 4 个模型');
    expect(formatSettingsText(SETTINGS_TEXT.en.modelsConfigured, { count: 4 })).toBe('4 models configured');
  });
});
