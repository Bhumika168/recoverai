"use client";

import React, { useEffect, useRef } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";

export function HeroParallaxBackground() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Mouse motion values normalized to [-0.5, 0.5]
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Physics spring for silky smooth parallax damping
  const springConfig = { damping: 30, stiffness: 100, mass: 0.5 };
  const smoothMouseX = useSpring(mouseX, springConfig);
  const smoothMouseY = useSpring(mouseY, springConfig);

  // Multi-layered subtle offsets
  const bgX = useTransform(smoothMouseX, [-0.5, 0.5], [-4, 4]);
  const bgY = useTransform(smoothMouseY, [-0.5, 0.5], [-4, 4]);

  const midX = useTransform(smoothMouseX, [-0.5, 0.5], [-8, 8]);
  const midY = useTransform(smoothMouseY, [-0.5, 0.5], [-8, 8]);

  const fgX = useTransform(smoothMouseX, [-0.5, 0.5], [-12, 12]);
  const fgY = useTransform(smoothMouseY, [-0.5, 0.5], [-12, 12]);

  const glowX = useTransform(smoothMouseX, [-0.5, 0.5], [-15, 15]);
  const glowY = useTransform(smoothMouseY, [-0.5, 0.5], [-15, 15]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      mouseX.set(e.clientX / innerWidth - 0.5);
      mouseY.set(e.clientY / innerHeight - 0.5);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0"
    >
      {/* 1. Underlying Deep Obsidian Base */}
      <div className="absolute inset-0 bg-[#070706]" />

      {/* 2. Interactive Subtle Ambient Glow */}
      <motion.div
        style={{ x: glowX, y: glowY }}
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[380px] bg-[#D79A43]/[0.045] blur-[140px] rounded-full"
      />

      {/* 3. Deep Background Layer: Geometric Matrix & Fine Grid */}
      <motion.div
        style={{ x: bgX, y: bgY }}
        className="absolute inset-0 opacity-[0.035]"
        style-bg="grid"
      >
        <div
          className="w-full h-full"
          style={{
            backgroundImage:
              "linear-gradient(rgba(245, 240, 232, 0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(245, 240, 232, 0.18) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
      </motion.div>

      {/* 4. Midground Layer: Vector Data Curves & Network Nodes */}
      <motion.div style={{ x: midX, y: midY }} className="absolute inset-0">
        <svg
          className="w-full h-full opacity-60"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="none"
          viewBox="0 0 1440 900"
        >
          <defs>
            <linearGradient id="goldGrad1" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#D79A43" stopOpacity="0.02" />
              <stop offset="50%" stopColor="#D79A43" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#20B89A" stopOpacity="0.25" />
            </linearGradient>
            <linearGradient id="goldGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#E56B6F" stopOpacity="0.15" />
              <stop offset="60%" stopColor="#D79A43" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#20B89A" stopOpacity="0.05" />
            </linearGradient>
          </defs>

          {/* Left-to-Right Converging Financial Trajectories */}
          <path
            d="M -50,750 C 300,850 600,720 1480,550"
            fill="none"
            stroke="url(#goldGrad1)"
            strokeWidth="1.5"
            strokeDasharray="4 6"
          />
          <path
            d="M -30,620 C 400,680 900,820 1480,680"
            fill="none"
            stroke="url(#goldGrad2)"
            strokeWidth="1"
            strokeDasharray="2 8"
          />
          <path
            d="M 50,420 C 350,550 1100,580 1480,420"
            fill="none"
            stroke="rgba(215, 154, 67, 0.08)"
            strokeWidth="1"
          />

          {/* Left Data Nodes */}
          <circle cx="120" cy="520" r="3.5" fill="#D79A43" fillOpacity="0.4" />
          <circle cx="240" cy="650" r="2.5" fill="#E56B6F" fillOpacity="0.5" />
          <line x1="120" y1="520" x2="240" y2="650" stroke="rgba(215,154,67,0.12)" strokeWidth="1" />

          {/* Right Recovery Nodes */}
          <circle cx="1300" cy="480" r="3" fill="#20B89A" fillOpacity="0.6" />
          <circle cx="1180" cy="620" r="4" fill="#20B89A" fillOpacity="0.5" />
          <line x1="1180" y1="620" x2="1300" y2="480" stroke="rgba(32,184,154,0.15)" strokeWidth="1" />
        </svg>
      </motion.div>

      {/* 5. Foreground Layer: Micro Floating Luminous Particles */}
      <motion.div style={{ x: fgX, y: fgY }} className="absolute inset-0">
        <div className="absolute top-[20%] left-[12%] w-1.5 h-1.5 rounded-full bg-[#D79A43]/40 blur-[0.5px]" />
        <div className="absolute top-[65%] left-[8%] w-2 h-2 rounded-full bg-[#D79A43]/30 blur-[0.5px]" />
        <div className="absolute top-[75%] left-[22%] w-1 h-1 rounded-full bg-[#F5F0E8]/40" />
        <div className="absolute top-[30%] right-[14%] w-1.5 h-1.5 rounded-full bg-[#20B89A]/40 blur-[0.5px]" />
        <div className="absolute top-[60%] right-[10%] w-2 h-2 rounded-full bg-[#20B89A]/50 blur-[0.5px]" />
        <div className="absolute top-[80%] right-[24%] w-1 h-1 rounded-full bg-[#D79A43]/40" />
      </motion.div>

      {/* 6. Masking Vignette: Heavy dark center to preserve 100% typography legibility */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 65% 60% at 50% 45%, #070706 0%, rgba(7, 7, 6, 0.95) 45%, rgba(7, 7, 6, 0.4) 85%, rgba(7, 7, 6, 0.8) 100%)",
        }}
      />
    </div>
  );
}
