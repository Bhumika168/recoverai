"use client";

import React from "react";
import { Search, Brain, GitFork, CheckCircle2 } from "lucide-react";

export function ProductStatementSection() {
  const steps = [
    {
      label: "Detect",
      number: "01",
      icon: Search,
      tag: "Event Risk Filter",
      description:
        "Ingests gateway events and transaction telemetry instantly to identify viable revenue recovery opportunities.",
    },
    {
      label: "Diagnose",
      number: "02",
      icon: Brain,
      tag: "8-Category Classification",
      description:
        "Extracts root cause: parses gateway sub-codes into temporary latency, insufficient funds, or hard decline.",
    },
    {
      label: "Decide",
      number: "03",
      icon: GitFork,
      tag: "Probabilistic Strategy",
      description:
        "Recommends the optimal recovery action with confidence scores, delay windows, and expected recovery probability.",
    },
    {
      label: "Recover",
      number: "04",
      icon: CheckCircle2,
      tag: "Policy Governed Execution",
      description:
        "Executes bounded workflows through dynamic payment links and intelligent retries, then cryptographically proves the outcome.",
    },
  ];

  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center max-w-4xl mx-auto mb-20">
          <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-4">
            02 / Autonomous Architecture
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl lg:text-6xl font-bold text-[#F5F0E8] leading-tight mb-6">
            We built an agent that doesn&apos;t stop at{" "}
            <span className="text-[#D79A43] italic font-normal">&ldquo;payment failed.&rdquo;</span>
          </h2>
          <p className="text-sm font-mono text-[#9E978C] max-w-2xl mx-auto leading-relaxed">
            Where legacy payment gateways drop the connection, RecoverAI begins an end-to-end cognitive
            recovery lifecycle governed by non-negotiable deterministic safety policies.
          </p>
        </div>

        {/* 4 Pillars Horizontal Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={idx}
                className="p-6 rounded-2xl bg-[#15130F] border border-[#F5F0E8]/[0.08] hover:border-[#D79A43]/40 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <span className="font-mono text-2xl font-bold text-[#D79A43]">
                      {step.number}
                    </span>
                    <div className="p-2 rounded-lg bg-[#0D0C0A] border border-[#F5F0E8]/10 text-[#D79A43]">
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>
                  <h3 className="font-editorial text-2xl font-bold text-[#F5F0E8] mb-1">
                    {step.label}.
                  </h3>
                  <span className="text-[10px] font-mono text-[#D79A43] uppercase tracking-wider block mb-3">
                    {step.tag}
                  </span>
                  <p className="text-xs font-mono text-[#9E978C] leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
