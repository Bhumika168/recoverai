"use client";

import React from "react";
import { ArrowUpRight } from "lucide-react";

export function RecoveryIntelligenceMatrix() {
  const matrix = [
    {
      code: "BAD_REQUEST_PAYMENT_TIMED_OUT",
      category: "Temporary Latency",
      probability: 88,
      action: "Delayed Smart Retry",
      delay: "15 min",
      channel: "Gateway Routing",
    },
    {
      code: "INSUFFICIENT_FUNDS",
      category: "Account Limit",
      probability: 72,
      action: "Subscription Cadence Retry",
      delay: "48 hrs",
      channel: "Auto-Debit Mandate",
    },
    {
      code: "CHECKOUT_ABANDONED",
      category: "Customer Drop-off",
      probability: 68,
      action: "Dynamic Recovery Link",
      delay: "Immediate",
      channel: "SMS / WhatsApp Link",
    },
    {
      code: "AUTHENTICATION_FAILED",
      category: "3DS OTP Timeout",
      probability: 81,
      action: "Customer Action Required",
      delay: "5 min",
      channel: "Email & Webhook",
    },
    {
      code: "CARD_STOLEN_OR_LOST",
      category: "Hard Decline",
      probability: 0,
      action: "No Action / Switch Method",
      delay: "None",
      channel: "Method Switch Prompt",
    },
  ];

  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-14">
          <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-3">
            06 / Diagnostic Matrix
          </span>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
            Recovery Intelligence Across Gateway Scenarios
          </h2>
          <p className="text-sm font-mono text-[#9E978C] max-w-2xl mt-3">
            Heuristic and AI classifiers map hundreds of issuing bank failure codes into distinct, bounded recovery strategies.
          </p>
        </div>

        {/* Matrix Table */}
        <div className="editorial-card overflow-hidden rounded-2xl border-[#F5F0E8]/[0.08]">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs">
              <thead>
                <tr className="border-b border-[#F5F0E8]/[0.08] bg-[#0D0C0A]/60 text-[10px] uppercase text-[#6B655C] tracking-wider">
                  <th className="py-4 px-6">Gateway Error Pattern</th>
                  <th className="py-4 px-6">Classification</th>
                  <th className="py-4 px-6">Expected Recovery Probability</th>
                  <th className="py-4 px-6">Recommended Action</th>
                  <th className="py-4 px-6 text-right">Execution Window</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F5F0E8]/[0.06]">
                {matrix.map((row, idx) => (
                  <tr key={idx} className="hover:bg-[#1C1914]/40 transition-colors">
                    <td className="py-4 px-6 font-semibold text-[#F5F0E8]">
                      {row.code}
                    </td>

                    <td className="py-4 px-6 text-[#9E978C]">
                      {row.category}
                    </td>

                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-[#0D0C0A] rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              row.probability >= 80
                                ? "bg-[#2A9D8F]"
                                : row.probability > 0
                                ? "bg-[#D79A43]"
                                : "bg-[#E63946]"
                            }`}
                            style={{ width: `${Math.max(5, row.probability)}%` }}
                          />
                        </div>
                        <span
                          className={`font-bold ${
                            row.probability > 0 ? "text-[#F5F0E8]" : "text-[#E63946]"
                          }`}
                        >
                          {row.probability}%
                        </span>
                      </div>
                    </td>

                    <td className="py-4 px-6 text-[#D79A43] font-medium">
                      {row.action}
                    </td>

                    <td className="py-4 px-6 text-right text-[#9E978C]">
                      {row.delay} ({row.channel})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
