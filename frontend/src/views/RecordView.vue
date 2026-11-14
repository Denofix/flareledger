<script setup lang="ts">
import AppIcon from "../components/AppIcon.vue";
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import { request } from "../lib/api";
import { useResource } from "../lib/useResource";
import type { Detail, UnknownRecord } from "../lib/types";
import {
  display,
  entityTitle,
  label,
  safeUrl,
  simpleFields,
} from "../lib/format";
import SourceList from "../components/SourceList.vue";
import RequestState from "../components/RequestState.vue";
import LimitationList from "../components/LimitationList.vue";
const props = defineProps<{ kind: "sources" | "records" | "evidence" }>();
const route = useRoute();
const resource = useResource<Detail>();
const fields = computed(() =>
  resource.data.value ? simpleFields(resource.data.value.item) : [],
);
const quantities = computed<(UnknownRecord & { name: string })[]>(() => {
  const value = resource.data.value?.item.reported_quantities;
  return value && typeof value === "object"
    ? Object.entries(value).map(([name, quantity]) => ({
        name,
        ...(quantity as UnknownRecord),
      }))
    : [];
});
function load() {
  resource.load((signal) =>
    request<Detail>(
      "/" + props.kind + "/" + encodeURIComponent(String(route.params.id)),
      { signal },
    ),
  );
}
watch(() => [route.params.id, props.kind], load, { immediate: true });
</script>
<template>
  <RouterLink to="/evidence" class="back-link">← Evidence search</RouterLink
  ><RequestState
    :loading="resource.loading.value"
    :error="resource.error.value"
    @retry="load"
  />
  <template v-if="resource.data.value"
    ><header class="page-heading">
      <div class="eyebrow">
        {{
          kind === "sources"
            ? "ORIGINAL SOURCE RECORD"
            : kind === "evidence"
              ? "SOURCE EVIDENCE"
              : "SOURCE-TABLE RECORD"
        }}
        / {{ resource.data.value.item.id }}
      </div>
      <h1>{{ entityTitle(resource.data.value.item) }}</h1>
      <p v-if="resource.data.value.item.citation" class="page-intro">
        {{ resource.data.value.item.citation }}
      </p>
      <a
        v-if="safeUrl(resource.data.value.item.url)"
        :href="safeUrl(resource.data.value.item.url)"
        target="_blank"
        rel="noopener noreferrer"
        class="button secondary"
        >Open original source <AppIcon name="external" :size="13" /></a
      ><RouterLink
        v-if="resource.data.value.item.investigation_id"
        :to="
          '/investigations/' +
          encodeURIComponent(String(resource.data.value.item.investigation_id))
        "
        class="text-link"
        >About the investigation <AppIcon name="external" :size="13"
      /></RouterLink>
    </header>
    <LimitationList :issues="resource.data.value.quality_issues" />
    <section
      v-if="kind === 'evidence' && resource.data.value.item.locator"
      class="panel section-space"
    >
      <h2>Original evidence locator</h2>
      <pre class="locator">{{
        JSON.stringify(resource.data.value.item.locator, null, 2)
      }}</pre>
      <p class="muted">
        Independent human review:
        {{
          resource.data.value.item.independent_human_review === true
            ? "Recorded"
            : "Not recorded"
        }}. Extraction and verification fields below are retained as reported.
      </p>
    </section>
    <section class="panel section-space">
      <div class="section-heading">
        <div>
          <div class="eyebrow">AS REPORTED</div>
          <h2>Record details</h2>
        </div>
      </div>
      <dl class="record-fields">
        <div v-for="[key, value] in fields" :key="key">
          <dt>{{ label(key) }}</dt>
          <dd>{{ display(value) }}</dd>
        </div>
      </dl>
    </section>
    <section v-if="quantities.length" class="panel section-space">
      <h2>Reported quantities</h2>
      <p class="muted">
        Units, qualifiers and uncertainty are retained from the source. Not
        reported does not mean zero.
      </p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Quantity</th>
              <th>Value</th>
              <th>Basis</th>
              <th>Qualifier</th>
              <th>Uncertainty</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="quantity in quantities" :key="String(quantity.name)">
              <td>{{ label(String(quantity.name)) }}</td>
              <td>
                {{ display(quantity.value, String(quantity.unit || "")) }}
              </td>
              <td>{{ display(quantity.basis) }}</td>
              <td>{{ display(quantity.qualifier) }}</td>
              <td>{{ display(quantity.uncertainty) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section v-if="resource.data.value.evidence.length" class="section-space">
      <h2>Evidence locators</h2>
      <div
        v-for="evidence in resource.data.value.evidence"
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
    </section>
    <section class="section-space">
      <h2>Linked sources</h2>
      <SourceList :sources="resource.data.value.sources" />
    </section>
    <details class="raw-record">
      <summary>View complete source payload</summary>
      <pre>{{ JSON.stringify(resource.data.value.item, null, 2) }}</pre>
    </details>
  </template>
</template>
