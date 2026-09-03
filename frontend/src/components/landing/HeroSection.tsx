"use client";

import React from "react";
import Link from "next/link";
import { motion, Variants } from "framer-motion";
import { ArrowRight, ShieldCheck, Zap, TrendingUp, Lock } from "lucide-react";
import { HeroParallaxBackground } from "./HeroParallaxBackground";
import { HeroDataFlowVisualizer } from "./HeroDataFlowVisualizer";

export function HeroSection() {
  // Container variants with staggered sequencing
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.08,
      },
    },
  };

  // Eyebrow and general items spring variant
  const itemSpringVariants: Variants = {
    hidden: {
      opacity: 0,
      y: 30,
      filter: "blur(4px)",
    },
    visible: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: {
        type: "spring",
        stiffness: 120,
        damping: 18,
        mass: 0.8,
      },
    },
  };

  // Line 1 word container
  const headlineLine1Container: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.06,
        delayChildren: 0.22,
      },
    },
  };

  // Line 2 word container
  const headlineLine2Container: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.42,
      },
    },
  };

  // Word spring variant with subtle elastic lift
  const wordVariants: Variants = {
    hidden: {
      opacity: 0,
      y: 40,
      filter: "blur(8px)",
    },
    visible: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: {
        type: "spring",
        stiffness: 110,
        damping: 16,
        mass: 0.7,
      },
    },
  };

  // Serif word variant for second line
  const serifWordVariants: Variants = {
    hidden: {
      opacity: 0,
      y: 45,
      scale: 0.94,
      filter: "blur(10px)",
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      filter: "blur(0px)",
      transition: {
        type: "spring",
        stiffness: 90,
        damping: 15,
        mass: 0.9,
      },
    },
  };

  const line1Words = ["Revenue", "is", "already", "there."];
  const line2Words = ["We", "bring", "it", "back."];

  return (
    <section className="relative pt-20 pb-16 lg:pt-28 lg:pb-24 overflow-hidden border-b border-white/[0.07] bg-[#070706]">
      {/* 1. Cinematic Multi-Layered Interactive Parallax Background */}
      <HeroParallaxBackground />

      <div className="max-w-6xl mx-auto px-6 relative z-10 text-center">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center"
        >
          {/* Eyebrow Badge (0.15s) */}
          <motion.div variants={itemSpringVariants}>
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#141412] border border-white/[0.09] text-[11px] font-mono text-[#D79A43] mb-8 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
              <span>AUTONOMOUS REVENUE RECOVERY PLATFORM</span>
            </div>
          </motion.div>

          {/* Headline Line 1 (Staggered Word Springs) */}
          <motion.h1
            variants={headlineLine1Container}
            className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight text-[#F5F0E8] max-w-4xl mx-auto leading-[1.05] flex flex-wrap justify-center gap-x-3.5 sm:gap-x-5"
          >
            {line1Words.map((word, idx) => (
              <motion.span key={idx} variants={wordVariants} className="inline-block">
                {word}
              </motion.span>
            ))}
          </motion.h1>

          {/* Headline Line 2 (Staggered Italic Serif Gold Words) */}
          <motion.div
            variants={headlineLine2Container}
            className="font-serif italic font-normal text-[#D79A43] text-4xl sm:text-6xl md:text-7xl lg:text-8xl tracking-tight leading-[1.1] mt-2 mb-6 flex flex-wrap justify-center gap-x-3.5 sm:gap-x-5"
          >
            {line2Words.map((word, idx) => (
              <motion.span key={idx} variants={serifWordVariants} className="inline-block">
                {word}
              </motion.span>
            ))}
          </motion.div>

          {/* Supporting Description (0.55s) */}
          <motion.p
            variants={itemSpringVariants}
            className="max-w-2xl mx-auto text-base sm:text-lg font-mono text-[#918D84] leading-relaxed mb-10"
          >
            RecoverAI detects failed transactions, diagnoses root causes, and executes bounded recovery workflows
            governed by deterministic policy engine rules.
          </motion.p>

          {/* CTA Action Buttons with Spring Hover (0.70s - 0.80s) */}
          <motion.div
            variants={itemSpringVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 w-full sm:w-auto"
          >
            <motion.a
              href="#simulation"
              whileHover={{ scale: 1.03, y: -2 }}
              whileTap={{ scale: 0.98 }}
              transition={{ type: "spring", stiffness: 350, damping: 20 }}
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-colors shadow-gold flex items-center justify-center gap-2 group cursor-pointer"
            >
              <span>See the Agent Work</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1.5 transition-transform duration-200" />
            </motion.a>

            <motion.div
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              transition={{ type: "spring", stiffness: 350, damping: 20 }}
            >
              <Link
                href="/dashboard"
                className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#141412] text-[#F5F0E8] hover:bg-[#1A1A18] border border-white/[0.10] hover:border-[#D79A43]/40 font-mono text-xs font-medium transition-colors shadow-sm flex items-center justify-center gap-2"
              >
                <span>Open Merchant Dashboard</span>
              </Link>
            </motion.div>
          </motion.div>

          {/* Hero Financial Intelligence Pipeline Flow Visualizer (0.95s) */}
          <motion.div variants={itemSpringVariants} className="w-full">
            <HeroDataFlowVisualizer />
          </motion.div>

          {/* Redesigned KPI Data Console Strip (1.10s) */}
          <motion.div
            variants={itemSpringVariants}
            className="w-full max-w-4xl mx-auto rounded-xl bg-[#11110F]/80 border border-white/[0.07] p-6 grid grid-cols-2 lg:grid-cols-4 gap-6 text-left backdrop-blur-md"
          >
            <div className="border-r border-white/[0.06] pr-4">
              <span className="mono-label text-[#66625B] block mb-1">Target Volume</span>
              <div className="font-serif text-3xl sm:text-4xl font-bold text-[#F5F0E8] tabular-nums">
                ₹2.4Cr+
              </div>
              <span className="text-[10px] font-mono text-[#918D84] mt-0.5 block">Revenue at Risk</span>
            </div>

            <div className="border-r border-white/[0.06] pr-4">
              <span className="mono-label text-[#D79A43] block mb-1">Autonomous Capture</span>
              <div className="font-serif text-3xl sm:text-4xl font-bold text-[#D79A43] tabular-nums">
                39.2%
              </div>
              <span className="text-[10px] font-mono text-[#918D84] mt-0.5 block">Recovery Rate</span>
            </div>

            <div className="border-r border-white/[0.06] pr-4">
              <span className="mono-label text-[#20B89A] block mb-1">Deterministic Rules</span>
              <div className="font-serif text-3xl sm:text-4xl font-bold text-[#20B89A] tabular-nums">
                13 / 13
              </div>
              <span className="text-[10px] font-mono text-[#918D84] mt-0.5 block">Safety Invariant Tests</span>
            </div>

            <div>
              <span className="mono-label text-[#66625B] block mb-1">Ledger Integrity</span>
              <div className="font-serif text-3xl sm:text-4xl font-bold text-[#F5F0E8] tabular-nums">
                SHA-256
              </div>
              <span className="text-[10px] font-mono text-[#918D84] mt-0.5 block">Cryptographically Chained</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
