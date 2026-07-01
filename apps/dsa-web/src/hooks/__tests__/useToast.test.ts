import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useToast } from '../useToast';

describe('useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize with empty toasts', () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toasts).toHaveLength(0);
  });

  it('should add a toast when calling toast()', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.toast('success', 'Test message', 'Test title');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0]).toMatchObject({
      type: 'success',
      message: 'Test message',
      title: 'Test title',
    });
  });

  it('should auto-dismiss toast after default duration', () => {
    const { result } = renderHook(() => useToast(3000));

    act(() => {
      result.current.toast('success', 'Auto dismiss test');
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('should not auto-dismiss toast when duration is 0', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.toast('info', 'No auto dismiss', undefined, 0);
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(result.current.toasts).toHaveLength(1);
  });

  it('should dismiss toast manually', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.toast('error', 'Manual dismiss test');
    });

    const toastId = result.current.toasts[0].id;

    act(() => {
      result.current.dismiss(toastId);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('should dismiss all toasts', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.toast('success', 'Message 1');
      result.current.toast('error', 'Message 2');
      result.current.toast('warning', 'Message 3');
    });

    expect(result.current.toasts).toHaveLength(3);

    act(() => {
      result.current.dismissAll();
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('should have convenience methods', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Success message', 'Success title');
      result.current.error('Error message', 'Error title');
      result.current.warning('Warning message', 'Warning title');
    });

    expect(result.current.toasts).toHaveLength(3);
    expect(result.current.toasts[0].type).toBe('success');
    expect(result.current.toasts[1].type).toBe('error');
    expect(result.current.toasts[2].type).toBe('warning');
  });

  it('should use default duration from hook parameter', () => {
    const { result } = renderHook(() => useToast(5000));

    act(() => {
      result.current.toast('info', 'Custom default duration');
    });

    act(() => {
      vi.advanceTimersByTime(4999);
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(result.current.toasts).toHaveLength(0);
  });
});
