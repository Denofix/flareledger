import type { SearchItem, Series } from "../src/lib/types";

export function makeSeries(overrides: Partial<Series> = {}): Series {
  return {
    id: "TEST-SERIES",
    investigation_id: "TEST",
    original_trial_label: "Synthetic test fixture",
    x: { name: "Time_sec", label_en: "Source time", unit: "s" },
    y: { name: "DropletDiameter_mm", label_en: "Droplet diameter", unit: "mm" },
    point_count: 3,
    points: [
      [4, 2],
      [5, 0],
      [6, 1],
    ],
    uncertainty: null,
    source_ids: [],
    synthetic: true,
    measurement_origin: "test_only",
    ...overrides,
  };
}

export function makeSearchHit(): SearchItem {
  return {
    kind: "record",
    id: "TEST-RECORD",
    investigation_id: "TEST-INVESTIGATION",
    title: "Synthetic test fixture record",
    excerpt: "Contract fixture only; no scientific claim.",
    source_ids: ["TEST-SOURCE"],
    evidence_ids: ["TEST-EVIDENCE"],
    sources: [
      {
        id: "TEST-SOURCE",
        title: "Synthetic source fixture",
        url: "https://example.org/test-only",
      },
    ],
  };
}
