import { describe, expect, it } from "vitest";
import { canTransition } from "./status";

describe("canTransition", () => {
  it("allows the normal flow", () => {
    expect(canTransition("to_apply", "applied")).toBe(true);
    expect(canTransition("applied", "interview")).toBe(true);
    expect(canTransition("interview", "offer")).toBe(true);
  });

  it("forbids skipping the application step", () => {
    expect(canTransition("to_apply", "interview")).toBe(false);
  });

  it("allows reopening after a silence or a refusal", () => {
    expect(canTransition("no_response", "interview")).toBe(true);
    expect(canTransition("rejected", "offer")).toBe(true);
  });

  it("allows several interview rounds", () => {
    expect(canTransition("interview", "interview")).toBe(true);
  });
});
