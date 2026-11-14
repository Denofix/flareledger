<script setup lang="ts">
import { ref } from "vue";
import { useRoute } from "vue-router";
import { ApiError, request } from "../lib/api";
import { useResource } from "../lib/useResource";
import type { AskResult } from "../lib/types";
import { corpusMeta } from "../lib/session";
import EvidenceCards from "../components/EvidenceCards.vue";
import RequestState from "../components/RequestState.vue";
import AppIcon from "../components/AppIcon.vue";
const route = useRoute();
const question = ref(String(route.query.q || ""));
const result = useResource<AskResult>();
function submit() {
  if (!question.value.trim() || result.loading.value) return;
  result.load(async (signal) => {
    const response = await request<AskResult>(
      "/ask",
      {
        method: "POST",
        signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.value.trim() }),
      },
      [503],
    );
    if (response.error && response.error.code !== "llm_unavailable")
      throw new ApiError(503, response.error.code, response.error.message);
    return response;
  });
}
</script>
<template>
  <header class="page-heading">
    <div class="eyebrow">
      QUESTIONS / RETRIEVED EVIDENCE / VISIBLE LIMITATIONS
    </div>
    <h1>A question is a starting point.</h1>
    <p class="page-intro">
      Find the evidence behind a combustion question. Source retrieval remains
      useful even when live generation is unavailable.
    </p>
  </header>
  <div class="ask-layout">
    <div>
      <form class="question-panel panel" @submit.prevent="submit">
        <label for="question" class="section-label"
          >WHAT WOULD YOU LIKE TO EXPLORE?</label
        ><textarea
          id="question"
          v-model="question"
          rows="5"
          maxlength="1000"
          placeholder="What evidence is available about PMMA in the BASS experiments?"
          required
        />
        <div class="question-footer">
          <span>{{ question.length }} / 1000</span
          ><button
            class="button"
            type="submit"
            :disabled="result.loading.value || !question.trim()"
          >
            {{
              result.loading.value
                ? "Finding evidence…"
                : "Find supporting evidence"
            }}<AppIcon name="arrow" :size="17" />
          </button>
        </div>
      </form>
      <div class="suggestion-row">
        <span>TRY A QUESTION</span
        ><button @click="question = 'PMMA'">PMMA</button
        ><button @click="question = 'FLEX droplet'">FLEX droplet</button
        ><button @click="question = 'oxygen'">Oxygen</button>
      </div>
      <RequestState
        :loading="result.loading.value"
        :error="result.error.value"
        @retry="submit"
      />
      <template v-if="result.data.value"
        ><section
          v-if="!result.data.value.live_generation_available"
          class="generation-notice"
          role="status"
        >
          <AppIcon name="spark" :size="25" />
          <div>
            <h2>Live generation is not configured</h2>
            <p>
              No AI answer was generated. The source-linked keyword results
              below are retrieved evidence, not a generated explanation.
            </p>
          </div>
        </section>
        <section
          v-else-if="result.data.value.answer"
          class="panel generated-answer"
        >
          <div class="eyebrow">FLARELEDGER-GENERATED EXPLANATION</div>
          <p>{{ result.data.value.answer }}</p>
        </section>
        <div class="result-summary">
          <strong>Retrieved evidence</strong
          ><span
            >{{ result.data.value.retrieved_evidence.length }} matches · keyword
            retrieval</span
          >
        </div>
        <EvidenceCards :items="result.data.value.retrieved_evidence" />
        <div
          v-if="!result.data.value.retrieved_evidence.length"
          class="empty-state"
        >
          <h2>No matching evidence found</h2>
          <p>
            Try fewer keywords. The current release does not infer a scientific
            answer from an empty result.
          </p>
        </div></template
      >
    </div>
    <aside class="ask-context">
      <div class="eyebrow">CURRENT MODE</div>
      <h2>Sources first.</h2>
      <div class="mode-badge">
        <span class="status-light amber" />{{
          corpusMeta?.live_generation_available
            ? "Generation available"
            : "Evidence retrieval"
        }}
      </div>
      <p>
        This release uses lexical keyword retrieval. It does not call an
        external language model.
      </p>
      <ol>
        <li>Search the reviewed corpus.</li>
        <li>Inspect matched records.</li>
        <li>Open the original source.</li>
        <li>Read the limitations.</li>
      </ol>
      <div class="metadata-note">
        This is a research exploration tool, not a validated fire safety
        recommendation. Missing evidence is never replaced with an invented
        source.
      </div>
      <RouterLink to="/evidence" class="text-link"
        >Go to evidence search <AppIcon name="external" :size="13"
      /></RouterLink>
    </aside>
  </div>
</template>
