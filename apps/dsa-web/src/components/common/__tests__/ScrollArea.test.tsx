import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScrollArea } from '../ScrollArea';

describe('ScrollArea', () => {
  it('renders a scrollable viewport and forwards custom classes', () => {
    render(
      <ScrollArea
        className="outer-shell"
        viewportClassName="inner-viewport"
        testId="scroll-area-viewport"
        ariaLabel="Custom region label"
      >
        <div>scroll content</div>
      </ScrollArea>
    );

    const viewport = screen.getByTestId('scroll-area-viewport');
    expect(viewport).toBeInTheDocument();
    expect(viewport).toHaveClass('inner-viewport');
    expect(viewport).toHaveTextContent('scroll content');
    expect(viewport).toHaveAttribute('tabindex', '0');
    expect(viewport).toHaveAttribute('role', 'region');
    expect(viewport).toHaveAttribute('aria-label', 'Custom region label');
    expect(viewport.parentElement).toHaveClass('outer-shell');
  });

  it('falls back to a generic accessible label when none is provided', () => {
    render(
      <ScrollArea testId="scroll-area-default-label">
        <div>scroll content</div>
      </ScrollArea>
    );

    const viewport = screen.getByTestId('scroll-area-default-label');
    expect(viewport).toHaveAttribute('aria-label', expect.stringMatching(/scroll/i));
    expect(viewport).toHaveAttribute('role', 'region');
  });

  it('omits region role and aria-label when bareViewport is set', () => {
    render(
      <ScrollArea testId="scroll-area-bare" bareViewport>
        <div>scroll content</div>
      </ScrollArea>
    );

    const viewport = screen.getByTestId('scroll-area-bare');
    expect(viewport).not.toHaveAttribute('role');
    expect(viewport).not.toHaveAttribute('aria-label');
    expect(viewport).toHaveAttribute('tabindex', '0');
  });
});
