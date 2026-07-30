import { useEffect, useRef } from "react";

type Star = {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  hue: "gold" | "white";
  twinkleSpeed: number;
  twinklePhase: number;
  baseAlpha: number;
};

type ShootingStar = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
};

const STAR_COUNT_DESKTOP = 130;
const STAR_COUNT_NARROW = 60;
const GOLD_RGB = "255, 191, 92";
const WHITE_RGB = "255, 250, 240";

interface Props {
  /** "rich" (default) — the Threshold hero's full count. "quiet" — roughly half, used on every
   * other screen so the atmosphere reads as alive without ever competing with dense data content
   * (Rule of Subtraction). */
  density?: "rich" | "quiet";
}

/** The app's shared atmosphere layer, drawn over both the Threshold hero and (at reduced density)
 * every other screen's cosmic backdrop: real four-point star sprites (not flat dots, not a
 * connected particle network) in exactly two hues — warm gold and warm white, matching the
 * artwork's own palette — drifting extremely slowly, twinkling via a per-star sine phase, plus a
 * rare shooting star every 6-14s. A single static frame is drawn under `prefers-reduced-motion`
 * and shooting stars never spawn in that mode. Canvas-based: hundreds of DOM nodes animating
 * individually would be real, measurable overhead for a purely decorative layer. */
export function StarField({ density = "rich" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isNarrow = window.innerWidth < 640;
    const densityFactor = density === "quiet" ? 0.5 : 1;
    const starCount = Math.round((isNarrow ? STAR_COUNT_NARROW : STAR_COUNT_DESKTOP) * densityFactor);

    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let stars: Star[] = [];
    let shootingStars: ShootingStar[] = [];
    let animationId = 0;
    let nextShootAt = 0;
    let elapsed = 0;

    function drawStar(cx: number, cy: number, outerR: number, innerR: number) {
      ctx!.beginPath();
      for (let i = 0; i < 8; i++) {
        const angle = (Math.PI / 4) * i - Math.PI / 2;
        const r = i % 2 === 0 ? outerR : innerR;
        const px = cx + Math.cos(angle) * r;
        const py = cy + Math.sin(angle) * r;
        if (i === 0) ctx!.moveTo(px, py);
        else ctx!.lineTo(px, py);
      }
      ctx!.closePath();
      ctx!.fill();
    }

    function seed() {
      stars = Array.from({ length: starCount }, () => {
        // Gold stars run brighter and a touch larger than white ones — "random depth" (a star
        // that reads as nearer is both bigger and more luminous) plus enough baseline visibility
        // that they never wash out against the cosmic backdrop the way the original tuning did.
        const gold = Math.random() < 0.35;
        const depth = Math.random(); // 0 = distant/small/dim, 1 = near/large/bright
        return {
          x: Math.random() * width,
          y: Math.random() * height,
          r: (gold ? 0.9 + depth * 1.6 : 0.5 + depth * 1.1),
          vx: (Math.random() - 0.5) * 0.015,
          vy: (Math.random() - 0.5) * 0.01 + 0.004,
          hue: gold ? "gold" : "white",
          twinkleSpeed: Math.random() * 0.8 + 0.3,
          twinklePhase: Math.random() * Math.PI * 2,
          baseAlpha: gold ? 0.55 + depth * 0.4 : 0.32 + depth * 0.38,
        };
      });
      nextShootAt = 6 + Math.random() * 8;
      elapsed = 0;
    }

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    }

    function spawnShootingStar() {
      const startX = Math.random() * width * 0.7;
      const angle = (Math.PI / 5) + Math.random() * 0.3; // shallow downward-right streak
      const speed = 9 + Math.random() * 5;
      shootingStars.push({
        x: startX,
        y: Math.random() * height * 0.35,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 0,
        maxLife: 22 + Math.random() * 10,
      });
    }

    function drawFrame(dt: number) {
      ctx!.clearRect(0, 0, width, height);

      for (const s of stars) {
        const twinkle = 0.5 + 0.5 * Math.sin(s.twinklePhase);
        const alpha = s.baseAlpha * (0.55 + twinkle * 0.45);
        const rgb = s.hue === "gold" ? GOLD_RGB : WHITE_RGB;
        ctx!.fillStyle = `rgba(${rgb}, ${alpha})`;
        // A soft glow behind gold stars only — the warm accent should clearly read as gold even
        // at a glance, not just a slightly-tinted white dot.
        if (s.hue === "gold") {
          ctx!.shadowColor = `rgba(${GOLD_RGB}, ${Math.min(alpha, 0.8)})`;
          ctx!.shadowBlur = 4 + s.r * 2;
        } else {
          ctx!.shadowBlur = 0;
        }
        drawStar(s.x, s.y, s.r * 2.1, s.r * 0.8);
      }
      ctx!.shadowBlur = 0;

      for (const shoot of shootingStars) {
        const t = shoot.life / shoot.maxLife;
        const fade = t < 0.15 ? t / 0.15 : 1 - (t - 0.15) / 0.85;
        const tailX = shoot.x - shoot.vx * 3.2;
        const tailY = shoot.y - shoot.vy * 3.2;
        const gradient = ctx!.createLinearGradient(shoot.x, shoot.y, tailX, tailY);
        gradient.addColorStop(0, `rgba(${GOLD_RGB}, ${0.85 * fade})`);
        gradient.addColorStop(1, `rgba(${GOLD_RGB}, 0)`);
        ctx!.strokeStyle = gradient;
        ctx!.lineWidth = 1.6;
        ctx!.lineCap = "round";
        ctx!.beginPath();
        ctx!.moveTo(shoot.x, shoot.y);
        ctx!.lineTo(tailX, tailY);
        ctx!.stroke();
      }

      if (!reducedMotion) {
        for (const s of stars) {
          s.x += s.vx;
          s.y += s.vy;
          s.twinklePhase += s.twinkleSpeed * dt;
          if (s.x < -4) s.x = width + 4;
          if (s.x > width + 4) s.x = -4;
          if (s.y > height + 4) s.y = -4;
        }
        shootingStars = shootingStars.filter((sh) => sh.life < sh.maxLife);
        for (const sh of shootingStars) {
          sh.x += sh.vx;
          sh.y += sh.vy;
          sh.life += 1;
        }
        elapsed += dt;
        if (elapsed >= nextShootAt) {
          spawnShootingStar();
          nextShootAt = elapsed + 6 + Math.random() * 8;
        }
      }
    }

    let lastTime = performance.now();
    function step(now: number) {
      const dt = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;
      drawFrame(dt);
      animationId = window.requestAnimationFrame(step);
    }

    function handleVisibility() {
      if (document.hidden) {
        window.cancelAnimationFrame(animationId);
      } else if (!reducedMotion) {
        lastTime = performance.now();
        animationId = window.requestAnimationFrame(step);
      }
    }

    resize();
    drawFrame(0);

    if (!reducedMotion) {
      animationId = window.requestAnimationFrame(step);
    }
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [density]);

  return <canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none absolute inset-0" />;
}
