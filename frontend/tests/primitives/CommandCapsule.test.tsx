import { act, render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "jest-axe";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  CommandCapsule,
  CommandCapsuleProvider,
  useRegisterCommandSections,
} from "../../src/primitives/CommandCapsule";

function Registrar({ sections }: { sections: { id: string; label: string }[] }) {
  useRegisterCommandSections(sections);
  return (
    <>
      {sections.map((s) => (
        <div key={s.id} id={s.id} />
      ))}
    </>
  );
}

function renderCapsule(sections: { id: string; label: string }[] = []) {
  return render(
    <MemoryRouter>
      <CommandCapsuleProvider>
        {sections.length > 0 && <Registrar sections={sections} />}
        <CommandCapsule />
      </CommandCapsuleProvider>
    </MemoryRouter>,
  );
}

// The docked chip only appears once a registered section has genuinely scrolled into
// view (see CommandCapsule.tsx's IntersectionObserver) — not the instant it's
// registered, which used to make the chip appear on mount, potentially long before the
// founder scrolls anywhere near it, overlapping unrelated content above it. This fake
// lets tests simulate "the section is now in view" explicitly and deterministically.
let ioCallback: IntersectionObserverCallback | null = null;
class FakeIntersectionObserver {
  constructor(cb: IntersectionObserverCallback) {
    ioCallback = cb;
  }
  observe() {}
  unobserve() {}
  disconnect() {}
}

function markInView(id: string) {
  const el = document.getElementById(id)!;
  act(() => {
    ioCallback?.(
      [{ isIntersecting: true, intersectionRatio: 1, target: el } as IntersectionObserverEntry],
      {} as IntersectionObserver,
    );
  });
}

// The docked chip also requires a genuine scroll distance, not just an in-view section (see
// CommandCapsule.tsx: a tall first section reports "in view" for its entire height, which used to
// make the chip appear at scroll position zero and sit on top of that section's own text).
function simulateScroll(y: number) {
  Object.defineProperty(window, "scrollY", { value: y, configurable: true });
  act(() => {
    window.dispatchEvent(new Event("scroll"));
  });
}

describe("CommandCapsule", () => {
  beforeEach(() => {
    vi.stubGlobal("IntersectionObserver", FakeIntersectionObserver);
  });
  afterEach(() => {
    ioCallback = null;
    vi.unstubAllGlobals();
    // `simulateScroll` mutates `window.scrollY` directly (jsdom's window persists across tests
    // within this file) — reset it so one test's scroll position never leaks into the next.
    Object.defineProperty(window, "scrollY", { value: 0, configurable: true });
  });

  it("renders no docked chip when no sections are registered", () => {
    renderCapsule();
    expect(screen.queryByRole("button", { name: /jump to/i })).not.toBeInTheDocument();
  });

  it("does not dock a chip merely because sections were registered — only once one is actually in view", () => {
    renderCapsule([{ id: "s1", label: "Section One" }]);
    expect(screen.queryByRole("button", { name: "Section One" })).not.toBeInTheDocument();
  });

  it("docks a visible chip once a registered section is actually observed in view", () => {
    renderCapsule([{ id: "s1", label: "Section One" }]);
    markInView("s1");
    simulateScroll(200);
    expect(screen.getByRole("button", { name: "Section One" })).toBeInTheDocument();
  });

  it("withholds the chip until the page has actually scrolled, even once a section reports in view", () => {
    // A tall first section can report "in view" for its entire height, including before any
    // scrolling — the chip must not dock on that alone, or it sits on top of that section's own
    // text at scroll position zero (the real bug this guards against).
    renderCapsule([{ id: "s1", label: "Section One" }]);
    markInView("s1");
    expect(screen.queryByRole("button", { name: "Section One" })).not.toBeInTheDocument();
  });

  it("expands into a listbox with real sections plus the two global commands", () => {
    renderCapsule([{ id: "s1", label: "Section One" }]);
    markInView("s1");
    simulateScroll(200);
    fireEvent.click(screen.getByRole("button", { name: "Section One" }));
    const listbox = screen.getByRole("listbox", { name: "Jump to a section" });
    expect(within(listbox).getByText("Section One")).toBeInTheDocument();
    expect(within(listbox).getByText("Start a new analysis")).toBeInTheDocument();
    expect(within(listbox).getByText("Open a previous venture")).toBeInTheDocument();
  });

  it("opens on Ctrl+K even with no docked chip (global reachability)", () => {
    renderCapsule();
    fireEvent.keyDown(document, { key: "k", ctrlKey: true });
    expect(screen.getByRole("listbox", { name: "Jump to a section" })).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    renderCapsule();
    fireEvent.keyDown(document, { key: "k", ctrlKey: true });
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    // AnimatePresence keeps the exiting element mounted for its exit transition
    // before removing it — a synchronous assertion here would race that animation.
    await waitFor(() => expect(screen.queryByRole("listbox")).not.toBeInTheDocument());
  });

  it("has no accessibility violations while expanded", async () => {
    const { container } = renderCapsule([{ id: "s1", label: "Section One" }]);
    markInView("s1");
    simulateScroll(200);
    fireEvent.click(screen.getByRole("button", { name: "Section One" }));
    expect(await axe(container)).toHaveNoViolations();
  });
});
