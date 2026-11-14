import { onScopeDispose, ref, shallowRef } from "vue";

export function useResource<T>() {
  const data = shallowRef<T | null>(null);
  const loading = ref(false);
  const error = shallowRef<Error | null>(null);
  let current: AbortController | null = null;
  function reset() {
    current?.abort();
    current = null;
    data.value = null;
    error.value = null;
    loading.value = false;
  }
  async function load(fetcher: (signal: AbortSignal) => Promise<T>) {
    current?.abort();
    const controller = new AbortController();
    current = controller;
    data.value = null;
    error.value = null;
    loading.value = true;
    try {
      const result = await fetcher(controller.signal);
      if (!controller.signal.aborted) data.value = result;
    } catch (problem) {
      if (!controller.signal.aborted)
        error.value =
          problem instanceof Error
            ? problem
            : new Error("Unable to load this record.");
    } finally {
      if (!controller.signal.aborted) loading.value = false;
    }
  }
  onScopeDispose(() => current?.abort());
  return { data, loading, error, load, reset };
}
