<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { Point, Series } from "../lib/types";
import { display } from "../lib/format";
const props = defineProps<{ series: Series[] }>();
const palette = ["#197a73", "#d17948", "#7063a6", "#487fa8"];
const selectedIndex = ref(0);
const selectedSeries = ref(0);
const chartElement = ref<HTMLElement>();
const width = ref(840);
const expanded = ref(false);
let observer: ResizeObserver | undefined;
onMounted(() => {
  if (typeof ResizeObserver === "undefined" || !chartElement.value) return;
  observer = new ResizeObserver(([entry]) => {
    if (entry && entry.contentRect.width > 0)
      width.value = entry.contentRect.width;
  });
  observer.observe(chartElement.value);
});
onBeforeUnmount(() => observer?.disconnect());
const chartWidth = computed(() =>
  Math.max(expanded.value ? 760 : 250, width.value),
);
const compact = computed(() => chartWidth.value < 520);
const left = 64;
const right = computed(() => chartWidth.value - 24);
const top = 25;
const bottom = computed(() => (compact.value ? 230 : 315));
function valid(point: Point): point is [number, number] {
  return (
    typeof point[0] === "number" &&
    Number.isFinite(point[0]) &&
    typeof point[1] === "number" &&
    Number.isFinite(point[1])
  );
}
const all = computed(() =>
  props.series.flatMap((item) => (item.points || []).filter(valid)),
);
const domain = computed(() => {
  const xs = all.value.map((point) => point[0]),
    ys = all.value.map((point) => point[1]);
  if (!xs.length) return { x0: 0, x1: 1, y0: 0, y1: 1 };
  const x0 = Math.min(...xs),
    x1 = Math.max(...xs),
    y0 = Math.min(0, ...ys),
    y1 = Math.max(...ys);
  return {
    x0,
    x1: x1 === x0 ? x0 + 1 : x1,
    y0,
    y1: y0 + (y1 - y0 || 1) * 1.06,
  };
});
const x = (value: number) =>
  left +
  ((value - domain.value.x0) / (domain.value.x1 - domain.value.x0)) *
    (right.value - left);
const y = (value: number) =>
  bottom.value -
  ((value - domain.value.y0) / (domain.value.y1 - domain.value.y0)) *
    (bottom.value - top);
function ticks(min: number, max: number, count: number) {
  const rough = (max - min) / count;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step =
    (rough / power <= 1
      ? 1
      : rough / power <= 2
        ? 2
        : rough / power <= 5
          ? 5
          : 10) * power;
  const start = Math.ceil(min / step);
  return Array.from(
    { length: Math.max(0, Math.floor(max / step) - start + 1) },
    (_, i) => (start + i) * step,
  );
}
const xTicks = computed(() =>
  ticks(domain.value.x0, domain.value.x1, compact.value ? 3 : 5),
);
const yTicks = computed(() => ticks(domain.value.y0, domain.value.y1, 4));
function tick(value: number) {
  return Number(value.toPrecision(4)).toLocaleString("en-US", {
    maximumSignificantDigits: 4,
  });
}
function path(points: Point[]) {
  let drawing = false;
  return points
    .map((point) => {
      if (!valid(point)) {
        drawing = false;
        return "";
      }
      const command = drawing ? "L" : "M";
      drawing = true;
      return `${command}${x(point[0]).toFixed(3)},${y(point[1]).toFixed(3)}`;
    })
    .join(" ");
}
watch(
  () => props.series.map((item) => item.id).join(","),
  () => {
    selectedSeries.value = 0;
    selectedIndex.value = 0;
  },
);
const active = computed(
  () => props.series[Math.min(selectedSeries.value, props.series.length - 1)],
);
const activePoint = computed(
  () =>
    active.value?.points?.[
      Math.min(selectedIndex.value, (active.value?.points?.length || 1) - 1)
    ],
);
</script>
<template>
  <div class="chart-axis-label">
    Y · {{ series[0]?.y.label_en }} ({{
      series[0]?.y.unit || "unit not reported"
    }})
  </div>
  <button
    class="chart-size-toggle"
    type="button"
    :aria-pressed="expanded"
    @click="expanded = !expanded"
  >
    {{
      expanded ? "Show entire chart" : "Enlarge chart for horizontal scrolling"
    }}
  </button>
  <p v-if="expanded" class="chart-scroll-hint">
    Scroll horizontally inside the chart to inspect the full time range.
  </p>
  <div
    ref="chartElement"
    class="chart-wrap"
    tabindex="0"
    role="region"
    aria-label="Measured chart; scroll horizontally when enlarged"
  >
    <svg
      class="measurement-chart"
      :viewBox="`0 0 ${chartWidth} ${bottom + 45}`"
      :style="{ minWidth: expanded ? '760px' : '0' }"
      role="img"
      :aria-label="
        'Original measurements: ' +
        series.map((item) => item.original_trial_label).join(', ')
      "
    >
      <title>
        {{ series[0]?.y.label_en }} against {{ series[0]?.x.label_en }}
      </title>
      <desc>
        Source numerical points connected in their original order. Missing
        coordinates create gaps. No smoothing or interpolation is applied to the
        data.
      </desc>
      <g v-for="value in yTicks" :key="'y' + value">
        <line
          :x1="left"
          :x2="right"
          :y1="y(value)"
          :y2="y(value)"
          stroke="#e1e7e5"
        />
        <text
          :x="left - 13"
          :y="y(value) + 4"
          text-anchor="end"
          class="chart-tick"
        >
          {{ tick(value) }}
        </text>
      </g>
      <g v-for="value in xTicks" :key="'x' + value">
        <line
          :x1="x(value)"
          :x2="x(value)"
          :y1="top"
          :y2="bottom"
          stroke="#eef1ef"
        />
        <text
          :x="x(value)"
          :y="bottom + 23"
          text-anchor="middle"
          class="chart-tick"
        >
          {{ tick(value) }}
        </text>
      </g>
      <path
        v-for="(item, index) in series"
        :key="item.id"
        :d="path(item.points || [])"
        fill="none"
        :stroke="palette[index]"
        stroke-width="2.2"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
      <circle
        v-if="activePoint && valid(activePoint)"
        :cx="x(activePoint[0])"
        :cy="y(activePoint[1])"
        r="5"
        :fill="palette[selectedSeries]"
        stroke="white"
        stroke-width="2"
      />
    </svg>
  </div>
  <div class="chart-axis-label">
    X · {{ series[0]?.x.label_en }} ({{
      series[0]?.x.unit || "unit not reported"
    }})
  </div>
  <div class="chart-legend">
    <button
      v-for="(item, index) in series"
      :key="item.id"
      :class="{ selected: selectedSeries === index }"
      :aria-pressed="selectedSeries === index"
      @click="
        selectedSeries = index;
        selectedIndex = 0;
      "
    >
      <span :style="{ background: palette[index] }" />{{
        item.original_trial_label
      }}<small>{{ item.point_count }} points</small>
    </button>
  </div>
  <div v-if="active?.points?.length" class="point-inspector">
    <label for="source-point"
      >Inspect source point
      <strong
        >{{ Math.min(selectedIndex + 1, active.points.length) }} /
        {{ active.points.length }}</strong
      ></label
    ><input
      id="source-point"
      v-model.number="selectedIndex"
      type="range"
      min="0"
      :max="active.points.length - 1"
    />
    <div class="point-readout">
      <span
        >X
        <strong>{{
          display(activePoint?.[0], active.x.unit || "")
        }}</strong></span
      ><span
        >Y
        <strong>{{
          display(activePoint?.[1], active.y.unit || "")
        }}</strong></span
      >
    </div>
  </div>
  <p class="chart-caption">
    Lines connect original numerical points. Time coordinates are retained as
    provided; zero events have not been independently aligned. No smoothing or
    new measurements are introduced.
  </p>
</template>
