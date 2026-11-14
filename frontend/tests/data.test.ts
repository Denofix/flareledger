import { describe, expect, it } from "vitest";
import { compatible, display, safeUrl } from "../src/lib/format";
import { makeSeries } from "./fixtures";

describe("scientific display boundaries", () => {
  it("retains zero while distinguishing missing measurements", () => {
    expect(display(0, "mm")).toBe("0 mm");
    expect(display(null, "mm")).toBe("Not reported");
    expect(display(undefined)).toBe("Not reported");
  });
  it("rejects different quantities even when both use millimetres", () => {
    const droplet = makeSeries();
    const flame = makeSeries({
      y: { name: "FlameDiameter_mm", label_en: "Flame diameter", unit: "mm" },
    });
    expect(compatible([droplet, flame])).toBe(false);
    expect(compatible([droplet, makeSeries({ id: "second" })])).toBe(true);
    expect(
      compatible([
        droplet,
        makeSeries({ x: { name: "Frames", label_en: "Frame", unit: null } }),
      ]),
    ).toBe(false);
  });
  it("allows source links without allowing executable URLs", () => {
    expect(safeUrl("https://doi.org/10.1234/test")).toBe(
      "https://doi.org/10.1234/test",
    );
    expect(safeUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeUrl("data:text/html,<script>alert(1)</script>")).toBeUndefined();
    expect(safeUrl("//untrusted.example")).toBeUndefined();
  });
});
