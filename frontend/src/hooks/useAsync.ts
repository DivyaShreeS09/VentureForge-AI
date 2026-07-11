import { useCallback, useState } from "react";
import { ApiError } from "../services/api";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

/** Wraps an async call with loading/error/data state so pages don't repeat this boilerplate. */
export function useAsync<T, Args extends unknown[]>(fn: (...args: Args) => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: false, error: null });

  const run = useCallback(
    async (...args: Args) => {
      setState({ data: null, loading: true, error: null });
      try {
        const data = await fn(...args);
        setState({ data, loading: false, error: null });
        return data;
      } catch (err) {
        const message = err instanceof ApiError ? String(err.detail ?? err.message) : "Unexpected error";
        setState({ data: null, loading: false, error: message });
        return null;
      }
    },
    [fn],
  );

  return { ...state, run };
}
