<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError, request } from "../lib/api";
import { compatible, display } from "../lib/format";
import { useResource } from "../lib/useResource";
import type { Comparison, Detail, Issue, Page, Series } from "../lib/types";
import RequestState from "../components/RequestState.vue";
import SeriesChart from "../components/SeriesChart.vue";
import SourceList from "../components/SourceList.vue";
import LimitationList from "../components/LimitationList.vue";
import AppIcon from "../components/AppIcon.vue";
const route = useRoute(),
  router = useRouter();
const list = useResource<Page<Series>>();
const charts = useResource<{
  details: Detail<Series>[];
  limitations: string[];
}>();
const selected = computed(() =>
  typeof route.query.ids === "string"
    ? route.query.ids.split(",").filter(Boolean)
    : list.data.value?.items
        .slice(0, route.path === "/compare" ? 2 : 1)
        .map((item) => item.id) || [],
);
const isCompare = computed(() => route.path === "/compare");
const selectionError = computed(() =>
  charts.error.value instanceof ApiError &&
  ["incompatible_axes", "invalid_selection"].includes(charts.error.value.code)
    ? charts.error.value
    : null,
);
function relatedIssue(issue: Issue, series: Series) {
  return (
    issue.source_ids?.some((id) => series.source_ids.includes(id)) ||
    (Array.isArray(series.quality_issue_ids) &&
      series.quality_issue_ids.includes(issue.id))
  );
}
function seriesIssues(detail: Detail<Series>) {
  return detail.quality_issues.filter((issue) =>
    relatedIssue(issue, detail.item),
  );
}
function otherIssues(detail: Detail<Series>) {
  return detail.quality_issues.filter(
    (issue) => !relatedIssue(issue, detail.item),
  );
}
function loadList() {
  list.load((signal) => request<Page<Series>>("/series?limit=100", { signal }));
}
function loadCharts() {
  const ids = [...selected.value];
  if (!ids.length) {
    charts.reset();
    return;
  }
  charts.load(async (signal) => {
    if (ids.length > 4 || new Set(ids).size !== ids.length)
      throw new ApiError(
        422,
        "invalid_selection",
        "Choose up to four distinct measured series.",
      );
    const details = await Promise.all(
      ids.map((id) =>
        request<Detail<Series>>("/series/" + encodeURIComponent(id), {
          signal,
        }),
      ),
    );
    if (details.length > 1) {
      if (!compatible(details.map((detail) => detail.item)))
        throw new ApiError(
          422,
          "incompatible_axes",
          "These series measure different quantities or use different axes. Choose matching measurements before comparing. Droplet diameter and flame diameter are different quantities.",
        );
      const result = await request<Comparison>(
        "/compare?ids=" + encodeURIComponent(ids.join(",")),
        { signal },
      );
      return { details: result.series, limitations: result.limitations };
    }
    return {
      details,
      limitations: [
        "A shared axis does not establish matched experimental conditions or causality.",
      ],
    };
  });
}
function toggle(id: string) {
  const ids = selected.value.includes(id)
    ? selected.value.filter((value) => value !== id)
    : [...selected.value, id];
  router.replace({ path: route.path, query: { ids: ids.join(",") } });
}
watch(() => selected.value.join(","), loadCharts, { immediate: true });
onMounted(loadList);
</script>
<template>
  <header class="page-heading">
    <div class="eyebrow">MEASURED DATA / ORIGINAL COORDINATES</div>
    <h1>
      {{
        isCompare ? "Compare the measurements." : "A closer look at the data."
      }}
    </h1>
    <p class="page-intro">
      Follow numerical measurements from the FLEX source files. Original values,
      units and limitations stay with every series.
    </p>
    <a v-if="selected.length" href="#measurement-plot" class="text-link"
      >Jump to chart or selection guidance</a
    >
  </header>
  <RequestState
    :loading="list.loading.value"
    :error="list.error.value"
    @retry="loadList"
  />
  <div v-if="list.data.value" class="measurements-layout">
    <aside id="series-picker" class="series-picker">
      <div class="eyebrow">SELECT UP TO FOUR SERIES</div>
      <h2>
        Source series <span>{{ list.data.value.total }}</span>
      </h2>
      <label
        v-for="item in list.data.value.items"
        :key="item.id"
        class="series-option"
        :class="{ selected: selected.includes(item.id) }"
        ><input
          type="checkbox"
          :checked="selected.includes(item.id)"
          :disabled="selected.length >= 4 && !selected.includes(item.id)"
          @change="toggle(item.id)"
        />
        <div>
          <strong>{{ item.original_trial_label }}</strong><span>{{
            item.y.label_en
          }}</span
          ><small
            >{{ item.point_count }} points · {{ item.y.unit }} ·
            {{ item.x.unit }}</small
          >
        </div></label
      >
      <p class="picker-note">
        Only series with matching quantity names and units can share a
        comparison.
      </p>
      <RouterLink to="/investigations/PSI-69" class="text-link"
        >About FLEX <AppIcon name="external" :size="13"
      /></RouterLink>
    </aside>
    <div id="measurement-plot" class="chart-content">
      <section v-if="selectionError" class="limitations" role="status">
        <h2>These series cannot be compared</h2>
        <p>{{ selectionError.message }}</p>
        <a href="#series-picker" class="text-link"
          >Change the selected series</a
        >
      </section>
      <RequestState
        v-else
        :loading="charts.loading.value"
        :error="charts.error.value"
        @retry="loadCharts"
      />
      <section v-if="!selected.length" class="empty-state">
        <AppIcon name="chart" :size="32" />
        <h2>Choose a measured series</h2>
        <p>
          Select a series to inspect its original points and source evidence.
        </p>
      </section>
      <template v-else-if="charts.data.value && !charts.error.value"
        ><section class="panel chart-panel">
          <a href="#series-picker" class="text-link">Change selected series</a>
          <div class="section-heading">
            <div>
              <div class="eyebrow">
                {{
                  charts.data.value.details.length > 1
                    ? "SOURCE-LINKED COMPARISON"
                    : "ORIGINAL NUMERICAL SERIES"
                }}
              </div>
              <h2>{{ charts.data.value.details[0]?.item.y.label_en }}</h2>
            </div>
            <span class="tag"
              >{{
                charts.data.value.details
                  .reduce((total, detail) => total + detail.item.point_count, 0)
                  .toLocaleString("en-US")
              }}
              points</span
            >
          </div>
          <SeriesChart
            :series="charts.data.value.details.map((detail) => detail.item)"
          />
        </section>
        <LimitationList :notes="charts.data.value.limitations" />
        <section
          v-for="detail in charts.data.value.details"
          :key="detail.item.id"
          class="series-detail panel"
        >
          <div class="section-heading">
            <div>
              <div class="eyebrow">{{ detail.item.id }}</div>
              <h2>{{ detail.item.original_trial_label }} · source context</h2>
            </div>
            <span class="tag subtle">{{ detail.item.investigation_id }}</span>
          </div>
          <h3>Selected series limitations</h3>
          <p>
            {{
              detail.item.quality_note_en ||
              "No series-specific note is reported."
            }}
          </p>
          <dl class="inline-facts">
            <div>
              <dt>Uncertainty</dt>
              <dd>{{ display(detail.item.uncertainty) }}</dd>
            </div>
            <div>
              <dt>Data processing</dt>
              <dd>Original numeric values</dd>
            </div>
            <div>
              <dt>Time origin</dt>
              <dd>Not independently aligned</dd>
            </div>
          </dl>
          <LimitationList :issues="seriesIssues(detail)" />
          <details
            v-if="otherIssues(detail).length"
            class="investigation-notes"
          >
            <summary>
              Other investigation source notes — not assigned to this series
            </summary>
            <p>
              These notes concern other sources or trials in
              {{ detail.item.investigation_id }}. They are not established
              limitations of the selected series.
            </p>
            <LimitationList :issues="otherIssues(detail)" />
          </details>
          <SourceList :sources="detail.sources" />
          <details class="evidence-locators">
            <summary>View evidence locators</summary>
            <div
              v-for="evidence in detail.evidence"
              :key="evidence.id"
              class="locator"
            >
              <strong>{{ evidence.id }}</strong>
              <pre>{{ JSON.stringify(evidence.locator, null, 2) }}</pre>
              <p>
                Independent human review:
                {{
                  evidence.independent_human_review === true
                    ? "Recorded"
                    : "Not recorded"
                }}
              </p>
            </div>
          </details>
        </section>
      </template>
    </div>
  </div>
</template>
