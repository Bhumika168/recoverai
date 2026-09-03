"use client";

import React, { useState } from "react";
import { Brain, ShieldCheck, CheckCircle2, AlertOctagon, ExternalLink } from "lucide-react";

export function AIDecisionInspectionSection() {
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0);

  const cases = [
    {
      title: "SaaS Enterprise Invoice",
      amount: "₹42,500.00",
      method: "CARD (Visa Corporate)",
      failure: "BAD_REQUEST_PAYMENT_TIMED_OUT",
      reason: "Issuing bank authorization server experienced 30s gateway timeout during peak settlement window.",
      probability: 88,
      confidence: 94,
      action: "DELAYED_RETRY",
      policyVerdict: "HELD_FOR_APPROVAL",
      policyNote: "High-value transaction (>= ₹25k). Held in PENDING_APPROVAL for merchant consent.",
      execution: "Merchant one-click approved. Scheduled delayed retry via Intelligent Smart Routing at T+15m.",
      outcome: "RECOVERED (₹42,500.00)",
    },
    {
      title: "E-Commerce Checkout Intent",
      amount: "₹4,899.00",
      method: "UPI Intent",
      failure: "CHECKOUT_ABANDONED",
      reason: "Customer navigated away before completing PIN authorization in UPI payment app.",
      probability: 76,
      confidence: 91,
      action: "PAYMENT_LINK",
      policyVerdict: "APPROVED",
      policyNote: "Standard value under ₹25k threshold. Max retry limit check: 0/3 attempts.",
      execution: "Generated dynamic Smart Payment Link with 24h validity.",
      outcome: "RECOVERED (₹4,899.00)",
    },
    {
      title: "Recurring Subscription Mandate",
      amount: "₹9,999.00",
      method: "SUBSCRIPTION (Auto-Debit)",
      failure: "INSUFFICIENT_FUNDS",
      reason: "Monthly debit attempt exceeded available balance limit on billing date.",
      probability: 65,
      confidence: 89,
      action: "SUBSCRIPTION_RETRY",
      policyVerdict: "APPROVED",
      policyNote: "Auto-debit cadence rule. Retry scheduled after salary cycle window (T+48h).",
      execution: "Scheduled recurring mandate retry with customer multi-channel notification.",
      outcome: "SCHEDULED_RETRY",
    },
  ];

  const current = cases[selectedCaseIdx];

  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-14">
          <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-3">
            04 / Decision Transparency
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
            Every recovery decision is explainable and bounded.
          </h2>
          <p className="text-sm font-mono text-[#9E978C] max-w-2xl mt-3">
            Inspect real scenario decisions: the AI reasons on failure context, while the deterministic policy
            engine enforces strict safety constraints before any recovery action is dispatched.
          </p>
        </div>

        {/* Case Selector Tabs */}
        <div className="flex items-center gap-3 overflow-x-auto pb-3 mb-8">
          {cases.map((c, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedCaseIdx(idx)}
              className={`px-4 py-2 rounded-xl text-xs font-mono whitespace-nowrap transition-all border ${
                selectedCaseIdx === idx
                  ? "bg-[#15130F] border-[#D79A43] text-[#F5F0E8] shadow-gold font-semibold"
                  : "bg-[#15130F]/40 border-[#F5F0E8]/[0.08] text-[#9E978C] hover:text-[#F5F0E8]"
              }`}
            >
              <span>{c.title}</span>
              <span className="text-[#D79A43] ml-2 font-bold">{c.amount}</span>
            </button>
          ))}
        </div>

        {/* Interactive Case Visualizer Box */}
        <div className="editorial-card p-8 rounded-2xl border-[#F5F0E8]/10 space-y-6">
          {/* Header Row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#F5F0E8]/[0.08] gap-4">
            <div>
              <span className="text-[11px] font-mono text-[#6B655C] uppercase tracking-wider block">
                Transaction at Risk
              </span>
              <div className="flex items-baseline gap-3">
                <span className="font-editorial text-3xl sm:text-4xl font-bold text-[#F5F0E8]">
                  {current.amount}
                </span>
                <span className="text-xs font-mono text-[#9E978C]">({current.method})</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-right">
                <span className="text-[10px] font-mono text-[#6B655C] uppercase block">
                  Recovery Probability
                </span>
                <span className="text-2xl font-mono font-bold text-[#2A9D8F]">
                  {current.probability}%
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-mono text-[#6B655C] uppercase block">
                  AI Confidence
                </span>
                <span className="text-2xl font-mono font-bold text-[#D79A43]">
                  {current.confidence}%
                </span>
              </div>
            </div>
          </div>

          {/* Diagnostic Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/[0.06]">
                <span className="text-[10px] font-mono text-[#E76F51] uppercase tracking-wider block mb-1 flex items-center gap-1.5">
                  <AlertOctagon className="w-3.5 h-3.5" />
                  Failure Diagnosis
                </span>
                <span className="text-xs font-mono text-[#F5F0E8] font-bold block mb-1">
                  {current.failure}
                </span>
                <p className="text-xs font-mono text-[#9E978C] leading-relaxed">
                  {current.reason}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/[0.06]">
                <span className="text-[10px] font-mono text-[#D79A43] uppercase tracking-wider block mb-1 flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5" />
                  Recommended Strategy
                </span>
                <span className="text-xs font-mono text-[#F5F0E8] font-bold block">
                  {current.action}
                </span>
              </div>
            </div>

            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/[0.06]">
                <span className="text-[10px] font-mono text-[#2A9D8F] uppercase tracking-wider block mb-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Deterministic Policy Check
                </span>
                <span className="text-xs font-mono text-[#F5F0E8] font-bold block mb-1">
                  Status: {current.policyVerdict}
                </span>
                <p className="text-xs font-mono text-[#9E978C] leading-relaxed">
                  {current.policyNote}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/[0.06]">
                <span className="text-[10px] font-mono text-[#E5A958] uppercase tracking-wider block mb-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Execution &amp; Proven Outcome
                </span>
                <p className="text-xs font-mono text-[#9E978C] leading-relaxed mb-2">
                  {current.execution}
                </p>
                <span className="inline-flex items-center px-2.5 py-1 rounded bg-[#2A9D8F]/15 border border-[#2A9D8F]/30 text-[#2A9D8F] text-xs font-mono font-bold">
                  {current.outcome}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
