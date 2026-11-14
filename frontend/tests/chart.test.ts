import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SeriesChart from "../src/components/SeriesChart.vue";
import SourceList from "../src/components/SourceList.vue";
import { makeSeries } from "./fixtures";

describe("measured series", () => {
  it("keeps a missing coordinate as a gap and exposes original point values", async () => {
    const series = makeSeries({
      point_count: 4,
      points: [
        [4, 2],
        [5, 0],
        [null, 1],
        [8, 3],
      ],
    });
    const wrapper = mount(SeriesChart, { props: { series: [series] } });
    const path = wrapper.get("svg path").attributes("d") || "";
    expect((path.match(/M/g) || []).length).toBe(2);
    expect((path.match(/L/g) || []).length).toBe(1);
    await wrapper.get('input[type="range"]').setValue("1");
    expect(wrapper.get(".point-readout").text()).toContain("0 mm");
    await wrapper.get('input[type="range"]').setValue("2");
    expect(wrapper.get(".point-readout").text()).toContain("Not reported");
    expect(wrapper.text()).toContain("3 / 4");
    expect(wrapper.get("svg title").text()).toContain("Droplet diameter");
  });
  it("renders source titles as text and removes executable outbound links", () => {
    const wrapper = mount(SourceList, {
      props: {
        sources: [
          {
            id: "TEST",
            title: "<img src=x onerror=alert(1)>",
            url: "javascript:alert(1)",
          },
        ],
      },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find('a[target="_blank"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("<img src=x onerror=alert(1)>");
  });
});
