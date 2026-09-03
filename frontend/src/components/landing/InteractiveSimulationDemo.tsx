"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Brain,
  ShieldCheck,
  Zap,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Lock,
} from "lucide-react";

export function InteractiveSimulationDemo() {
  const [phase, setPhase] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const phases = [
    {
      id: "failed",
      phaseNumber: "PHASE 01",
      stepName: "FAILED",
      title: "1. Payment Failure Event Received",
      amount: "₹8,500",
      amountStatus: "FAILED",
      badgeColor: "bg-[#E56B6F]/15 text-[#E56B6F] border-[#E56B6F]/30",
      description:
        "Customer initiated ₹8,500 order. Payment gateway returned BAD_REQUEST_PAYMENT_TIMED_OUT from issuer auth bank.",
      actionText: "Detector ingesting failure telemetry...",
      telemetry: {
        event: "payment.failed",
        transaction_id: "txn_live_99214",
        amount_in_inr: 8500,
        gateway_error: "BAD_REQUEST_PAYMENT_TIMED_OUT",
        status: "FAILED",
      },
    },
    {
      id: "detected",
      phaseNumber: "PHASE 02",
      stepName: "DETECTED",
      title: "2. Viability & Lifetime Value Analysis",
      amount: "₹8,500",
      amountStatus: "EVALUATING",
      badgeColor: "bg-[#D79A43]/15 text-[#D79A43] border-[#D79A43]/30",
      description:
        "Detector isolates drop-off, verifies customer lifetime history (₹42,000 LTV), and initiates isolated Recovery Case.",
      actionText: "Dispatching to AI Diagnostician...",
      telemetry: {
        case_id: "rec_case_88201",
        customer_ltv: 42000,
        recovery_priority: "HIGH",
        status: "DETECTED",
      },
    },
    {
      id: "diagnosed",
      phaseNumber: "PHASE 03",
      stepName: "DIAGNOSED",
      title: "3. Root Cause AI Diagnosis",
      amount: "₹8,500",
      amountStatus: "DIAGNOSED",
      badgeColor: "bg-[#D79A43]/15 text-[#D79A43] border-[#D79A43]/30",
      description:
        "Diagnostician classifies error as transient network timeout with 94% confidence. Issuer servers have resumed normal throughput.",
      actionText: "Formulating bounded recovery decision...",
      telemetry: {
        classification: "TRANSIENT_FAILURE",
        confidence: 0.94,
        root_cause: "Bank auth server transient spike",
        status: "DIAGNOSED",
      },
    },
    {
      id: "policy",
      phaseNumber: "PHASE 04",
      stepName: "POLICY CHECK",
      title: "4. Deterministic Policy Verification",
      amount: "₹8,500",
      amountStatus: "GUARDED",
      badgeColor: "bg-[#D79A43]/15 text-[#D79A43] border-[#D79A43]/30",
      description:
        "Policy engine executes 6 deterministic invariant checks. Retries ≤ 3 (0/3), cooldown active, transaction < ₹25,000.",
      actionText: "Authorizing recovery execution...",
      telemetry: {
        policy_verdict: "RETRY_ALLOWED",
        prior_retries: 0,
        max_allowed_retries: 3,
        safety_status: "PASSED",
      },
    },
    {
      id: "action",
      phaseNumber: "PHASE 05",
      stepName: "RECOVERY ACTION",
      title: "5. Safe Bounded Execution",
      amount: "₹8,500",
      amountStatus: "DISPATCHED",
      badgeColor: "bg-[#D79A43]/15 text-[#D79A43] border-[#D79A43]/30",
      description:
        "Smart dynamic payment link created and dispatched to customer with mutual exclusion lock.",
      actionText: "Awaiting customer settlement...",
      telemetry: {
        action_type: "DELAYED_SMART_RETRY",
        payment_link_id: "plink_live_99014",
        idempotency_key: "e4a8...7b21",
        status: "ACTIVE",
      },
    },
    {
      id: "verified",
      phaseNumber: "PHASE 06",
      stepName: "VERIFIED",
      title: "6. Gateway Confirmation & Ledger Hash",
      amount: "₹8,500",
      amountStatus: "CAPTURED",
      badgeColor: "bg-[#20B89A]/15 text-[#20B89A] border-[#20B89A]/30",
      description:
        "Webhook payment.captured received. ₹8,500 settled, cryptographic SHA-256 block chained to immutable ledger.",
      actionText: "Ledger validated • Reconciled",
      telemetry: {
        event: "payment.captured",
        sha256_hash: "3e5a7b...c9120",
        chain_height: 4892,
        status: "VERIFIED",
      },
    },
    {
      id: "recovered",
      phaseNumber: "PHASE 07",
      stepName: "REVENUE RECOVERED",
      title: "7. Revenue Recovered & Reconciled",
      amount: "₹8,500",
      amountStatus: "RECOVERED",
      badgeColor: "bg-[#20B89A]/20 text-[#20B89A] border-[#20B89A]/40",
      description:
        "Transaction complete: ₹8,500 recovered without human escalation. Merchant dashboard updated in real time.",
      actionText: "Autonomous lifecycle complete",
      telemetry: {
        recovered_amount: 8500,
        settlement_status: "RECOVERED",
        time_to_recover_seconds: 42,
        reconciled: true,
      },
    },
  ];

  // Auto-play loop
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        setPhase((prev) => {
          if (prev >= phases.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1800);
    }
    return () => clearInterval(interval);
  }, [isPlaying, phases.length]);

  const handlePlayToggle = () => {
    if (phase >= phases.length - 1) {
      setPhase(0);
    }
    setIsPlaying(!isPlaying);
  };

  const handleReset = () => {
    setIsPlaying(false);
    setPhase(0);
  };

  return (
    <section id="simulation" className="py-24 sm:py-32 border-b border-white/[0.07] bg-[#070706] relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#D79A43]/[0.025] blur-[160px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        {/* Editorial Heading */}
        <div className="mb-14 text-center max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
            <span>AUTONOMOUS AGENT TRACE</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F0E8] leading-[1.08]">
            <span>Watch ₹8,500 Transform from</span>
            <span className="font-serif italic font-normal text-[#D79A43] block mt-1.5">
              Lost to Recovered
            </span>
          </h2>
          <p className="text-sm font-mono text-[#918D84] mt-3">
            Real-time step-by-step execution trace of AI diagnosis, policy invariant checks, and gateway settlement
          </p>
        </div>

        {/* Live Simulation Console */}
        <div className="rounded-2xl bg-[#11110F] border border-white/[0.08] p-6 sm:p-10 shadow-[0_8px_32px_rgba(0,0,0,0.6)] backdrop-blur-xl relative overflow-hidden">
          {/* Top Bar: Value Status & Play Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-white/[0.07] gap-4">
            {/* Dynamic Value Badge */}
            <div className="flex items-center gap-3.5">
              <div className="flex flex-col">
                <span className="text-[10px] font-mono text-[#66625B] uppercase">Transaction Value</span>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-serif font-bold text-[#F5F0E8] tracking-tight">
                    {phases[phase].amount}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold border ${phases[phase].badgeColor}`}>
                    {phases[phase].amountStatus}
                  </span>
                </div>
              </div>
            </div>

            {/* Play Controls */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-[#66625B] mr-2">
                {phases[phase].phaseNumber} OF 07
              </span>

              <motion.button
                onClick={handlePlayToggle}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-colors shadow-gold cursor-pointer"
              >
                {isPlaying ? (
                  <>
                    <Pause className="w-3.5 h-3.5 fill-[#070706]" />
                    <span>Pause</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-[#070706]" />
                    <span>{phase >= phases.length - 1 ? "Replay Trace" : "Play Live Trace"}</span>
                  </>
                )}
              </motion.button>

              <motion.button
                onClick={handleReset}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="p-2.5 rounded-xl bg-[#171614] border border-white/[0.08] text-[#918D84] hover:text-[#F5F0E8] transition-colors cursor-pointer"
                title="Reset simulation"
              >
                <RotateCcw className="w-4 h-4" />
              </motion.button>
            </div>
          </div>

          {/* 7-Step Moving Signal Progress Strip */}
          <div className="my-8 relative">
            {/* Background Line */}
            <div className="absolute top-1/2 left-0 right-0 -translate-y-1/2 h-[2px] bg-white/[0.06] -z-0" />

            {/* Dynamic Gold Progress Line */}
            <motion.div
              className="absolute top-1/2 left-0 -translate-y-1/2 h-[2px] bg-gradient-to-r from-[#E56B6F] via-[#D79A43] to-[#20B89A] -z-0"
              animate={{ width: `${(phase / (phases.length - 1)) * 100}%` }}
              transition={{ type: "spring", stiffness: 100, damping: 20 }}
            />

            {/* 7 Phase Steps */}
            <div className="grid grid-cols-7 gap-1 sm:gap-2 relative z-10">
              {phases.map((p, idx) => {
                const isActive = phase === idx;
                const isPassed = phase > idx;

                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      setIsPlaying(false);
                      setPhase(idx);
                    }}
                    className="flex flex-col items-center group cursor-pointer"
                  >
                    <div
                      className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-[10px] font-mono font-bold transition-all ${
                        isActive
                          ? "bg-[#D79A43] text-[#070706] scale-110 shadow-[0_0_15px_rgba(215,154,67,0.5)]"
                          : isPassed
                          ? "bg-[#20B89A]/20 text-[#20B89A] border border-[#20B89A]/40"
                          : "bg-[#141412] text-[#66625B] border border-white/[0.06] group-hover:border-white/[0.2]"
                      }`}
                    >
                      {idx + 1}
                    </div>
                    <span
                      className={`text-[9px] font-mono mt-2 hidden sm:block truncate max-w-full text-center ${
                        isActive ? "text-[#F5F0E8] font-bold" : "text-[#66625B]"
                      }`}
                    >
                      {p.stepName}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Phase Details & Live Telemetry Inspector */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pt-2">
            {/* Phase Description */}
            <div className="lg:col-span-7 space-y-4">
              <AnimatePresence mode="wait">
                <motion.div
                  key={phases[phase].id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ type: "spring", stiffness: 200, damping: 20 }}
                  className="space-y-3"
                >
                  <h3 className="font-serif text-2xl sm:text-3xl font-bold text-[#F5F0E8] leading-tight">
                    {phases[phase].title}
                  </h3>
                  <p className="text-sm font-mono text-[#918D84] leading-relaxed">
                    {phases[phase].description}
                  </p>
                  <div className="pt-2 flex items-center gap-2 text-xs font-mono text-[#D79A43]">
                    <Sparkles className="w-4 h-4" />
                    <span>{phases[phase].actionText}</span>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Live State Payload Inspector */}
            <div className="lg:col-span-5 p-5 rounded-xl bg-[#080807] border border-white/[0.08] font-mono text-xs shadow-inner">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2 text-[10px] uppercase font-bold text-[#66625B]">
                <span>State Payload Inspector</span>
                <span className="text-[#20B89A] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B89A] animate-pulse" />
                  SHA-256 Verified
                </span>
              </div>
              <pre className="text-[#D79A43] text-[11px] leading-relaxed overflow-x-auto py-2 font-mono">
                {JSON.stringify(phases[phase].telemetry, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
