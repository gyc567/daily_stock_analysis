import { useCallback, useState } from 'react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

interface UseToastReturn {
  toasts: ToastMessage[];
  toast: (type: ToastType, message: string, title?: string, duration?: number) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

export function useToast(defaultDuration = 4000): UseToastReturn {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  const toast = useCallback(
    (type: ToastType, message: string, title?: string, duration = defaultDuration) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const newToast: ToastMessage = { id, type, message, title, duration };
      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => dismiss(id), duration);
      }
    },
    [defaultDuration, dismiss],
  );

  const success = useCallback(
    (message: string, title?: string) => toast('success', message, title),
    [toast],
  );

  const error = useCallback(
    (message: string, title?: string) => toast('error', message, title),
    [toast],
  );

  const warning = useCallback(
    (message: string, title?: string) => toast('warning', message, title),
    [toast],
  );

  return { toasts, toast, success, error, warning, dismiss, dismissAll };
}
