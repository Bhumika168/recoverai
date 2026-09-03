"use client";

import React from "react";
import { CreditCard, ShoppingBag, RefreshCw, ClockAlert } from "lucide-react";

export function ProblemSection() {
  const problems = [
    {
      title: "Payment Failures",
      category: "Infrastructure & Network",
      description:
        "Temporary bank downtime, gateway latency spikes, and 3DS authentication timeouts cause 20%+ of viable transactions to fail silently.",
      icon: CreditCard,
    },
    {
      title: "Checkout Abandonment",
      category: "Intent & Friction",
      description:
        "Buyers encounter payment friction or UPI intent app handoff drop-offs and abandon high-intent carts without automated recovery links.",
      icon: ShoppingBag,
    },
    {
      title: "Subscription Failures",
      category: "Recurring Revenue",
      description:
        "SaaS recurring billing hits transient insufficient funds or card lifecycle expirations, turning active recurring revenue into churn.",
      icon: RefreshCw,
    },
    {
      title: "Overdue Receivables",
      category: "B2B & Invoices",
      description:
        "Unsettled high-value invoices remain pending without smart multi-channel payment links and automated ledger reconciliation.",
      icon: ClockAlert,
    },
  ];

  return (
    <section id="problem" className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08]">
      <div className="max-w-6xl mx-auto">
        {/* Large Editorial Statement */}
        <div className="mb-16">
          <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-3">
            01 / The Leakage Reality
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] max-w-3xl leading-tight">
            Revenue leakage doesn&apos;t happen in one place.
          </h2>
          <p className="text-sm font-mono text-[#9E978C] max-w-2xl mt-4 leading-relaxed">
            Payment failure is not a single binary state. It spans four distinct loss vectors across
            authorization, customer intent, card lifecycle, and enterprise settlement.
          </p>
        </div>

        {/* 4 Pillars Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {problems.map((p, idx) => {
            const Icon = p.icon;
            return (
              <div
                key={idx}
                className="p-8 rounded-2xl bg-[#15130F] border border-[#F5F0E8]/[0.08] hover:border-[#D79A43]/30 transition-all group"
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="p-3 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/10 text-[#D79A43] group-hover:border-[#D79A43]/40 transition-colors">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[11px] font-mono text-[#6B655C] tracking-wider uppercase">
                    Vector 0{idx + 1}
                  </span>
                </div>

                <span className="text-xs font-mono text-[#D79A43] uppercase tracking-wider block mb-1">
                  {p.category}
                </span>
                <h3 className="font-editorial text-xl font-bold text-[#F5F0E8] mb-3">
                  {p.title}
                </h3>
                <p className="text-xs font-mono text-[#9E978C] leading-relaxed">
                  {p.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
