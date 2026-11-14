import type { Entity, Series, UnknownRecord } from "./types";

export function display(value: unknown, unit = ""): string {
  if (value === null || value === undefined || value === "")
    return "Not reported";
  if (typeof value === "number")
    return String(value) + (unit ? " " + unit : "");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value))
    return value.map((item) => display(item)).join(", ");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}
export function label(value: string): string {
  return value.replace(/_/g, " ").replace(/^./, (first) => first.toUpperCase());
}
export function entityTitle(item: Entity): string {
  return String(
    item.title_en ||
      item.title ||
      item.original_trial_label ||
      item.original_test_id ||
      item.material ||
      item.id,
  );
}
export function safeUrl(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
export function compatible(series: Series[]): boolean {
  if (series.length < 2) return false;
  const signatures = series.map((item) =>
    JSON.stringify([item.x.name, item.x.unit, item.y.name, item.y.unit]),
  );
  return signatures.every((signature) => signature === signatures[0]);
}
export function simpleFields(item: UnknownRecord): [string, unknown][] {
  return Object.entries(item).filter(
    ([key, value]) =>
      ![
        "id",
        "title",
        "title_en",
        "summary_en",
        "points",
        "source_rows",
        "source_ids",
        "evidence_ids",
        "quality_issue_ids",
      ].includes(key) &&
      (value === null ||
        ["string", "number", "boolean"].includes(typeof value)),
  );
}
