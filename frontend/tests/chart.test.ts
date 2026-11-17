import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import type { Window as HappyWindow } from "happy-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import SeriesChart from "../src/components/SeriesChart.vue";
import SourceList from "../src/components/SourceList.vue";
import { makeSeries } from "./fixtures";
afterEach(() => vi.unstubAllGlobals());

describe("measured series", () => {
  it.each([768, 1024])(
    "allows enlarged-chart scrolling at a %i px viewport with the full stylesheet",
    async (viewport) => {
      const initialWidth = window.innerWidth;
      const initialHeight = window.innerHeight;
      const viewportWindow = window as unknown as HappyWindow;
      viewportWindow.happyDOM.setWindowSize({ width: viewport, height: 900 });
      const style = document.createElement("style");
      style.textContent = readFileSync("src/style.css", "utf8");
      document.head.append(style);
      vi.stubGlobal(
        "ResizeObserver",
        class {
          constructor(private callback: (entries: unknown[]) => void) {}
          observe() {
            this.callback([{ contentRect: { width: 580 } }]);
          }
          disconnect() {}
        },
      );
      const wrapper = mount(SeriesChart, {
        props: { series: [makeSeries()] },
        attachTo: document.body,
      });
      try {
        await wrapper.vm.$nextTick();
        const container = wrapper.get(".chart-wrap").element;
        const overflowX = () =>
          getComputedStyle(container).overflowX ||
          getComputedStyle(container).overflow;
        expect(window.innerWidth).toBe(viewport);
        expect(overflowX()).toBe("hidden");
        await wrapper.get(".chart-size-toggle").trigger("click");
        expect(wrapper.get("svg").attributes("style")).toContain("760px");
        expect(overflowX()).toBe("auto");
        await wrapper.get(".chart-size-toggle").trigger("click");
        expect(overflowX()).toBe("hidden");
        expect(wrapper.get("svg").attributes("viewBox")).toBe("0 0 580 360");
      } finally {
        wrapper.unmount();
        style.remove();
        viewportWindow.happyDOM.setWindowSize({
          width: initialWidth,
          height: initialHeight,
        });
      }
    },
  );
  it.each([299, 329])(
    "fits the full chart in a %i px container with visible axis units",
    async (width) => {
      vi.stubGlobal(
        "ResizeObserver",
        class {
          constructor(private callback: (entries: unknown[]) => void) {}
          observe() {
            this.callback([{ contentRect: { width } }]);
          }
          disconnect() {}
        },
      );
      const series = makeSeries({
        x: {
          name: "Time_sec",
          label_en: "Time in the original source file",
          unit: "s",
        },
        y: {
          name: "FlameDiameter_mm",
          label_en: "Flame diameter from the color camera",
          unit: "mm",
        },
      });
      const wrapper = mount(SeriesChart, { props: { series: [series] } });
      await wrapper.vm.$nextTick();
      expect(wrapper.get("svg").attributes("viewBox")).toBe(`0 0 ${width} 275`);
      expect(wrapper.get("svg").attributes("style")).toContain("min-width: 0");
      expect(wrapper.findAll("svg text.chart-axis")).toHaveLength(0);
      expect(
        wrapper.findAll(".chart-axis-label").map((label) => label.text()),
      ).toEqual([
        "Y · Flame diameter from the color camera (mm)",
        "X · Time in the original source file (s)",
      ]);
      await wrapper.get(".chart-size-toggle").trigger("click");
      expect(wrapper.get("svg").attributes("viewBox")).toBe("0 0 760 360");
      expect(wrapper.text()).toContain("Scroll horizontally");
      await wrapper.get(".chart-size-toggle").trigger("click");
      expect(wrapper.get("svg").attributes("viewBox")).toBe(`0 0 ${width} 275`);
      wrapper.unmount();
    },
  );
  it("selects the fourth series without changing its source point values", async () => {
    const series = Array.from({ length: 4 }, (_, i) =>
      makeSeries({
        id: `SERIES-${i}`,
        original_trial_label: `Run ${i}`,
        points: [[-1.5, i + 0.123456789]],
        point_count: 1,
      }),
    );
    const wrapper = mount(SeriesChart, { props: { series } });
    expect(wrapper.findAll("svg path")).toHaveLength(4);
    await wrapper.findAll(".chart-legend button")[3]!.trigger("click");
    expect(wrapper.get(".point-readout").text()).toContain("3.123456789 mm");
    expect(
      wrapper.findAll(".chart-legend button")[3]!.attributes("aria-pressed"),
    ).toBe("true");
    wrapper.unmount();
  });
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
