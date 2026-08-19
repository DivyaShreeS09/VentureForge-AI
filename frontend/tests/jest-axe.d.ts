import "vitest";

// jest-axe ships its matcher typings against Jest's `jest.Matchers`; this repo runs
// Vitest, so `toHaveNoViolations()` is re-declared against Vitest's `Assertion`
// interface instead — without this, `expect(results).toHaveNoViolations()` type-checks
// as a nonexistent method even though the matcher is registered correctly at runtime
// (tests/setup.ts).
declare module "vitest" {
  interface Assertion {
    toHaveNoViolations(): void;
  }
}
