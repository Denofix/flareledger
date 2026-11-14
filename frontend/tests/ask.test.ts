import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import AskView from "../src/views/AskView.vue";
import { makeSearchHit } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());
it("an unavailable model shows retrieved evidence mode instead of a fabricated answer", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "llm_unavailable", message: "Not configured" },
          answer: null,
          retrieved_evidence: [],
          retrieval_method: "lexical_keywords",
          live_generation_available: false,
        }),
        { status: 503 },
      ),
    ),
  );
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/ask", component: AskView }],
  });
  await router.push("/ask");
  await router.isReady();
  const wrapper = mount(AskView, { global: { plugins: [router] } });
  await wrapper.get("textarea").setValue("PMMA");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(wrapper.text()).toContain("No AI answer was generated");
  expect(wrapper.text()).toContain("No matching evidence found");
  expect(wrapper.find(".generated-answer").exists()).toBe(false);
  wrapper.unmount();
});

it("retains populated source retrieval when the model is unavailable", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "llm_unavailable", message: "Not configured" },
          answer: null,
          retrieved_evidence: [makeSearchHit()],
          retrieval_method: "lexical_keywords",
          live_generation_available: false,
        }),
        { status: 503 },
      ),
    ),
  );
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/ask", component: AskView },
      { path: "/records/:id", component: { template: "<div />" } },
      { path: "/sources/:id", component: { template: "<div />" } },
    ],
  });
  await router.push("/ask");
  await router.isReady();
  const wrapper = mount(AskView, { global: { plugins: [router] } });
  await wrapper.get("textarea").setValue("Test-only question");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(wrapper.text()).toContain("No AI answer was generated");
  expect(wrapper.text()).toContain("Synthetic test fixture record");
  expect(wrapper.get(".evidence-card h3 a").attributes("href")).toBe(
    "/records/TEST-RECORD",
  );
  expect(wrapper.find(".generated-answer").exists()).toBe(false);
  wrapper.unmount();
});
