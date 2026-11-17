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
  expect(wrapper.text()).toContain("No SI answer was generated");
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
  expect(wrapper.text()).toContain("No SI answer was generated");
  expect(wrapper.text()).toContain("Synthetic test fixture record");
  expect(wrapper.get(".evidence-card h3 a").attributes("href")).toBe(
    "/records/TEST-RECORD",
  );
  expect(wrapper.find(".generated-answer").exists()).toBe(false);
  wrapper.unmount();
});

async function answered(body: object, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })),
  );
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/ask", component: AskView },
      { path: "/records/:id", component: { template: "<div />" } },
      { path: "/sources/:id", component: { template: "<div />" } },
      { path: "/measurements", component: { template: "<div />" } },
      { path: "/", component: { template: "<div />" } },
    ],
  });
  await router.push("/ask");
  await router.isReady();
  const wrapper = mount(AskView, { global: { plugins: [router] } });
  await wrapper.get("textarea").setValue("PMMA");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  return wrapper;
}

const base = {
  answer: null,
  retrieved_evidence: [makeSearchHit()],
  retrieval_method: "lexical_keywords",
  live_generation_available: true,
};

it.each(["gemini-3.6-flash", "gemini-4-hydrogen"])(
  "labels %s interpretation and renders exact excerpts as text with verified source routes",
  async (model) => {
    const wrapper = await answered({
      ...base,
      status: "generated",
      answer: "<img src=x onerror=alert(1)> [TEST-RECORD]",
      provider: "gemini",
      model,
      corpus_version: "TEST-CORPUS",
      notice:
        "FlareLedger-generated interpretation; scientific correctness is not established.",
      citations: [
        {
          context_id: "TEST-RECORD",
          source_id: "TEST-SOURCE",
          quote: "An exact test-only context excerpt.",
        },
      ],
      limitations: ["Test-only limitation; not measured data."],
    });
    const answer = wrapper.get(".generated-answer");
    expect(answer.text()).toContain("FLARELEDGER-GENERATED EXPLANATION");
    expect(answer.text()).toContain(model);
    expect(wrapper.get(".mode-badge").text()).toContain("Generation enabled");
    expect(wrapper.text()).not.toContain("Generation available");
    expect(answer.text()).toContain("<img src=x onerror=alert(1)>");
    expect(answer.find("img").exists()).toBe(false);
    expect(answer.text()).toContain("Exact context excerpt");
    expect(answer.get("a").attributes("href")).toBe("/sources/TEST-SOURCE");
    expect(answer.text()).toContain("Test-only limitation");
    expect(wrapper.text()).not.toContain("No SI answer was generated");
    wrapper.unmount();
  },
);

it.each([
  ["provider_quota_exhausted", "Gemini generation limit reached"],
  ["invalid_model_output", "No supported explanation was returned"],
  ["provider_unavailable", "Live generation is unavailable"],
])(
  "keeps evidence available after %s without promising provider availability",
  async (reason, title) => {
    const wrapper = await answered(
      {
        ...base,
        status: "unavailable",
        error: { code: "llm_unavailable", reason },
      },
      503,
    );
    expect(wrapper.get(".generation-notice h2").text()).toBe(title);
    expect(wrapper.get(".mode-badge").text()).toContain("Generation enabled");
    expect(wrapper.find(".evidence-card").exists()).toBe(true);
    expect(wrapper.find(".generated-answer").exists()).toBe(false);
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  },
);

it("keeps source retrieval visible during a shared quota rejection", async () => {
  const wrapper = await answered(
    {
      ...base,
      status: "rate_limited",
      retry_after_seconds: 61,
      error: { code: "rate_limited", message: "Shared demo limit" },
    },
    429,
  );
  expect(wrapper.text()).toContain("Shared generation limit reached");
  expect(wrapper.text()).toContain("approximately 61 seconds");
  expect(wrapper.find(".evidence-card").exists()).toBe(true);
  expect(wrapper.find(".generated-answer").exists()).toBe(false);
  wrapper.unmount();
});

it("shows an explicit insufficient-evidence state without a generated answer", async () => {
  const wrapper = await answered({
    ...base,
    status: "insufficient_evidence",
    limitations: ["No measured support"],
  });
  expect(wrapper.text()).toContain("Insufficient supporting evidence");
  expect(wrapper.text()).toContain("No SI answer was generated");
  expect(wrapper.find(".generated-answer").exists()).toBe(false);
  wrapper.unmount();
});

it("handles an infrastructure 503 without treating it as the structured Ask result", async () => {
  const wrapper = await answered(
    { error: { code: "upstream_unavailable", message: "API restarting" } },
    503,
  );
  expect(wrapper.get('[role="alert"]').text()).toContain("API restarting");
  expect(wrapper.find(".generated-answer").exists()).toBe(false);
  wrapper.unmount();
});

it("links a retrieved measured-series entry to its original chart", async () => {
  const wrapper = await answered({
    ...base,
    status: "insufficient_evidence",
    retrieved_evidence: [
      { ...makeSearchHit(), kind: "series", id: "TEST-SERIES" },
    ],
  });
  expect(wrapper.get(".evidence-card h3 a").attributes("href")).toBe(
    "/measurements?ids=TEST-SERIES",
  );
  wrapper.unmount();
});
