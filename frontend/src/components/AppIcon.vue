<script setup lang="ts">
defineProps<{ name: string; size?: number }>();
const paths: Record<string, string> = {
  grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  chart: "M4 3v17h17 M7 15l4-5 4 3 5-7",
  compare: "M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4",
  search: "M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15Zm5.5-2 5 5",
  book: "M4 3h12a3 3 0 0 1 3 3v15H6a3 3 0 0 1 0-6h13M6 3v12",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  external: "M14 3h7v7M21 3 10 14M10 3H4v17h17v-6",
  check: "M5 12l4 4L19 6",
  alert: "m12 3 10 18H2L12 3Zm0 6v5m0 3v.1",
  spark: "m12 3 2.7 6.3L21 12l-6.3 2.7L12 21l-2.7-6.3L3 12l6.3-2.7L12 3Z",
  close: "m6 6 12 12M18 6 6 18",
};
</script>
<template>
  <svg
    :width="size || 20"
    :height="size || 20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name] || paths.book" />
  </svg>
</template>
