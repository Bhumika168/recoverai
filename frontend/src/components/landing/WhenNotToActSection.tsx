"use client";

import React from "react";
import { ShieldCheck, Brain, Lock, AlertOctagon, CheckCircle2, ShieldAlert } from "lucide-react";

export function WhenNotToActSection() {
  return (
    <section id="safety" className="py-20 lg:py-28 border-b border-white/[0.07] bg-[#0A0A09]">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-14 text-center max-w-2xl mx-auto">
          <span className="mono-label text-[#D9A441] block mb-2">Deterministic Safety</span>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F1E8]">
            AI Proposes. Policy Decides.
          </h2>
          <p className="text-xs font-mono text-[#918D84] mt-2">
            The LLM reasons probabilistically, but execution is strictly governed by deterministic invariant rules
          </p>
        </div>

        {/* Side-by-Side Architectural Contrast */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          {/* Left: Probabilistic AI Reasoning */}
          <div className="fintech-card p-8 bg-[#151513] border-white/[0.08] space-y-4">
            <div className="flex items-center gap-3 border-b border-white/[0.06] pb-4">
              <div className="w-10 h-10 rounded-xl bg-[#D9A441]/15 border border-[#D9A441]/30 flex items-center justify-center text-[#D9A441]">
                <Brain className="w-5 h-5" />
              </div>
              <div>
                <span className="mono-label text-[#D9A441]">Probabilistic Intelligence</span>
                <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#F5F1E8]">AI Reasoning Model</h3>
              </div>
            </div>

            <p className="text-xs font-mono text-[#918D84] leading-relaxed">
              Analyzes multi-dimensional failure context, customer lifetime value, issuer network status,
              and historic retry success rates to propose optimal strategies.
            </p>

            <div className="space-y-2.5 pt-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#0A0A09] border border-white/[0.06] flex items-center justify-between text-[#918D84]">
                <span>Strategy Selection</span>
                <span className="text-[#F0B84B] font-semibold">Recommended</span>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A09] border border-white/[0.06] flex items-center justify-between text-[#918D84]">
                <span>Confidence Assessment</span>
                <span className="text-[#36C9A5] font-semibold">Probabilistic Score</span>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A09] border border-white/[0.06] flex items-center justify-between text-[#918D84]">
                <span>Authority</span>
                <span className="text-[#E56B6F] font-semibold">Zero Direct Gateway Control</span>
              </div>
            </div>
          </div>

          {/* Right: Deterministic Policy Engine */}
          <div className="fintech-card-gold p-8 bg-[#151513] space-y-4">
            <div className="flex items-center gap-3 border-b border-white/[0.06] pb-4">
              <div className="w-10 h-10 rounded-xl bg-[#36C9A5]/15 border border-[#36C9A5]/30 flex items-center justify-center text-[#36C9A5]">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <span className="mono-label text-[#36C9A5]">Deterministic Authority</span>
                <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#F5F1E8]">Policy Safety Engine</h3>
              </div>
            </div>

            <p className="text-xs font-mono text-[#918D84] leading-relaxed">
              Enforces hard mathematical rules that cannot be bypassed by any prompt or model hallucination.
              Executes or halts actions with deterministic certainty.
            </p>

            <div className="space-y-2.5 pt-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#0A0A09] border border-white/[0.06] flex items-center justify-between text-[#918D84]">
                <span>Max 3 Retry Invariant</span>
                <span className="text-[#36C9A5] font-semibold">Hard Circuit Breaker</span>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A09] border border-white/[0.06] flex items-center justify-between text-[#918D84]">
                <span>Hard Decline Suppression</span>
                <span className="text-[#E56B6F] font-semibold">Instant Halt</span>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A09] border border-white/[0.06] flex items-center justify-between text-[#918D84]">
                <span>High-Value Gate (≥ ₹25,000)</span>
                <span className="text-[#E5A958] font-semibold">Mandatory Human Approval</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
