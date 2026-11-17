<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { request } from "../lib/api";
import type { Investigation, Page } from "../lib/types";
import { useResource } from "../lib/useResource";
import { corpusMeta } from "../lib/session";
import { display, label } from "../lib/format";
import RequestState from "../components/RequestState.vue";
import AppIcon from "../components/AppIcon.vue";
const resource = useResource<Page<Investigation>>();
const search = ref("");
const phase = ref("all");
const items = computed(
  () =>
    resource.data.value?.items.filter(
      (item) =>
        (phase.value === "all" || item.fuel_phase === phase.value) &&
        [item.title_en, item.summary_en, item.id, item.acronym, ...item.tags]
          .join(" ")
          .toLowerCase()
          .includes(search.value.trim().toLowerCase()),
    ) || [],
);
const phases = computed(() => [
  ...new Set(resource.data.value?.items.map((item) => item.fuel_phase) || []),
]);
function load() {
  resource.load((signal) =>
    request<Page<Investigation>>("/investigations?limit=100", { signal }),
  );
}
onMounted(load);
</script>
<template>
  <section class="catalog-hero">
    <div>
      <div class="eyebrow">
        <span class="short-rule" /> MICROGRAVITY COMBUSTION / EVIDENCE EXPLORER
      </div>
      <h1>Explore the research.<br /><em>Follow the evidence.</em></h1>
      <p class="hero-copy">
        An open research desk for NASA combustion data. Find an investigation,
        examine the measurements, and trace what you see back to its original
        source.
      </p>
      <div class="hero-actions">
        <a href="#investigations" class="button"
          >Explore investigations <AppIcon name="arrow" :size="17" /></a
        ><RouterLink to="/evidence" class="text-link"
          >Search the evidence
          <span><AppIcon name="external" :size="13" /></span
        ></RouterLink>
      </div>
    </div>
    <RouterLink
      to="/measurements?ids=SERIES-FLEX-002-DropletData"
      class="feature-card"
      ><span class="eyebrow">A GOOD PLACE TO START</span>
      <div class="orbit-art" aria-hidden="true">
        <span class="orbit o1" /><span class="orbit o2" /><span
          class="droplet"
        /><span class="orbit-dot" />
      </div>
      <span class="feature-code mono">PSI-69 / FLEX</span>
      <h2>One measurement.<br />A traceable story.</h2>
      <span class="feature-bottom"
        >Explore measured droplet series <AppIcon name="arrow" /></span
    ></RouterLink>
  </section>
  <section class="stat-strip" aria-label="Corpus summary">
    <div>
      <strong>{{ corpusMeta?.statistics.investigations ?? "—" }}</strong><span
        >Investigations</span
      >
    </div>
    <div>
      <strong>{{
        corpusMeta?.statistics.record_types.trial_row?.toLocaleString(
          "en-US",
        ) ?? "—"
      }}</strong><span
        >Trial rows <small>distinct from other records</small></span
      >
    </div>
    <div>
      <strong>{{
        corpusMeta?.statistics.numerical_time_series ?? "—"
      }}</strong><span>Measured series</span>
    </div>
    <div>
      <strong>{{ corpusMeta?.statistics.source_records ?? "—" }}</strong><span
        >Source records</span
      >
    </div>
  </section>
  <section id="investigations" class="catalog-section">
    <div class="section-heading">
      <div>
        <div class="eyebrow">THE COLLECTION</div>
        <h2>Find your next investigation</h2>
      </div>
      <span class="collection-count mono"
        >{{ items.length }} OF
        {{ resource.data.value?.total ?? "—" }} INVESTIGATIONS</span
      >
    </div>
    <div class="catalog-toolbar">
      <label class="search-input"
        ><AppIcon name="search" /><span class="sr-only"
          >Filter investigations</span
        ><input
          v-model="search"
          type="search"
          placeholder="Search by title, material, or investigation ID…" /></label
      ><label class="phase-filter"
        ><span>Fuel phase</span
        ><select v-model="phase">
          <option value="all">All phases</option>
          <option v-for="value in phases" :key="value" :value="value">
            {{ label(value) }}
          </option>
        </select></label
      >
    </div>
    <RequestState
      :loading="resource.loading.value"
      :error="resource.error.value"
      @retry="load"
    />
    <div v-if="resource.data.value" class="investigation-grid">
      <RouterLink
        v-for="item in items"
        :key="item.id"
        :to="'/investigations/' + item.id"
        class="investigation-card"
        ><div class="card-top">
          <span
            class="study-mark"
            :class="{ orange: item.fuel_phase === 'liquid' }"
            ><AppIcon
              :name="item.availability.includes('series') ? 'chart' : 'book'"
              :size="22" /></span
          ><span class="mono muted">{{ item.id }}</span>
        </div>
        <div class="card-eyebrow">
          {{ item.acronym || "INVESTIGATION" }}
        </div>
        <h3>{{ item.title_en || item.title }}</h3>
        <p>{{ item.summary_en }}</p>
        <div class="tag-row">
          <span class="tag">{{ label(item.fuel_phase) }}</span><span
            class="tag subtle"
            >{{ display(item.gravity_regime) }}</span
          >
        </div>
        <div class="card-foot">
          <span>{{
            item.availability === "metadata_only"
              ? "Investigation metadata"
              : "Explore records & sources"
          }}</span><AppIcon name="arrow" :size="19" /></div
      ></RouterLink>
    </div>
    <div v-if="resource.data.value && !items.length" class="empty-state">
      <h3>No matching investigations</h3>
      <p>Try a different term or include all fuel phases.</p>
      <button
        class="button secondary"
        @click="
          search = '';
          phase = 'all';
        "
      >
        Clear filters
      </button>
    </div>
  </section>
  <aside class="research-note">
    <AppIcon name="book" :size="23" />
    <div>
      <strong>Evidence before conclusions.</strong>
      <p>
        Source identity is verified during import. Scientific limitations remain
        visible: a matching checksum is not an independent scientific review.
      </p>
    </div>
    <RouterLink to="/evidence"
      >Explore sources <AppIcon name="external" :size="13"
    /></RouterLink>
  </aside>
</template>
