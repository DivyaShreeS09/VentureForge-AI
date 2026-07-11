import { useEffect, useRef } from "react";

interface Props {
  /** Only the hero zone draws connective lines between nearby particles — everywhere else gets
   * plain drifting points, so the "connected intelligence network" reads as a deliberate zone,
   * not a repeated background texture. */
  connected?: boolean;
  className?: string;
}

type Particle = { x: number; y: number; vx: number; vy: number; r: number; color: string };

const VIOLET = ["#7c2cff", "#a445ff"];
const BLUE = ["#168bff", "#20c7ff"];
const GOLD = "#ff9d1c";

function pickColor(): string {
  const roll = Math.random();
  if (roll < 0.06) return GOLD; // gold is rare — an occasional signal, not a flood
  if (roll < 0.55) return VIOLET[Math.floor(Math.random() * VIOLET.length)];
  return BLUE[Math.floor(Math.random() * BLUE.length)];
}

/**
 * A lightweight, dependency-free canvas particle field. Represents venture "signals" drifting
 * through space — slow, elegant, never a distracting starfield. Respects
 * `prefers-reduced-motion` (renders one static frame, no loop), scales particle count down on
 * narrow/low-power viewports, pauses entirely when the tab is hidden, and never intercepts
 * pointer events so it can never obstruct text or controls.
 */
export function ParticleField({ connected = false, className = "" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isNarrow = window.innerWidth < 640;
    const particleCount = isNarrow ? 18 : connected ? 48 : 30;
    const linkDistance = isNarrow ? 0 : connected ? 120 : 0;

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let particles: Particle[] = [];
    let animationId = 0;
    let mouseX = 0;
    let mouseY = 0;
    let hasMouse = false;

    function seedParticles() {
      particles = Array.from({ length: particleCount }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        r: Math.random() * 1.6 + 0.6,
        color: pickColor(),
      }));
    }

    function resize() {
      const parent = canvas!.parentElement;
      width = parent ? parent.clientWidth : window.innerWidth;
      height = parent ? parent.clientHeight : window.innerHeight;
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      seedParticles();
    }

    function drawFrame() {
      ctx!.clearRect(0, 0, width, height);
      const parallaxX = hasMouse ? (mouseX / width - 0.5) * 6 : 0;
      const parallaxY = hasMouse ? (mouseY / height - 0.5) * 6 : 0;

      if (linkDistance > 0) {
        for (let i = 0; i < particles.length; i++) {
          for (let j = i + 1; j < particles.length; j++) {
            const a = particles[i];
            const b = particles[j];
            const dx = a.x - b.x;
            const dy = a.y - b.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < linkDistance) {
              ctx!.strokeStyle = `rgba(124, 44, 255, ${0.12 * (1 - dist / linkDistance)})`;
              ctx!.lineWidth = 1;
              ctx!.beginPath();
              ctx!.moveTo(a.x + parallaxX, a.y + parallaxY);
              ctx!.lineTo(b.x + parallaxX, b.y + parallaxY);
              ctx!.stroke();
            }
          }
        }
      }

      for (const p of particles) {
        ctx!.beginPath();
        ctx!.fillStyle = p.color;
        ctx!.globalAlpha = 0.75;
        ctx!.arc(p.x + parallaxX, p.y + parallaxY, p.r, 0, Math.PI * 2);
        ctx!.fill();
      }
      ctx!.globalAlpha = 1;
    }

    function step() {
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;
      }
      drawFrame();
      animationId = window.requestAnimationFrame(step);
    }

    function handleMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
      hasMouse = true;
    }

    function handleVisibility() {
      if (document.hidden) {
        window.cancelAnimationFrame(animationId);
      } else if (!reducedMotion) {
        animationId = window.requestAnimationFrame(step);
      }
    }

    resize();
    drawFrame();

    if (!reducedMotion) {
      animationId = window.requestAnimationFrame(step);
      if (!isNarrow) window.addEventListener("mousemove", handleMouseMove);
    }
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [connected]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 ${className}`}
    />
  );
}
