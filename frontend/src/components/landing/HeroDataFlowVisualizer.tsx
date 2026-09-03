"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Brain,
  ShieldCheck,
  Send,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

export function HeroDataFlowVisualizer() {
  const [activeNode, setActiveNode] = useState(0);
  const [recoveredCounter, setRecoveredCounter] = useState(84500);

  // Cycle through the pipeline nodes continuously
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveNode((prev) => {
        const next = (prev + 1) % 5;
        if (next === 4) {
          // Increment simulated recovered revenue upon reaching final node
          setRecoveredCounter((c) => c + Math.floor(Math.random() * 4500 + 3500));
        }
        return next;
      });
    }, 1800);

    return () => clearInterval(interval);
  }, []);

  const pipelineSteps = [
    {
      id: "failed",
      label: "Failed Event",
      sub: "Timeout / Drop-off",
      icon: AlertTriangle,
      color: "text-[#E56B6F]",
      border: "border-[#E56B6F]/40",
      bg: "bg-[#E56B6F]/10",
      glow: "shadow-[0_0_15px_rgba(229,107,111,0.25)]",
    },
    {
      id: "diagnosis",
      label: "AI Diagnosis",
      sub: "Root Cause 94%",
      icon: Brain,
      color: "text-[#D79A43]",
      border: "border-[#D79A43]/40",
      bg: "bg-[#D79A43]/10",
      glow: "shadow-[0_0_15px_rgba(215,154,67,0.25)]",
    },
    {
      id: "policy",
      label: "Policy Engine",
      sub: "6 Invariants Passed",
      icon: ShieldCheck,
      color: "text-[#D79A43]",
      border: "border-[#D79A43]/40",
      bg: "bg-[#D79A43]/10",
      glow: "shadow-[0_0_15px_rgba(215,154,67,0.25)]",
    },
    {
      id: "recovery",
      label: "Recovery Link",
      sub: "Dispatched (Idempotent)",
      icon: Send,
      color: "text-[#D79A43]",
      border: "border-[#D79A43]/40",
      bg: "bg-[#D79A43]/10",
      glow: "shadow-[0_0_15px_rgba(215,154,67,0.25)]",
    },
    {
      id: "recovered",
      label: "Revenue Captured",
      sub: "Settled & Verified",
      icon: CheckCircle2,
      color: "text-[#20B89A]",
      border: "border-[#20B89A]/50",
      bg: "bg-[#20B89A]/15",
      glow: "shadow-[0_0_20px_rgba(32,184,154,0.35)]",
    },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto my-10 p-5 sm:p-6 rounded-2xl bg-[#11110F]/90 border border-white/[0.08] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.6)] relative overflow-hidden">
      {/* Top Header Strip */}
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-white/[0.06] text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#20B89A] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#20B89A]" />
          </span>
          <span className="text-[#F5F0E8] font-semibold tracking-wide">
            Autonomous Pipeline Stream
          </span>
          <span className="text-white/20 hidden sm:inline">•</span>
          <span className="text-[#918D84] hidden sm:inline">Payment Gateway Telemetry</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-[#171614] px-2.5 py-1 rounded-lg border border-white/[0.07]">
            <span className="text-[#918D84] text-[11px]">Recovered:</span>
            <span className="text-[#20B89A] font-bold tabular-nums text-xs">
              ₹{recoveredCounter.toLocaleString("en-IN")}
            </span>
          </div>
        </div>
      </div>

      {/* Horizontal Interactive Pipeline Visualizer */}
      <div className="relative grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-2 items-center">
        {/* Animated Connecting Line on Desktop */}
        <div className="hidden sm:block absolute top-[28px] left-[10%] right-[10%] h-[2px] bg-white/[0.06] -z-0">
          <motion.div
            className="h-full bg-gradient-to-r from-[#E56B6F] via-[#D79A43] to-[#20B89A]"
            animate={{
              width: `${(activeNode / 4) * 100}%`,
            }}
            transition={{ type: "spring", stiffness: 90, damping: 20 }}
          />
        </div>

        {pipelineSteps.map((step, idx) => {
          const Icon = step.icon;
          const isCurrent = activeNode === idx;
          const isPassed = activeNode > idx;

          return (
            <div
              key={step.id}
              className={`relative z-10 flex flex-col items-center p-3 sm:p-3.5 rounded-xl transition-all duration-300 ${
                isCurrent
                  ? `${step.bg} ${step.border} ${step.glow} scale-[1.03]`
                  : isPassed
                  ? "bg-[#171614]/80 border border-white/[0.09]"
                  : "bg-[#141412]/40 border border-white/[0.04] opacity-60"
              }`}
            >
              {/* Node Icon */}
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center mb-2 transition-all ${
                  isCurrent
                    ? `${step.bg} ${step.color} border ${step.border}`
                    : isPassed
                    ? "bg-white/[0.05] text-[#F5F0E8]"
                    : "bg-white/[0.02] text-[#918D84]"
                }`}
              >
                <Icon className="w-4 h-4" />
              </div>

              {/* Node Text */}
              <span className="text-[11px] font-mono font-bold text-[#F5F0E8] text-center leading-tight">
                {step.label}
              </span>
              <span className="text-[9px] font-mono text-[#918D84] text-center mt-0.5 truncate max-w-full">
                {step.sub}
              </span>

              {/* Active Pulse Dot */}
              {isCurrent && (
                <motion.div
                  layoutId="pulseDot"
                  className={`w-1.5 h-1.5 rounded-full mt-2 ${
                    idx === 4 ? "bg-[#20B89A]" : idx === 0 ? "bg-[#E56B6F]" : "bg-[#D79A43]"
                  }`}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Real-time Telemetry Caption */}
      <div className="mt-5 pt-3 border-t border-white/[0.05] flex flex-col sm:flex-row items-center justify-between text-[11px] font-mono text-[#918D84] gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[#D79A43] font-bold">STATE {activeNode + 1}/5:</span>
          <span>
            {activeNode === 0 && "Timeout captured on payment gateway (₹12,500)"}
            {activeNode === 1 && "AI Diagnostician: Temporary bank network congestion"}
            {activeNode === 2 && "Deterministic Policy: 0 prior retries, rule check passed"}
            {activeNode === 3 && "Executor: Dynamic smart payment link generated with SHA-256 lock"}
            {activeNode === 4 && "Verifier: Payment confirmed, ₹12,500 reconciled into ledger"}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[#20B89A] font-semibold">
          <TrendingUp className="w-3.5 h-3.5" />
          <span>99.98% Gateway Uptime</span>
        </div>
      </div>
    </div>
  );
}
