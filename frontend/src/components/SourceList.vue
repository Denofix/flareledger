<script setup lang="ts">
import type { Source } from "../lib/types";
import { safeUrl, label } from "../lib/format";
import AppIcon from "./AppIcon.vue";
defineProps<{ sources: Source[] }>();
</script>
<template>
  <div class="source-list">
    <article v-for="source in sources" :key="source.id" class="source-card">
      <div class="source-icon"><AppIcon name="book" /></div>
      <div class="source-content">
        <div class="eyebrow">
          {{
            source.publisher || label(source.document_type || "Source record")
          }}
        </div>
        <RouterLink
          :to="'/sources/' + encodeURIComponent(source.id)"
          class="source-title"
          >{{ source.title || source.id }}</RouterLink
        >
        <p v-if="source.citation" class="source-citation">
          {{ source.citation }}
        </p>
        <div class="source-meta">
          <span class="mono">{{ source.id }}</span><span v-if="source.version"
            >Version {{ source.version }}</span
          ><span v-if="source.license_identifier">{{
            source.license_identifier
          }}</span>
        </div>
      </div>
      <a
        v-if="safeUrl(source.url)"
        :href="safeUrl(source.url)"
        target="_blank"
        rel="noopener noreferrer"
        class="icon-button"
        :aria-label="'Open original source: ' + source.title"
        ><AppIcon name="external"
      /></a>
    </article>
    <p v-if="!sources.length" class="muted">
      No linked source records are available for this item.
    </p>
  </div>
</template>
