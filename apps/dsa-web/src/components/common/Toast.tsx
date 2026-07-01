import type React from 'react';
import { CheckCircle, Info, X, XCircle, AlertTriangle } from 'lucide-react';
import { cn } from '../../utils/cn';
import type { ToastMessage, ToastType } from '../../hooks/useToast';

interface ToastProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

const iconMap: Record<ToastType, React.ComponentType<{ className?: string }>> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const styleMap: Record<ToastType, string> = {
  success: 'border-success/30 bg-success/10 text-success',
  error: 'border-[hsl(var(--color-danger-alert-border)/0.3)] bg-[hsl(var(--color-danger-alert-bg)/0.1)] text-[hsl(var(--color-danger-alert-text))]',
  warning: 'border-warning/30 bg-warning/10 text-warning',
  info: 'border-cyan/30 bg-cyan/10 text-cyan',
};

export const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  const Icon = iconMap[toast.type];

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        'pointer-events-auto flex w-[360px] max-w-[calc(100vw-24px)] items-start gap-3 rounded-xl border px-4 py-3 shadow-soft-card-strong backdrop-blur-sm',
        styleMap[toast.type],
      )}
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="min-w-0 flex-1">
        {toast.title ? (
          <p className="text-sm font-semibold">{toast.title}</p>
        ) : null}
        <p className={cn('text-sm', toast.title ? 'mt-0.5 opacity-90' : '')}>
          {toast.message}
        </p>
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="关闭"
        className="shrink-0 rounded p-1 opacity-70 transition-opacity hover:opacity-100"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col gap-3">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
};
