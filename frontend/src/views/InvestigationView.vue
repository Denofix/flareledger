<script setup lang="ts">
import { watch } from "vue";
import { useRoute } from "vue-router";
import { request, query } from "../lib/api";
import type {
  Detail,
  Investigation,
  Page,
  ResearchRecord,
  Series,
} from "../lib/types";
import { useResource } from "../lib/useResource";
import { display, label } from "../lib/format";
import RequestState from "../components/RequestState.vue";
import SourceList from "../components/SourceList.vue";
import LimitationList from "../components/LimitationList.vue";
import AppIcon from "../components/AppIcon.vue";
const route = useRoute();
const resource = useResource<{
  detail: Detail<Investigation>;
  records: Page<ResearchRecord>;
  series: Page<Series>;
}>();
function load() {
  const id = String(route.params.id);
  resource.load(async (signal) => {
    const [detail, records, series] = await Promise.all([
      request<Detail<Investigation>>(
        "/investigations/" + encodeURIComponent(id),
        { signal },
      ),
      request<Page<ResearchRecord>>(
        "/records" + query({ investigation_id: id, limit: 12 }),
        { signal },
      ),
      request<Page<Series>>(
        "/series" + query({ investigation_id: id, limit: 100 }),
        { signal },
      ),
    ]);
    return { detail, records, series };
  });
}
watch(() => route.params.id, load, { immediate: true });
</script>
<template>
  <RouterLink to="/" class="back-link">← All investigations</RouterLink>
  <RequestState
    :loading="resource.loading.value"
    :error="resource.error.value"
    @retry="load"
  />
  <template v-if="resource.data.value">
    <header class="page-heading">
      <div class="eyebrow">
        {{ resource.data.value.detail.item.id }} /
        {{ resource.data.value.detail.item.acronym }} / VERSION
        {{ resource.data.value.detail.item.version }}
      </div>
      <h1>
        {{
          resource.data.value.detail.item.title_en ||
          resource.data.value.detail.item.title
        }}
      </h1>
      <p class="page-intro">{{ resource.data.value.detail.item.summary_en }}</p>
      <div class="tag-row">
        <span class="tag">{{
          label(resource.data.value.detail.item.fuel_phase)
        }}</span><span class="tag">{{
          resource.data.value.detail.item.gravity_regime
        }}</span
        ><a
          :href="'https://doi.org/' + resource.data.value.detail.item.doi"
          class="tag subtle"
          target="_blank"
          rel="noopener noreferrer"
          >DOI {{ resource.data.value.detail.item.doi }}
          <AppIcon name="external" :size="13"
        /></a>
      </div>
    </header>
    <div class="detail-layout">
      <div class="detail-main">
        <LimitationList :issues="resource.data.value.detail.quality_issues" />
        <section class="panel section-space">
          <div class="section-heading">
            <div>
              <div class="eyebrow">ORIGINAL MEASUREMENTS</div>
              <h2>Measured series</h2>
            </div>
            <span class="count-pill">{{
              resource.data.value.series.total
            }}</span>
          </div>
          <RouterLink
            v-for="series in resource.data.value.series.items"
            :key="series.id"
            :to="{ path: '/measurements', query: { ids: series.id } }"
            class="series-link"
            ><div class="study-mark"><AppIcon name="chart" /></div>
            <div>
              <strong
                >{{ series.original_trial_label }} ·
                {{ series.y.label_en }}</strong
              ><small
                >{{ series.point_count }} points · {{ series.x.unit }} /
                {{ series.y.unit }}</small
              >
            </div>
            <AppIcon name="arrow"
          /></RouterLink>
          <p v-if="!resource.data.value.series.total" class="muted">
            No chart-ready measured series are included for this investigation.
            Its records and source evidence remain available below.
          </p>
        </section>
        <section class="panel section-space">
          <div class="section-heading">
            <div>
              <div class="eyebrow">SOURCE TABLES</div>
              <h2>Research records</h2>
            </div>
            <span class="count-pill">{{
              resource.data.value.records.total
            }}</span>
          </div>
          <p class="muted">
            Rows include trial records, operating conditions and notes. A
            source-table row is not automatically an independent trial.
          </p>
          <div
            v-if="resource.data.value.records.items.length"
            class="table-scroll"
          >
            <table>
              <thead>
                <tr>
                  <th>Record / test</th>
                  <th>Type</th>
                  <th>Material</th>
                  <th>Oxygen</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="record in resource.data.value.records.items"
                  :key="record.id"
                >
                  <td>
                    <RouterLink :to="'/records/' + record.id"
                      >{{ record.original_test_id || record.id }}
                      <AppIcon name="external" :size="13"
                    /></RouterLink>
                  </td>
                  <td>
                    <span class="tag subtle">{{
                      label(record.record_type)
                    }}</span>
                  </td>
                  <td>{{ display(record.material) }}</td>
                  <td>{{ display(record.oxygen_percent, "%") }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="muted">
            No embedded table records are included for this investigation.
          </p>
          <p
            v-if="resource.data.value.records.total > 12"
            class="table-caption"
          >
            Showing the first 12 of
            {{ resource.data.value.records.total }} records.
            <RouterLink
              :to="{
                path: '/evidence',
                query: { q: resource.data.value.detail.item.acronym },
              }"
              >Search related evidence <AppIcon name="external" :size="13"
            /></RouterLink>
          </p>
        </section>
        <section class="section-space">
          <div class="section-heading">
            <div>
              <div class="eyebrow">THE PAPER TRAIL</div>
              <h2>Original sources</h2>
            </div>
          </div>
          <SourceList :sources="resource.data.value.detail.sources" />
        </section>
      </div>
      <aside class="metadata-panel">
        <div class="eyebrow">INVESTIGATION CONTEXT</div>
        <dl>
          <dt>Classification</dt>
          <dd>{{ display(resource.data.value.detail.item.gravity_regime) }}</dd>
          <dt>Classification basis</dt>
          <dd>
            {{ display(resource.data.value.detail.item.gravity_regime_basis) }}
          </dd>
          <dt>Facility, as reported</dt>
          <dd>
            {{ display(resource.data.value.detail.item.facility_as_reported) }}
          </dd>
          <dt>Platform, as reported</dt>
          <dd>
            {{
              display(
                resource.data.value.detail.item.flight_platform_as_reported,
              )
            }}
          </dd>
          <dt>Source version</dt>
          <dd>{{ resource.data.value.detail.item.version }}</dd>
        </dl>
        <div class="metadata-note">
          Metadata is retained as reported. Investigation classification does
          not establish the gravity regime of every individual external file.
        </div>
        <RouterLink
          :to="{
            path: '/ask',
            query: { q: resource.data.value.detail.item.acronym },
          }"
          class="button secondary"
          >Explore the evidence <AppIcon name="arrow" :size="16"
        /></RouterLink>
      </aside>
    </div>
  </template>
</template>
