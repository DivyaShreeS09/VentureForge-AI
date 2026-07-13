import { useEffect, useRef } from "react";

/** A soft light that trails the cursor across the whole app — desktop/fine-pointer only, and
 * fully inert under `prefers-reduced-motion` (the effect never attaches a listener in that case).
 * Pure `transform` updates via a ref, not React state, so this never triggers a re-render loop. */
export function CursorGlow() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;

    const el = ref.current;
    if (!el) return;

    let raf = 0;
    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    let visible = false;

    function onMove(e: MouseEvent) {
      x = e.clientX;
      y = e.clientY;
      if (!visible) {
        visible = true;
        if (el) el.style.opacity = "1";
      }
      if (!raf) {
        raf = requestAnimationFrame(() => {
          if (el) el.style.transform = `translate3d(${x - 220}px, ${y - 220}px, 0)`;
          raf = 0;
        });
      }
    }

    function onLeave() {
      visible = false;
      if (el) el.style.opacity = "0";
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseleave", onLeave);
    return () => {
      window.removeEventListener("mousemove", onMove);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 -z-10 h-[440px] w-[440px] rounded-full opacity-0 transition-opacity duration-500"
      style={{
        background:
          "radial-gradient(circle, rgba(124,44,255,0.14) 0%, rgba(22,139,255,0.06) 45%, transparent 70%)",
        willChange: "transform",
      }}
    />
  );
}
