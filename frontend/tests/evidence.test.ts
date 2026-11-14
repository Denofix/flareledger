import { mount } from "@vue/test-utils";
import { expect, it } from "vitest";
import EvidenceCards from "../src/components/EvidenceCards.vue";
import { makeSearchHit } from "./fixtures";

it("renders flattened API search hits and points readers to full source evidence", () => {
  const hit = makeSearchHit();
  const wrapper = mount(EvidenceCards, {
    props: { items: [hit] },
    global: {
      stubs: {
        RouterLink: { props: ["to"], template: '<a :href="to"><slot /></a>' },
      },
    },
  });
  expect(wrapper.get("h3 a").attributes("href")).toBe("/records/TEST-RECORD");
  expect(wrapper.text()).toContain(hit.title);
  expect(wrapper.text()).toContain(hit.excerpt);
  expect(wrapper.text()).toContain("TEST-EVIDENCE");
  expect(wrapper.find('a[href="/evidence/TEST-EVIDENCE"]').exists()).toBe(true);
  expect(wrapper.text()).toContain("full locators");
  expect(wrapper.find(".source-title").text()).toBe("Synthetic source fixture");
  wrapper.unmount();
});
