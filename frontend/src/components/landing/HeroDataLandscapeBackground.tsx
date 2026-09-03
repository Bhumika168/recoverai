"use client";

import React, { useEffect, useRef } from "react";

export function HeroDataLandscapeBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };

    window.addEventListener("resize", handleResize);

    // Respect reduced motion preferences
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Subtle Particle System
    interface Particle {
      x: number;
      y: number;
      radius: number;
      vx: number;
      vy: number;
      alpha: number;
      maxAlpha: number;
      fadeSpeed: number;
      color: string;
    }

    const particleCount = 28;
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      // Concentrate particles towards edges & bottom
      const isLeft = Math.random() < 0.5;
      const x = isLeft
        ? Math.random() * (width * 0.35)
        : width * 0.65 + Math.random() * (width * 0.35);
      const y = Math.random() * height;

      particles.push({
        x,
        y,
        radius: Math.random() * 1.5 + 0.5,
        vx: (Math.random() * 0.15 + 0.05) * (Math.random() < 0.8 ? 1 : -0.5),
        vy: (Math.random() - 0.5) * 0.12,
        alpha: Math.random() * 0.25 + 0.05,
        maxAlpha: Math.random() * 0.35 + 0.15,
        fadeSpeed: Math.random() * 0.003 + 0.001,
        color: Math.random() < 0.75 ? "#D9A441" : "#F5F1E8",
      });
    }

    // Fixed Subtle Constellation Nodes on bottom/sides
    const nodes = [
      // Left cluster (Transactions originating / failing)
      { xRatio: 0.08, yRatio: 0.35, r: 2.5, pulse: 0 },
      { xRatio: 0.14, yRatio: 0.55, r: 2, pulse: 1.2 },
      { xRatio: 0.22, yRatio: 0.75, r: 3, pulse: 2.4 },
      { xRatio: 0.18, yRatio: 0.88, r: 2, pulse: 0.6 },
      { xRatio: 0.06, yRatio: 0.78, r: 2, pulse: 1.8 },

      // Right cluster (Intelligence & Recovery capture)
      { xRatio: 0.78, yRatio: 0.72, r: 3, pulse: 0.8 },
      { xRatio: 0.86, yRatio: 0.52, r: 2.5, pulse: 2.1 },
      { xRatio: 0.92, yRatio: 0.38, r: 2, pulse: 1.5 },
      { xRatio: 0.82, yRatio: 0.85, r: 2.5, pulse: 3.0 },
      { xRatio: 0.94, yRatio: 0.75, r: 2, pulse: 0.3 },
    ];

    let time = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      time += 0.008;

      // 1. Draw Subtle Background Vector Trajectories (Flowing Left -> Right)
      ctx.save();

      // Flow Path 1: Lower sweeping trajectory
      ctx.beginPath();
      ctx.moveTo(width * 0.02, height * 0.82);
      ctx.bezierCurveTo(
        width * 0.25,
        height * 0.92 + Math.sin(time * 0.5) * 8,
        width * 0.75,
        height * 0.94 + Math.cos(time * 0.4) * 8,
        width * 0.98,
        height * 0.72
      );
      ctx.strokeStyle = "rgba(217, 164, 65, 0.09)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 6]);
      ctx.lineDashOffset = -time * 12;
      ctx.stroke();

      // Flow Path 2: Secondary fine trajectory
      ctx.beginPath();
      ctx.moveTo(width * 0.05, height * 0.7);
      ctx.bezierCurveTo(
        width * 0.3,
        height * 0.78,
        width * 0.7,
        height * 0.82,
        width * 0.95,
        height * 0.58
      );
      ctx.strokeStyle = "rgba(138, 100, 31, 0.08)";
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 8]);
      ctx.lineDashOffset = -time * 8;
      ctx.stroke();

      // Flow Path 3: Subtle upper baseline curve
      ctx.beginPath();
      ctx.moveTo(width * 0.04, height * 0.45);
      ctx.bezierCurveTo(
        width * 0.2,
        height * 0.6,
        width * 0.8,
        height * 0.65,
        width * 0.96,
        height * 0.42
      );
      ctx.strokeStyle = "rgba(217, 164, 65, 0.05)";
      ctx.lineWidth = 0.8;
      ctx.setLineDash([]);
      ctx.stroke();

      ctx.restore();

      // 2. Draw Connected Node Geometry & Pulses
      ctx.save();
      // Left cluster connections
      ctx.strokeStyle = "rgba(217, 164, 65, 0.07)";
      ctx.lineWidth = 0.75;
      for (let i = 0; i < 4; i++) {
        const n1 = nodes[i];
        const n2 = nodes[i + 1];
        ctx.beginPath();
        ctx.moveTo(n1.xRatio * width, n1.yRatio * height);
        ctx.lineTo(n2.xRatio * width, n2.yRatio * height);
        ctx.stroke();
      }

      // Right cluster connections
      for (let i = 5; i < 9; i++) {
        const n1 = nodes[i];
        const n2 = nodes[i + 1];
        ctx.beginPath();
        ctx.moveTo(n1.xRatio * width, n1.yRatio * height);
        ctx.lineTo(n2.xRatio * width, n2.yRatio * height);
        ctx.stroke();
      }

      // Render Nodes with Soft Pulses
      nodes.forEach((n) => {
        const nx = n.xRatio * width;
        const ny = n.yRatio * height;
        const pulseFactor = prefersReducedMotion ? 1 : (Math.sin(time * 1.5 + n.pulse) + 1) / 2;

        // Outer subtle aura
        ctx.beginPath();
        ctx.arc(nx, ny, n.r + pulseFactor * 4, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(217, 164, 65, 0.04)";
        ctx.fill();

        // Node center core
        ctx.beginPath();
        ctx.arc(nx, ny, n.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(217, 164, 65, 0.35)";
        ctx.fill();
      });
      ctx.restore();

      // 3. Render Floating Microscopic Gold / Ivory Dust Particles
      ctx.save();
      particles.forEach((p) => {
        if (!prefersReducedMotion) {
          p.x += p.vx;
          p.y += p.vy;

          p.alpha += p.fadeSpeed;
          if (p.alpha > p.maxAlpha || p.alpha < 0.05) {
            p.fadeSpeed = -p.fadeSpeed;
          }

          // Boundary wraps
          if (p.x > width) p.x = 0;
          if (p.x < 0) p.x = width;
          if (p.y > height) p.y = 0;
          if (p.y < 0) p.y = height;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle =
          p.color === "#D9A441"
            ? `rgba(217, 164, 65, ${p.alpha * 0.6})`
            : `rgba(245, 241, 232, ${p.alpha * 0.4})`;
        ctx.fill();
      });
      ctx.restore();

      if (!prefersReducedMotion) {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0">
      {/* 1. Underlying Deep Obsidian Tone */}
      <div className="absolute inset-0 bg-[#080807]" />

      {/* 2. Generated 16:9 Cinematic Financial Data Landscape */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-40 mix-blend-screen"
        style={{
          backgroundImage: "url('/images/recoverai_hero_bg.jpg')",
        }}
      />

      {/* 3. Subtle Interactive Canvas Particle & Pulse Layer */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full opacity-60"
      />

      {/* 4. Ambient Peripheral Glows */}
      <div className="absolute -bottom-10 -left-10 w-[450px] h-[350px] bg-[#D9A441]/[0.04] blur-[120px] rounded-full" />
      <div className="absolute -bottom-10 -right-10 w-[450px] h-[350px] bg-[#D9A441]/[0.04] blur-[120px] rounded-full" />

      {/* 5. Masking Vignette: Heavy dark center ensuring 100% typography legibility */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 65% 55% at 50% 45%, #080807 0%, rgba(8, 8, 7, 0.92) 45%, rgba(8, 8, 7, 0.3) 85%, rgba(8, 8, 7, 0.7) 100%)",
        }}
      />

      {/* 6. Fine Geometric Grid Texture */}
      <div
        className="absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(245, 241, 232, 0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(245, 241, 232, 0.15) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
    </div>
  );
}
