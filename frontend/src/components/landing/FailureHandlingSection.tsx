"use client";

import React from "react";
import { UserCheck, ShieldOff, AlertCircle, Fingerprint } from "lucide-react";

export function FailureHandlingSection() {
  const edgeCases = [
    {
      condition: "AI Model Uncertain",
      behavior: "Routes to Human Review",
      icon: UserCheck,
      detail: "Confidence < 0.75 triggers immediate escalation to merchant console without taking automated action.",
    },
    {
      condition: "Gateway API Unavailable",
      behavior: "Exponential Backoff",
      icon: AlertCircle,
      detail: "Transient network drops trigger jittered exponential backoff with zero duplicated charges.",
    },
    {
      condition: "Retry Limit Exceeded",
      behavior: "Halts Automation",
      icon: ShieldOff,
      detail: "Strict 3-attempt ceiling prevents repetitive customer disturbance and gateway fatigue.",
    },
    {
      condition: "Duplicate Event Received",
      behavior: "Idempotency Lock",
      icon: Fingerprint,
      detail: "SHA-256 idempotency hashing blocks concurrent duplicate recovery triggers across parallel threads.",
    },
  ];

  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-16">
          <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-3">
            11 / Edge Case Governance
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
            Designed for real-world financial failure modes.
          </h2>
          <p className="text-sm font-mono text-[#9E978C] max-w-2xl mt-3">
            Every potential failure mode has a deterministic resolution path defined in policy code.
          </p>
        </div>

        {/* 4 Invariant Handling Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {edgeCases.map((ec, idx) => {
            const Icon = ec.icon;
            return (
              <div
                key={idx}
                className="p-6 rounded-2xl bg-[#15130F] border border-[#F5F0E8]/[0.08] hover:border-[#D79A43]/40 transition-all space-y-3"
              >
                <div className="p-2.5 w-fit rounded-lg bg-[#0D0C0A] border border-[#F5F0E8]/10 text-[#D79A43]">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-[#6B655C] uppercase block">
                    {ec.condition}
                  </span>
                  <h4 className="font-editorial text-lg font-bold text-[#F5F0E8]">
                    {ec.behavior}
                  </h4>
                </div>
                <p className="text-xs font-mono text-[#9E978C] leading-relaxed">
                  {ec.detail}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
