import type React from 'react';
import { cn } from '../../utils/cn';

interface ScrollAreaProps {
  children: React.ReactNode;
  className?: string;
  viewportClassName?: string;
  testId?: string;
  viewportRef?: React.Ref<HTMLDivElement>;
  onScroll?: React.UIEventHandler<HTMLDivElement>;
  /** Accessible label for the scrollable region. Falls back to a generic label. */
  ariaLabel?: string;
  /** Removes the default `role="region"` when set to true (rarely needed). */
  bareViewport?: boolean;
}

export const ScrollArea: React.FC<ScrollAreaProps> = ({
  children,
  className,
  viewportClassName,
  testId,
  viewportRef,
  onScroll,
  ariaLabel,
  bareViewport = false,
}) => {
  return (
    <div className={cn('min-h-0 flex-1 overflow-hidden', className)}>
      <div
        ref={viewportRef}
        data-testid={testId}
        onScroll={onScroll}
        tabIndex={0}
        role={bareViewport ? undefined : 'region'}
        aria-label={bareViewport ? undefined : (ariaLabel ?? 'Scrollable content')}
        className={cn(
          'h-full overflow-y-auto custom-scrollbar focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40',
          viewportClassName,
        )}
      >
        {children}
      </div>
    </div>
  );
};
