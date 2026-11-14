import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import RecordView from "../src/views/RecordView.vue";

afterEach(() => vi.unstubAllGlobals());
it("shows an evidence locator without inventing independent review", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            item: {
              id: "TEST-EVIDENCE",
              source_id: "TEST-SOURCE",
              locator: { table_id: "TEST-TABLE", data_row_number: 3 },
              extraction_method: "test_fixture_only",
              independent_human_review: false,
            },
            sources: [],
            evidence: [],
            quality_issues: [],
          }),
        ),
      ),
  );
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/evidence/:id",
        component: RecordView,
        props: { kind: "evidence" },
      },
      { path: "/evidence", component: { template: "<div />" } },
    ],
  });
  await router.push("/evidence/TEST-EVIDENCE");
  await router.isReady();
  const wrapper = mount(
    { template: "<RouterView />" },
    { global: { plugins: [router] } },
  );
  await flushPromises();
  expect(wrapper.text()).toContain("Original evidence locator");
  expect(wrapper.get("pre.locator").text()).toContain("TEST-TABLE");
  expect(wrapper.text()).toContain("Independent human review: Not recorded");
  wrapper.unmount();
});
