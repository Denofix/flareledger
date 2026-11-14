<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { corpusMeta, corpusError, refreshCorpus } from "./lib/session";
import AppIcon from "./components/AppIcon.vue";
const route = useRoute();
const menuOpen = ref(false);
const nav = [
  { path: "/", label: "Investigations", icon: "grid", index: "01" },
  { path: "/measurements", label: "Measurements", icon: "chart", index: "02" },
  { path: "/compare", label: "Compare series", icon: "compare", index: "03" },
  { path: "/evidence", label: "Evidence search", icon: "search", index: "04" },
  { path: "/ask", label: "Ask FlareLedger", icon: "spark", index: "05" },
];
function active(path: string) {
  return path === "/"
    ? route.path === "/" || route.path.startsWith("/investigations/")
    : route.path === path;
}
onMounted(refreshCorpus);
</script>
<template>
  <a class="skip-link" href="#main">Skip to research</a>
  <header class="mobile-header">
    <RouterLink to="/" class="brand"
      ><img
        src="/favicon.svg"
        width="32"
        height="32"
        alt=""
      />FlareLedger</RouterLink
    ><button
      class="icon-button"
      :aria-expanded="menuOpen"
      aria-controls="sidebar"
      aria-label="Toggle navigation"
      @click="menuOpen = !menuOpen"
    >
      <AppIcon :name="menuOpen ? 'close' : 'grid'" />
    </button>
  </header>
  <aside id="sidebar" class="sidebar" :class="{ 'is-open': menuOpen }">
    <RouterLink to="/" class="brand" @click="menuOpen = false"
      ><img src="/favicon.svg" width="38" height="38" alt="" /><span
        >FlareLedger<small>RESEARCH, TRACEABLE.</small></span
      ></RouterLink
    >
    <div class="nav-caption">THE RESEARCH DESK</div>
    <nav aria-label="Main navigation">
      <RouterLink
        v-for="item in nav"
        :key="item.path"
        :to="item.path"
        :class="{ active: active(item.path) }"
        @click="menuOpen = false"
        ><AppIcon :name="item.icon" /><span>{{ item.label }}</span
        ><small>{{ item.index }}</small></RouterLink
      >
    </nav>
    <div class="sidebar-note">
      <span class="orbit-icon"><AppIcon name="external" :size="30" /></span>
      <p>A clearer view of<br />combustion in microgravity.</p>
      <a
        href="https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/"
        target="_blank"
        rel="noopener noreferrer"
        >About the challenge <AppIcon name="external" :size="14"
      /></a>
    </div>
    <div class="corpus-status">
      <span
        class="status-light"
        :class="{ amber: !corpusMeta || corpusError }"
      />
      <div>
        <strong>{{
          corpusMeta && !corpusError
            ? "Source-linked corpus"
            : corpusError
              ? "API unavailable"
              : "Connecting to corpus"
        }}</strong><small>{{
          corpusMeta
            ? corpusMeta.corpus_version.split(":")[0]
            : corpusError
              ? "Retry connection"
              : "Checking connection"
        }}</small>
      </div>
      <button
        class="icon-button"
        aria-label="Refresh corpus connection"
        @click="refreshCorpus"
      >
        ↻
      </button>
    </div>
    <div class="sidebar-credit">
      AN INDEPENDENT PROJECT BY<br /><strong>PROOFONAUTS</strong
      ><a
        href="https://github.com/Denofix/flareledger"
        target="_blank"
        rel="noopener noreferrer"
        >View source code <AppIcon name="external" :size="13"
      /></a>
    </div>
  </aside>
  <div class="workspace">
    <div class="topbar">
      <div>
        <span class="breadcrumb">Research workspace</span
        ><span class="breadcrumb-separator">/</span>{{ route.meta.label }}
      </div>
      <span class="data-label"><span /> NASA PSI DATA</span>
    </div>
    <main id="main" tabindex="-1"><RouterView /></main>
    <footer class="footer">
      <span
        >Independent hackathon project. NASA has not reviewed or endorsed
        FlareLedger.</span
      ><span>Original data. Visible limitations. Traceable sources.</span>
    </footer>
  </div>
</template>
