"use client";

import React from "react";
import { Fingerprint, Lock, ShieldCheck } from "lucide-react";

export function AuditTrailSection() {
  const auditTimeline = [
    {
      step: "GENESIS",
      event: "TRANSACTION_INGESTED",
      actor: "GATEWAY_WEBHOOK",
      hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      notes: "Failed payment event received for ₹14,999.00 (Timeout)",
    },
    {
      step: "NODE 01",
      event: "FAILURE_DIAGNOSED",
      actor: "DIAGNOSTICIAN_AGENT",
      hash: "8f4b23c91e0a77b81923485d263901a89c31405e32187654ba0987654321cba9",
      notes: "Diagnosed as temporary_failure with 88% recovery likelihood",
    },
    {
      step: "NODE 02",
      event: "POLICY_EVALUATED",
      actor: "POLICY_ENGINE",
      hash: "7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
      notes: "Passed Invariant 1 (Attempt 0/3) & Invariant 4 (Amount < ₹25k)",
    },
    {
      step: "NODE 03",
      event: "RECOVERY_VERIFIED",
      actor: "OUTCOME_VERIFIER",
      hash: "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
      notes: "Payment captured via automated smart retry. ₹14,999.00 recovered.",
    },
  ];

  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-16">
          <span className="text-xs font-mono text-[#2A9D8F] uppercase tracking-widest block mb-3 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            09 / Cryptographic Immutability
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
            An audit trail that cannot be rewritten.
          </h2>
          <p className="text-sm font-mono text-[#9E978C] max-w-2xl mt-3 leading-relaxed">
            Every AI diagnosis, policy check, and financial outcome is cryptographically hashed in sequence
            using SHA-256 state chaining, providing complete auditability for financial controllers and regulators.
          </p>
        </div>

        {/* Chained Ledger Timeline */}
        <div className="space-y-4 font-mono text-xs">
          {auditTimeline.map((item, idx) => (
            <div
              key={idx}
              className="editorial-card p-5 rounded-xl border-[#F5F0E8]/[0.08] hover:border-[#D79A43]/30 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="flex items-center gap-4">
                <span className="w-16 text-[10px] text-[#6B655C] uppercase">{item.step}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#F5F0E8]">{item.event}</span>
                    <span className="text-[10px] text-[#D79A43]">by {item.actor}</span>
                  </div>
                  <p className="text-xs text-[#9E978C] mt-0.5">{item.notes}</p>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-[#6B655C] block uppercase">SHA-256 State Hash</span>
                <span className="text-[11px] text-[#2A9D8F] font-bold">
                  {item.hash.slice(0, 24)}...
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
