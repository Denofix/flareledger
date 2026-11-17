import { effectScope } from "vue";
import { expect, it } from "vitest";
import { useResource } from "../src/lib/useResource";

it("an older request cannot replace the current page after navigation", async () => {
  const scope = effectScope();
  const resource = scope.run(() => useResource<string>())!;
  let resolveOld: (value: string) => void = () => {};
  const old = resource.load(
    () =>
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
  );
  await resource.load(async () => "current investigation");
  resolveOld("previous investigation");
  await old;
  expect(resource.data.value).toBe("current investigation");
  resource.reset();
  expect(resource.data.value).toBeNull();
  expect(resource.loading.value).toBe(false);
  scope.stop();
});
