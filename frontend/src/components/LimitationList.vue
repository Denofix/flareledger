<script setup lang="ts">
import type { Issue } from "../lib/types";
import AppIcon from "./AppIcon.vue";
defineProps<{ issues?: Issue[]; notes?: string[] }>();
</script>
<template>
  <aside v-if="issues?.length || notes?.length" class="limitations">
    <div class="section-label">
      <AppIcon name="alert" :size="17" /> Read with these limitations
    </div>
    <ul>
      <li v-for="issue in issues" :key="issue.id">
        {{ issue.description_en || issue.action || issue.id }}
      </li>
      <li v-for="note in notes" :key="note">{{ note }}</li>
    </ul>
  </aside>
</template>
