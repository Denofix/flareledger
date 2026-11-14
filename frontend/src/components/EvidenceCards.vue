<script setup lang="ts">
import type { SearchItem } from "../lib/types";
import { label } from "../lib/format";
import SourceList from "./SourceList.vue";
defineProps<{ items: SearchItem[] }>();
function route(item: SearchItem): string | null {
  const group = (
    {
      investigation: "investigations",
      record: "records",
      source: "sources",
    } as Record<string, string>
  )[item.kind];
  return group ? `/${group}/${encodeURIComponent(item.id)}` : null;
}
</script>
<template>
  <article
    v-for="item in items"
    :key="item.kind + item.id"
    class="evidence-card"
  >
    <div class="card-top">
      <span class="tag">{{ label(item.kind) }}</span><span class="mono muted">{{
        item.id
      }}</span>
    </div>
    <h3>
      <RouterLink v-if="route(item)" :to="route(item)!">{{
        item.title
      }}</RouterLink><span v-else>{{ item.title }}</span>
    </h3>
    <p v-if="item.excerpt" class="muted">
      {{ item.excerpt }}
    </p>
    <details>
      <summary>
        View linked sources <span>{{ item.sources.length }}</span>
      </summary>
      <p class="muted">
        Search results are excerpts. Open the linked research record to inspect
        original values, full locators, review status and limitations.
      </p>
      <div v-if="item.evidence_ids.length" class="locator">
        <strong>Evidence identifiers</strong>
        <p v-for="id in item.evidence_ids" :key="id" class="mono">
          <RouterLink :to="'/evidence/' + encodeURIComponent(id)">{{
            id
          }}</RouterLink>
        </p>
      </div>
      <SourceList :sources="item.sources" />
    </details>
  </article>
</template>
