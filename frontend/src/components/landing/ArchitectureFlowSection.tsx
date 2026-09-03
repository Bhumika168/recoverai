"use client";

import React from "react";
import { ArrowRight, Zap, ShieldCheck, CheckCircle2 } from "lucide-react";

export function ArchitectureFlowSection() {
  const nodes = [
    { label: "Transaction Events", sub: "Payment Webhooks" },
    { label: "Detect", sub: "Risk Filter" },
    { label: "Diagnose", sub: "Cognitive Reasoner" },
    { label: "Decide", sub: "Strategy Engine" },
    { label: "Guard", sub: "Deterministic Policies" },
    { label: "Execute", sub: "Bounded Gateway API" },
    { label: "Verify", sub: "Outcome Ledger" },
    { label: "Revenue Recovered", sub: "Net GMV Restored" },
  ];

  return (
    <section id="architecture" className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-16 text-center max-w-3xl mx-auto">
          <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-3">
            10 / Core Architecture Principle
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
            The LLM reasons. The policy engine controls. The payment system executes.
          </h2>
          <p className="text-sm font-mono text-[#9E978C] mt-4 leading-relaxed">
            The fundamental design rule of RecoverAI is financial safety: probabilistic models never possess
            direct write credentials or uncontrolled execution capability.
          </p>
        </div>

        {/* Linear Architecture Flow */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 font-mono text-xs text-center">
          {nodes.map((node, idx) => {
            const isLast = idx === nodes.length - 1;
            const isGuard = node.label === "Guard";
            return (
              <div
                key={idx}
                className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
                  isLast
                    ? "bg-[#2A9D8F]/15 border-[#2A9D8F]/40 text-[#2A9D8F] font-bold"
                    : isGuard
                    ? "bg-[#D79A43]/15 border-[#D79A43]/40 text-[#D79A43] font-bold"
                    : "bg-[#15130F] border-[#F5F0E8]/[0.08] text-[#F5F0E8]"
                }`}
              >
                <span className="text-[10px] text-[#6B655C] block mb-2">0{idx + 1}</span>
                <span className="font-semibold block mb-1 text-xs">{node.label}</span>
                <span className="text-[9px] text-[#6B655C] block leading-tight">{node.sub}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
