import { useCallback, useState } from "react";
import { ApiError } from "../services/api";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** The real HTTP status of a failed request, when it was an `ApiError` — lets a caller tell a
   * genuine "this ID no longer exists" (404) apart from a transient network/server failure,
   * without a second duplicate fetch just to inspect the status code. `null` otherwise. */
  errorStatus: number | null;
};

/** Wraps an async call with loading/error/data state so pages don't repeat this boilerplate. */
export function useAsync<T, Args extends unknown[]>(fn: (...args: Args) => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: false, error: null, errorStatus: null });

  const run = useCallback(
    async (...args: Args) => {
      setState({ data: null, loading: true, error: null, errorStatus: null });
      try {
        const data = await fn(...args);
        setState({ data, loading: false, error: null, errorStatus: null });
        return data;
      } catch (err) {
        const message = err instanceof ApiError ? String(err.detail ?? err.message) : "Unexpected error";
        const errorStatus = err instanceof ApiError ? err.status : null;
        setState({ data: null, loading: false, error: message, errorStatus });
        return null;
      }
    },
    [fn],
  );

  return { ...state, run };
}
