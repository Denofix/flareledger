import { shallowRef } from "vue";
import { request } from "./api";
import type { Meta } from "./types";

export const corpusMeta = shallowRef<Meta | null>(null);
export const corpusError = shallowRef<Error | null>(null);
export async function refreshCorpus() {
  try {
    const [meta, ready] = await Promise.all([
      request<Meta>("/meta"),
      request<{ status: string; corpus_version: string }>("/health/ready"),
    ]);
    if (
      ready.status !== "ready" ||
      ready.corpus_version !== meta.corpus_version
    )
      throw new Error("The corpus is not ready.");
    corpusMeta.value = meta;
    corpusError.value = null;
  } catch (error) {
    corpusError.value =
      error instanceof Error ? error : new Error("Corpus unavailable");
  }
}
