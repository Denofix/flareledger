import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import MeasurementsView from "../src/views/MeasurementsView.vue";
import type { Detail, Series } from "../src/lib/types";
import { makeSeries } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());
const detail = (item: Series): Detail<Series> => ({
  item,
  sources: [],
  evidence: [],
  quality_issues: [],
});

async function openComparison(second: Series) {
  const first = makeSeries({ id: "SERIES-A" });
  const fetcher = vi.fn(async (url: string) => {
    const path = new URL(url, "https://test.invalid").pathname;
    let payload: unknown;
    if (path === "/api/series")
      payload = { items: [first, second], total: 2, limit: 100, offset: 0 };
    else if (path === "/api/series/SERIES-A") payload = detail(first);
    else if (path === "/api/series/SERIES-B") payload = detail(second);
    else if (path === "/api/compare")
      payload = {
        series: [detail(first), detail(second)],
        transformations: [],
        limitations: ["Test-only source limitation."],
      };
    else throw new Error("Unexpected request: " + path);
    return new Response(JSON.stringify(payload));
  });
  vi.stubGlobal("fetch", fetcher);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/compare", component: MeasurementsView }],
  });
  await router.push("/compare?ids=SERIES-A,SERIES-B");
  await router.isReady();
  const wrapper = mount(MeasurementsView, { global: { plugins: [router] } });
  await flushPromises();
  return { wrapper, fetcher };
}

describe("comparison navigation", () => {
  it("loads a direct URL with explicit series IDs and retains source limitations", async () => {
    const { wrapper, fetcher } = await openComparison(
      makeSeries({ id: "SERIES-B" }),
    );
    expect(wrapper.findAll("svg.measurement-chart path")).toHaveLength(2);
    expect(wrapper.text()).toContain("Test-only source limitation.");
    expect(
      fetcher.mock.calls.some(([url]) => url.startsWith("/api/compare?ids=")),
    ).toBe(true);
    wrapper.unmount();
  });
  it("does not draw an overlay or request comparison for different quantities", async () => {
    const { wrapper, fetcher } = await openComparison(
      makeSeries({
        id: "SERIES-B",
        y: { name: "FlameDiameter_mm", label_en: "Flame diameter", unit: "mm" },
      }),
    );
    expect(wrapper.find("svg.measurement-chart").exists()).toBe(false);
    expect(wrapper.text()).toContain("different quantities");
    expect(
      fetcher.mock.calls.some(([url]) => url.startsWith("/api/compare")),
    ).toBe(false);
    wrapper.unmount();
  });
});
