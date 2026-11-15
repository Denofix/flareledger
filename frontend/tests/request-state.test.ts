import { mount } from "@vue/test-utils";
import { expect, it } from "vitest";
import RequestState from "../src/components/RequestState.vue";
import { ApiError } from "../src/lib/api";

const global = { stubs: { RouterLink: { template: "<a><slot /></a>" } } };

it.each([404, 422])(
  "does not offer an unchanged retry for HTTP %i",
  (status) => {
    const wrapper = mount(RequestState, {
      props: { error: new ApiError(status, "test", "Test-only request error") },
      global,
    });
    expect(wrapper.get('[role="alert"]').text()).toContain(
      "Test-only request error",
    );
    expect(wrapper.find("button").exists()).toBe(false);
    expect(wrapper.text()).toContain("Back to investigations");
    if (status === 422)
      expect(wrapper.get("h2").text()).toBe("Check the request");
    wrapper.unmount();
  },
);

it.each([0, 503])(
  "retains manual retry for a recoverable HTTP %i failure",
  async (status) => {
    const wrapper = mount(RequestState, {
      props: {
        error: new ApiError(status, "test", "Test-only transient error"),
      },
      global,
    });
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("retry")).toHaveLength(1);
    wrapper.unmount();
  },
);
