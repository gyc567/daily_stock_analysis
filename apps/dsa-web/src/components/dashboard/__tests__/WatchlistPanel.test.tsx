import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { WatchlistPanel } from '../WatchlistPanel';
import { UiLanguageProvider } from '../../../contexts/UiLanguageContext';

const renderWithI18n = (ui: React.ReactNode) =>
  render(<UiLanguageProvider>{ui}</UiLanguageProvider>);

describe('WatchlistPanel', () => {
  it('renders one chip per stock code and the count badge', () => {
    renderWithI18n(
      <WatchlistPanel
        codes={['600176', '688486', '002957']}
        isLoading={false}
        onSelect={() => undefined}
      />,
    );

    const chips = screen.getAllByTestId('watchlist-chip');
    expect(chips).toHaveLength(3);
    expect(chips[0]).toHaveAttribute('data-stock-code', '600176');
    expect(chips[1]).toHaveAttribute('data-stock-code', '688486');
    expect(chips[2]).toHaveAttribute('data-stock-code', '002957');
    expect(screen.getByTestId('watchlist-count').textContent).toContain('3');
  });

  it('invokes onSelect with the clicked code', () => {
    const onSelect = vi.fn();
    renderWithI18n(
      <WatchlistPanel
        codes={['600176', '688486']}
        isLoading={false}
        onSelect={onSelect}
      />,
    );
    // Each chip renders a button with aria-label="分析 <code>". Pick the second
    // code (688486) and click it.
    const buttons = screen.getAllByTestId('watchlist-chip');
    expect(buttons[1]).toHaveAttribute('data-stock-code', '688486');
    fireEvent.click(buttons[1]);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('688486');
  });

  it('shows the empty-state message when codes is empty', () => {
    renderWithI18n(<WatchlistPanel codes={[]} isLoading={false} />);
    expect(screen.getByTestId('watchlist-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('watchlist-chips')).toBeNull();
  });

  it('renders the actions slot when provided', () => {
    renderWithI18n(
      <WatchlistPanel
        codes={['600176', '688486']}
        isLoading={false}
        actions={<button type="button" data-testid="custom-action">Custom</button>}
      />,
    );
    expect(screen.getByTestId('custom-action')).toBeInTheDocument();
    expect(screen.getByText('Custom')).toBeInTheDocument();
  });

  it('shows a loading message when isLoading is true and codes is empty', () => {
    renderWithI18n(<WatchlistPanel codes={[]} isLoading />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByTestId('watchlist-empty')).toBeNull();
    expect(screen.queryByTestId('watchlist-chips')).toBeNull();
  });

  it('collapses the overflow chips behind a "+N more" chip past maxVisible', () => {
    const codes = Array.from({ length: 30 }, (_, i) => `6000${i.toString().padStart(2, '0')}`);
    renderWithI18n(
      <WatchlistPanel
        codes={codes}
        isLoading={false}
        maxVisible={5}
        onSelect={() => undefined}
      />,
    );

    expect(screen.getAllByTestId('watchlist-chip')).toHaveLength(5);
    expect(screen.getByTestId('watchlist-overflow').textContent).toContain('25');
  });
});
