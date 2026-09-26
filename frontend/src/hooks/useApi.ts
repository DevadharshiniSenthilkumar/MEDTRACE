import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../services/api";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Calls `fn` on mount (and whenever `deps` change), tracking
 * loading/error/data state. Every page's data comes from a real
 * api.ts function passed in here — nothing is computed locally.
 */
export function useApi<T>(
  fn: () => Promise<T>,
  deps: React.DependencyList = []
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fn()
      .then((result) => setData(result))
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Something went wrong.")
      )
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  return { data, loading, error, reload: () => setTick((t) => t + 1) };
}
