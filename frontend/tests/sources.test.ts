import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import SourceList from "../src/components/SourceList.vue";
import RecordView from "../src/views/RecordView.vue";
import type { Source } from "../src/lib/types";

afterEach(() => vi.unstubAllGlobals());

it("keeps file and investigation versions distinct while navigating to the source", async () => {
  const source: Source = {
    id: "TEST-FILE",
    title: "Test-only source file",
    url: "https://example.org/download?file=test&version=2&redirect=false",
    file_version: 2,
    investigation_version: 4,
    doi: "10.1234/test-only",
    license_identifier: "CC0-1.0",
  };
  const fetcher = vi
    .fn()
    .mockResolvedValue(
      new Response(
        JSON.stringify({
          item: source,
          sources: [source],
          evidence: [],
          quality_issues: [],
        }),
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: SourceList, props: { sources: [source] } },
      {
        path: "/sources/:id",
        component: RecordView,
        props: { kind: "sources" },
      },
      { path: "/evidence", component: { template: "<div />" } },
    ],
  });
  await router.push("/");
  await router.isReady();
  const wrapper = mount(
    { template: "<RouterView />" },
    { global: { plugins: [router] } },
  );
  await flushPromises();
  expect(wrapper.text()).toContain("File version 2");
  expect(wrapper.text()).toContain("Investigation version 4");
  expect(wrapper.text()).toContain("DOI 10.1234/test-only");
  expect(wrapper.text()).toContain("CC0-1.0");
  expect(wrapper.get('a[target="_blank"]').attributes("href")).toBe(source.url);
  await wrapper.get("a.source-title").trigger("click");
  await flushPromises();
  expect(router.currentRoute.value.path).toBe("/sources/TEST-FILE");
  expect(fetcher.mock.calls[0]![0]).toBe("/api/sources/TEST-FILE");
  expect(wrapper.get("h1").text()).toBe(source.title);
  expect(wrapper.get('a.button[target="_blank"]').attributes("href")).toBe(
    source.url,
  );
  wrapper.unmount();
});

it("does not invent missing versions or a DOI", () => {
  const wrapper = mount(SourceList, {
    props: { sources: [{ id: "NO-VERSION", title: "No recorded version" }] },
    global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
  });
  expect(wrapper.get(".source-meta").text()).not.toContain("version");
  expect(wrapper.get(".source-meta").text()).not.toContain("DOI");
  wrapper.unmount();
});

it("retains a legacy version when no scoped version is recorded", () => {
  const wrapper = mount(SourceList, {
    props: { sources: [{ id: "LEGACY", title: "Legacy fixture", version: 3 }] },
    global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
  });
  expect(wrapper.get(".source-meta").text()).toContain("Version 3");
  wrapper.unmount();
});
