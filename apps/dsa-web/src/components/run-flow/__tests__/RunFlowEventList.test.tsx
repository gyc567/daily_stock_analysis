import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { RunFlowEvent } from '../../../types/runFlow';
import { UiLanguageProvider } from '../../../contexts/UiLanguageContext';
import { RunFlowEventList } from '../RunFlowEventList';

const renderWithLanguage = (ui: React.ReactNode) =>
  render(<UiLanguageProvider>{ui}</UiLanguageProvider>);

const events: RunFlowEvent[] = [
  {
    id: 'evt-1',
    timestamp: '2026-06-08T08:00:01Z',
    severity: 'info',
    type: 'task_created',
    nodeId: 'request',
    title: '任务创建',
  },
  {
    id: 'evt-2',
    timestamp: '2026-06-08T08:00:02Z',
    severity: 'warning',
    type: 'provider_fallback',
    nodeId: 'daily_data',
    title: '日线降级',
    message: 'Tushare 失败后切换 AkShare',
  },
  {
    id: 'evt-3',
    timestamp: '2026-06-08T08:00:03Z',
    severity: 'danger',
    type: 'task_cancelled',
    nodeId: 'queue',
    title: '任务取消',
  },
];

describe('RunFlowEventList', () => {
  it('filters fallback and cancellation events with visible text labels', () => {
    window.localStorage.setItem('dsa.uiLanguage', 'zh');
    renderWithLanguage(<RunFlowEventList events={events} />);

    expect(screen.getAllByText('任务创建').length).toBeGreaterThan(0);
    expect(screen.getByText('日线降级')).toBeInTheDocument();
    expect(screen.getAllByText('任务取消').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '降级或重试' }));

    expect(screen.getByText('日线降级')).toBeInTheDocument();
    expect(screen.queryByText('任务创建')).not.toBeInTheDocument();
    expect(screen.queryByText('任务取消')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '取消' }));

    expect(screen.getAllByText('任务取消').length).toBeGreaterThan(0);
    expect(screen.queryByText('日线降级')).not.toBeInTheDocument();
    expect(screen.getByText('危险')).toBeInTheDocument();
  });

  it('renders localized event type labels and does not expose raw event.type', () => {
    window.localStorage.setItem('dsa.uiLanguage', 'zh');
    renderWithLanguage(<RunFlowEventList events={events} />);
    expect(screen.getAllByText('任务创建').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('数据源降级')).toBeInTheDocument();
    expect(screen.queryByText('provider_fallback')).not.toBeInTheDocument();
    expect(screen.queryByText('task_cancelled')).not.toBeInTheDocument();
  });

  it('selects the event node when an event row is clicked', () => {
    window.localStorage.setItem('dsa.uiLanguage', 'zh');
    const onSelectNode = vi.fn();
    renderWithLanguage(<RunFlowEventList events={events} onSelectNode={onSelectNode} />);

    fireEvent.click(screen.getByRole('button', { name: '查看事件 日线降级 关联节点' }));

    expect(onSelectNode).toHaveBeenCalledWith('daily_data');
  });

  it('falls back to "其他事件" for unknown event types', () => {
    window.localStorage.setItem('dsa.uiLanguage', 'zh');
    const unknownEvent: RunFlowEvent = {
      id: 'evt-4',
      timestamp: '2026-06-08T08:00:04Z',
      severity: 'info',
      type: 'mystery_future_event',
      nodeId: 'queue',
      title: '未来事件',
    };
    renderWithLanguage(<RunFlowEventList events={[unknownEvent]} />);
    expect(screen.getByText('mystery_future_event')).toBeInTheDocument();
  });
});
