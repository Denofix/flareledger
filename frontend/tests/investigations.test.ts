import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import CatalogView from "../src/views/CatalogView.vue";
import InvestigationView from "../src/views/InvestigationView.vue";
import type { Investigation } from "../src/lib/types";

afterEach(() => vi.unstubAllGlobals());

function investigation(id: string, acronym: string | null): Investigation {
  return {
    id,
    acronym,
    title: "Synthetic fixture",
    title_en: "Synthetic fixture",
    summary_en: "Test fixture only",
    fuel_phase: "solid",
    gravity_regime: "microgravity",
    gravity_regime_basis: "test",
    facility_as_reported: null,
    flight_platform_as_reported: null,
    doi: "test-only",
    version: 1,
    availability: "metadata",
    tags: [],
    source_ids: [],
  };
}

async function setup(
  component: typeof CatalogView | typeof InvestigationView,
  path: string,
) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: CatalogView },
      { path: "/investigations/:id", component: InvestigationView },
      { path: "/ask", component: { template: "<div />" } },
      { path: "/evidence", component: { template: "<div />" } },
      { path: "/measurements", component: { template: "<div />" } },
    ],
  });
  await router.push(path);
  await router.isReady();
  const wrapper = mount(component, { global: { plugins: [router] } });
  await flushPromises();
  return wrapper;
}

it("keeps a missing-acronym catalog label stable when preceding cards are filtered out", async () => {
  const rows = [
    investigation("TEST-1", "FIRST"),
    investigation("TEST-2", null),
  ];
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ items: rows, total: 2 })),
      ),
  );
  const wrapper = await setup(CatalogView, "/");
  expect(wrapper.findAll(".card-eyebrow").map((el) => el.text())).toEqual([
    "FIRST",
    "INVESTIGATION",
  ]);
  await wrapper.get('input[type="search"]').setValue("TEST-2");
  expect(wrapper.findAll(".card-eyebrow").map((el) => el.text())).toEqual([
    "INVESTIGATION",
  ]);
  expect(
    wrapper
      .get('a[href="/investigations/TEST-2"]')
      .text()
      .match(/TEST-2/g),
  ).toHaveLength(1);
  wrapper.unmount();
});

it("uses the source investigation ID for both evidence links when the acronym is missing", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) =>
      Promise.resolve(
        new Response(
          JSON.stringify(
            url.includes("/investigations/")
              ? {
                  item: investigation("TEST-2", null),
                  sources: [],
                  evidence: [],
                  quality_issues: [],
                }
              : { items: [], total: url.includes("/records") ? 13 : 0 },
          ),
        ),
      ),
    ),
  );
  const wrapper = await setup(InvestigationView, "/investigations/TEST-2");
  expect(
    wrapper.get(".page-heading .eyebrow").text().replace(/\s+/g, " "),
  ).toBe("TEST-2 / VERSION 1");
  expect(wrapper.get('a[href="/ask?q=TEST-2"]').text()).toContain(
    "Explore the evidence",
  );
  expect(wrapper.get('a[href="/evidence?q=TEST-2"]').text()).toContain(
    "Search related evidence",
  );
  wrapper.unmount();
});
