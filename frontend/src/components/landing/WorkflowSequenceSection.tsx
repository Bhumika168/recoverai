"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Radar,
  Brain,
  Cpu,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Lock,
  ArrowRight,
  ChevronRight,
  TrendingUp,
  Activity,
} from "lucide-react";

interface PipelineStage {
  id: string;
  stepNumber: string;
  name: string;
  role: string;
  module: string;
  summary: string;
  details: string;
  invariant: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
  badgeBg: string;
}

const pipelineStages: PipelineStage[] = [
  {
    id: "failure",
    stepNumber: "01",
    name: "PAYMENT FAILURE",
    role: "Ingestion & Capture",
    module: "Payment Webhook Stream",
    summary: "Payment provider reports a failed transaction or checkout drop-off event.",
    details:
      "Captures standard payment webhook payloads (`payment.failed`, `order.paid.failed`), extracts error codes (e.g. `BAD_REQUEST_ERROR`, `GATEWAY_ERROR`), and initializes raw transaction context.",
    invariant: "Idempotent event hash validated",
    icon: AlertTriangle,
    accentColor: "#E56B6F",
    badgeBg: "bg-[#E56B6F]/10 border-[#E56B6F]/30 text-[#E56B6F]",
  },
  {
    id: "detector",
    stepNumber: "02",
    name: "DETECTOR",
    role: "State Evaluation",
    module: "backend/app/agents/detector.py",
    summary: "Identifies transaction state and determines if recovery analysis is warranted.",
    details:
      "Filters non-recoverable mock states, deduplicates existing in-flight cases, and initiates an isolated recovery execution context with a unique Case ID.",
    invariant: "Duplicate case suppression active",
    icon: Radar,
    accentColor: "#D79A43",
    badgeBg: "bg-[#D79A43]/10 border-[#D79A43]/30 text-[#D79A43]",
  },
  {
    id: "diagnostician",
    stepNumber: "03",
    name: "AI DIAGNOSTICIAN",
    role: "Root Cause Classification",
    module: "backend/app/agents/diagnostician.py",
    summary: "Analyzes failure reason and classifies into transient, recoverable, or hard-decline.",
    details:
      "Performs LLM-assisted diagnostic reasoning over gateway error codes, card network decline signals, and historical merchant recovery patterns. Computes a quantitative Recovery Confidence Score (0–100%).",
    invariant: "Hard declines permanently blocked",
    icon: Brain,
    accentColor: "#D79A43",
    badgeBg: "bg-[#D79A43]/10 border-[#D79A43]/30 text-[#D79A43]",
  },
  {
    id: "decision",
    stepNumber: "04",
    name: "DECISION ENGINE",
    role: "Strategy Formulation",
    module: "backend/app/agents/decision_engine.py",
    summary: "Selects the optimal, safest recovery strategy based on diagnosis and confidence.",
    details:
      "Evaluates multi-channel alternatives (`SMART_PAYMENT_LINK`, `DELAYED_RETRY`, `WHATSAPP_LINK`, `HUMAN_ESCALATION`). Formulates parameter payload with precise cooldown schedules and discount bounds.",
    invariant: "Bounded action catalog enforcement",
    icon: Cpu,
    accentColor: "#D79A43",
    badgeBg: "bg-[#D79A43]/10 border-[#D79A43]/30 text-[#D79A43]",
  },
  {
    id: "policy",
    stepNumber: "05",
    name: "POLICY ENGINE",
    role: "Deterministic Safety Gate",
    module: "backend/app/agents/policy_engine.py",
    summary: "Applies non-negotiable deterministic safety rules before any action can execute.",
    details:
      "Pure Python deterministic rule evaluation with zero LLM hallucinations. Verifies max retry limits (≤3), 4-hour customer cooldown, high-value approval gates (≥₹25,000), and customer opt-out suppression.",
    invariant: "6/6 Non-negotiable invariants verified",
    icon: ShieldCheck,
    accentColor: "#D79A43",
    badgeBg: "bg-[#D79A43]/10 border-[#D79A43]/30 text-[#D79A43]",
  },
  {
    id: "executor",
    stepNumber: "06",
    name: "SAFE EXECUTOR",
    role: "Idempotent Execution",
    module: "backend/app/agents/executor.py",
    summary: "Executes only approved and cryptographically verified recovery operations.",
    details:
      "Dispatches action via Connected Provider API (e.g. creating signed Payment Links or scheduled retry intents). Enforces mutual exclusion locks to prevent double-charging or dual-dispatching.",
    invariant: "Strict 1-time idempotency lock",
    icon: Zap,
    accentColor: "#20B89A",
    badgeBg: "bg-[#20B89A]/10 border-[#20B89A]/30 text-[#20B89A]",
  },
  {
    id: "verifier",
    stepNumber: "07",
    name: "VERIFIER",
    role: "Reconciliation & Ledger",
    module: "backend/app/agents/verifier.py",
    summary: "Confirms transaction settlement and writes tamper-evident SHA-256 audit entry.",
    details:
      "Polls or listens to webhook confirmation (`payment.captured`), reconciles order balance, computes recovered revenue delta, and hashes immutable block into the chained ledger.",
    invariant: "SHA-256 Chained Hash written",
    icon: CheckCircle2,
    accentColor: "#20B89A",
    badgeBg: "bg-[#20B89A]/10 border-[#20B89A]/30 text-[#20B89A]",
  },
];

export function WorkflowSequenceSection() {
  const [selectedStageIndex, setSelectedStageIndex] = useState<number>(2); // Default AI Diagnostician
  const [activeParticleStage, setActiveParticleStage] = useState<number>(0);
  const [isHoveringPipeline, setIsHoveringPipeline] = useState<boolean>(false);

  // Travelling particle loop through the 7 stages
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveParticleStage((prev) => (prev + 1) % 7);
    }, 1900);

    return () => clearInterval(interval);
  }, []);

  const selectedStage = pipelineStages[selectedStageIndex];

  return (
    <section className="py-24 sm:py-32 border-b border-white/[0.07] bg-[#070706] relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-1/2 left-0 w-[500px] h-[500px] bg-[#D79A43]/[0.025] blur-[150px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-[#20B89A]/[0.025] blur-[150px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        {/* Asymmetric Section Header & Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          {/* Left Column (38%): Editorial Context & Live Mini Console */}
          <div className="lg:col-span-5 flex flex-col">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-6 w-fit">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
              <span>AUTONOMOUS RECOVERY ARCHITECTURE</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F0E8] leading-[1.08] mb-4">
              <span>The agent doesn&apos;t just detect failure.</span>
              <span className="font-serif italic font-normal text-[#D79A43] block mt-1.5">
                It decides what happens next.
              </span>
            </h2>

            <p className="text-sm sm:text-base font-mono text-[#918D84] leading-relaxed mb-8">
              RecoverAI detects the failure, understands its root cause, evaluates strict policy constraints, and
              executes only the bounded recovery actions it is deterministically permitted to take.
            </p>

            {/* Live Miniature Agent Console */}
            <div className="rounded-2xl bg-[#11110F] border border-white/[0.08] p-5 font-mono shadow-[0_4px_24px_rgba(0,0,0,0.5)]">
              <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-white/[0.06] text-xs">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#20B89A] opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#20B89A]" />
                  </span>
                  <span className="text-[#F5F0E8] font-semibold text-xs tracking-wider">
                    RECOVERAI AGENT TELEMETRY
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30 font-bold">
                  ● ANALYZING
                </span>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[#66625B]">Active Transaction:</span>
                  <span className="text-[#F5F0E8] font-bold">txn_live_84291</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#66625B]">Failure Code:</span>
                  <span className="text-[#E56B6F] font-bold">BANK_TIMEOUT</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#66625B]">AI Diagnosis:</span>
                  <span className="text-[#D79A43] font-bold">TRANSIENT_FAILURE</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#66625B]">Recovery Confidence:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-white/[0.08] overflow-hidden">
                      <div className="h-full bg-[#D79A43] w-[87%]" />
                    </div>
                    <span className="text-[#F5F0E8] font-bold">87%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#66625B]">Policy Guard:</span>
                  <span className="text-[#20B89A] font-bold">RETRY_ALLOWED (0/3)</span>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-white/[0.05]">
                  <span className="text-[#66625B]">Next Executed Action:</span>
                  <span className="text-[#20B89A] font-bold bg-[#20B89A]/10 px-2 py-0.5 rounded border border-[#20B89A]/30">
                    DELAYED_RETRY (+12m)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column (62%): 7-Stage Interactive Pipeline & Node Inspector */}
          <div className="lg:col-span-7 flex flex-col">
            {/* Pipeline Container */}
            <div
              className="p-5 sm:p-7 rounded-2xl bg-[#11110F]/90 border border-white/[0.08] backdrop-blur-md shadow-2xl relative"
              onMouseEnter={() => setIsHoveringPipeline(true)}
              onMouseLeave={() => setIsHoveringPipeline(false)}
            >
              {/* Header */}
              <div className="flex items-center justify-between pb-4 mb-5 border-b border-white/[0.06]">
                <span className="text-xs font-mono font-semibold text-[#918D84] tracking-wider uppercase">
                  Continuous 7-Stage Pipeline
                </span>
                <span className="text-[11px] font-mono text-[#D79A43]">Click node to inspect</span>
              </div>

              {/* 7 Interactive Nodes */}
              <div className="space-y-3 relative">
                {pipelineStages.map((stage, idx) => {
                  const Icon = stage.icon;
                  const isSelected = selectedStageIndex === idx;
                  const isParticleActive = activeParticleStage === idx;

                  return (
                    <motion.button
                      key={stage.id}
                      onClick={() => setSelectedStageIndex(idx)}
                      whileHover={{ scale: 1.015, x: 4 }}
                      whileTap={{ scale: 0.99 }}
                      transition={{ type: "spring", stiffness: 350, damping: 25 }}
                      className={`w-full p-3.5 sm:p-4 rounded-xl border text-left transition-all flex items-center justify-between cursor-pointer relative overflow-hidden ${
                        isSelected
                          ? "bg-[#171614] border-[#D79A43]/50 shadow-[0_0_20px_rgba(215,154,67,0.15)]"
                          : "bg-[#141412]/60 border-white/[0.06] hover:border-white/[0.15] hover:bg-[#161614]"
                      }`}
                    >
                      {/* Active Particle Highlight indicator */}
                      {isParticleActive && (
                        <motion.div
                          layoutId="activeGlow"
                          className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#D79A43] to-[#20B89A]"
                        />
                      )}

                      <div className="flex items-center gap-3.5 sm:gap-4">
                        {/* Node Number & Icon */}
                        <div
                          className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                            isSelected
                              ? `${stage.badgeBg} font-bold`
                              : "bg-white/[0.04] text-[#918D84] border border-white/[0.05]"
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono text-[#66625B]">
                              STAGE {stage.stepNumber}
                            </span>
                            <span className="text-white/20">•</span>
                            <span className="text-[10px] font-mono text-[#918D84]">
                              {stage.role}
                            </span>
                          </div>
                          <span
                            className={`text-xs sm:text-sm font-mono font-bold block ${
                              isSelected ? "text-[#F5F0E8]" : "text-[#D2CECE]"
                            }`}
                          >
                            {stage.name}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* Stage Specific Invariant badge */}
                        <span className="hidden sm:inline text-[10px] font-mono text-[#918D84] px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.05]">
                          {stage.invariant}
                        </span>
                        <ChevronRight
                          className={`w-4 h-4 transition-transform ${
                            isSelected ? "text-[#D79A43] translate-x-1" : "text-white/20"
                          }`}
                        />
                      </div>
                    </motion.button>
                  );
                })}

                {/* Final Terminal State Banner */}
                <div className="p-3.5 rounded-xl bg-[#20B89A]/10 border border-[#20B89A]/40 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2 h-2 rounded-full bg-[#20B89A] animate-pulse" />
                    <span className="text-[#20B89A] font-bold tracking-wider">
                      TERMINAL STATE: REVENUE RECOVERED
                    </span>
                  </div>
                  <span className="text-[11px] text-[#20B89A]/90 font-medium">
                    Settled & Cryptographically Verified
                  </span>
                </div>
              </div>
            </div>

            {/* Selected Node Detail Inspector Drawer */}
            <AnimatePresence mode="wait">
              <motion.div
                key={selectedStage.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ type: "spring", stiffness: 200, damping: 20 }}
                className="mt-6 p-6 rounded-2xl bg-[#11110F] border border-[#D79A43]/30 shadow-lg font-mono"
              >
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/[0.07]">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[#D79A43] font-bold">
                      INSPECTING STAGE {selectedStage.stepNumber}:
                    </span>
                    <span className="text-xs text-[#F5F0E8] font-bold">{selectedStage.name}</span>
                  </div>
                  <span className="text-[10px] text-[#918D84] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.06]">
                    {selectedStage.module}
                  </span>
                </div>

                <p className="text-xs text-[#F5F0E8] font-sans leading-relaxed mb-3">
                  {selectedStage.details}
                </p>

                <div className="flex items-center justify-between text-[11px] pt-2 border-t border-white/[0.05]">
                  <span className="text-[#66625B]">Enforced Safety Invariant:</span>
                  <span className="text-[#20B89A] font-semibold">{selectedStage.invariant}</span>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
