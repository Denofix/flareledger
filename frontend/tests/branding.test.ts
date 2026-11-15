import { readFileSync } from "node:fs";
import type { Window as HappyWindow } from "happy-dom";
import { expect, it } from "vitest";

it.each([701, 768, 980])(
  "keeps the wordmark proportional at %i px while retaining compact icons",
  (width) => {
    const initialWidth = window.innerWidth;
    const initialHeight = window.innerHeight;
    const viewport = window as unknown as HappyWindow;
    const style = document.createElement("style");
    const brand = document.createElement("a");
    try {
      viewport.happyDOM.setWindowSize({ width, height: 1024 });
      style.textContent = readFileSync("src/style.css", "utf8");
      document.head.append(style);
      brand.className = "brand";
      const wordmark = document.createElement("img");
      wordmark.className = "product-logo";
      const icon = document.createElement("img");
      brand.append(wordmark, icon);
      document.body.append(brand);
      expect(getComputedStyle(wordmark).height).toBe("auto");
      expect(getComputedStyle(wordmark).width).not.toBe("33px");
      expect(getComputedStyle(icon).width).toBe("33px");
    } finally {
      brand.remove();
      style.remove();
      viewport.happyDOM.setWindowSize({
        width: initialWidth,
        height: initialHeight,
      });
    }
  },
);
