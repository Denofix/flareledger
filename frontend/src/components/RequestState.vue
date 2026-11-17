<script setup lang="ts">
import { ApiError } from "../lib/api";
import AppIcon from "./AppIcon.vue";
defineProps<{ loading?: boolean; error?: Error | null }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div v-if="loading" class="loading-panel" role="status">
    <span class="loader" />Reading the source-linked corpus…
  </div>
  <section v-else-if="error" class="error-panel" role="alert">
    <AppIcon name="alert" :size="27" />
    <div>
      <h2>
        {{
          error instanceof ApiError && error.status === 404
            ? "Record not found"
            : error instanceof ApiError && error.status === 422
              ? "Check the request"
              : "We could not load this research"
        }}
      </h2>
      <p>{{ error.message }}</p>
      <button
        v-if="!(error instanceof ApiError && [404, 422].includes(error.status))"
        class="button secondary"
        @click="$emit('retry')"
      >
        Try again
      </button>
      <RouterLink to="/" class="text-link">Back to investigations</RouterLink>
    </div>
  </section>
</template>
