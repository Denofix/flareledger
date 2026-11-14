<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { request } from "../lib/api";
import type { SearchResult } from "../lib/types";
import { useResource } from "../lib/useResource";
import RequestState from "../components/RequestState.vue";
import EvidenceCards from "../components/EvidenceCards.vue";
import AppIcon from "../components/AppIcon.vue";
const route = useRoute(),
  router = useRouter();
const term = ref(String(route.query.q || ""));
const results = useResource<SearchResult>();
function load() {
  const q = String(route.query.q || "").trim();
  if (q)
    results.load((signal) =>
      request<SearchResult>(
        "/search?q=" + encodeURIComponent(q) + "&limit=20",
        { signal },
      ),
    );
  else results.reset();
}
function search() {
  if (term.value.trim()) router.replace({ query: { q: term.value.trim() } });
}
watch(
  () => route.query.q,
  () => {
    term.value = String(route.query.q || "");
    load();
  },
  { immediate: true },
);
</script>
<template>
  <header class="page-heading">
    <div class="eyebrow">LEXICAL RETRIEVAL / SOURCE-LINKED RESULTS</div>
    <h1>Find the evidence.</h1>
    <p class="page-intro">
      Search investigation metadata, research records, knowledge cards and
      source documents. Results are keyword matches, not generated scientific
      conclusions.
    </p>
  </header>
  <form class="evidence-search" @submit.prevent="search">
    <label class="search-input"
      ><AppIcon name="search" /><span class="sr-only">Search the corpus</span
      ><input
        v-model="term"
        type="search"
        placeholder="Try PMMA, FLEX, or oxygen…"
        maxlength="240"
        required /></label
    ><button class="button" type="submit">
      Search evidence <AppIcon name="arrow" :size="17" />
    </button>
  </form>
  <div class="suggestion-row">
    <span>START WITH</span
    ><RouterLink
      v-for="q in ['PMMA', 'FLEX', 'oxygen']"
      :key="q"
      :to="{ query: { q } }"
      >{{ q }} <AppIcon name="external" :size="13"
    /></RouterLink>
  </div>
  <RequestState
    :loading="results.loading.value"
    :error="results.error.value"
    @retry="load"
  />
  <template v-if="results.data.value"
    ><div class="result-summary">
      <strong>{{ results.data.value.items.length }} results shown</strong
      ><span>Keyword retrieval · no generated answer</span>
    </div>
    <EvidenceCards :items="results.data.value.items" />
    <div v-if="!results.data.value.items.length" class="empty-state">
      <h2>No matching evidence</h2>
      <p>
        Try fewer keywords or another term. Absence of a match is not evidence
        of absence.
      </p>
    </div></template
  >
  <div v-else-if="!route.query.q" class="search-intro">
    <AppIcon name="book" :size="34" />
    <h2>A direct route to the original source.</h2>
    <p>
      Search the reviewed corpus, inspect the source locators and keep the
      evidence separate from an interpretation.
    </p>
  </div>
</template>
