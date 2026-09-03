"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, LayoutDashboard, CreditCard, RefreshCw, FileCheck2 } from "lucide-react";

export function DashboardPreviewSection() {
  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
          <div>
            <span className="text-xs font-mono text-[#D79A43] uppercase tracking-widest block mb-3">
              08 / Merchant Interface
            </span>
            <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
              A command center designed for financial clarity.
            </h2>
            <p className="text-sm font-mono text-[#9E978C] max-w-xl mt-3">
              Monitor real-time revenue at risk, authorize enterprise recovery gates, and audit cryptographically verified state ledgers.
            </p>
          </div>

          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl bg-[#15130F] text-[#F5F0E8] font-mono font-bold text-xs border border-[#F5F0E8]/15 hover:border-[#D79A43]/50 hover:bg-[#1C1914] transition-all flex items-center gap-2 group w-fit"
          >
            <span>Open Command Center</span>
            <ArrowRight className="w-4 h-4 text-[#D79A43] group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* Dashboard Mock Shell */}
        <div className="editorial-card rounded-2xl border-[#F5F0E8]/15 overflow-hidden shadow-2xl bg-[#15130F] relative group">
          {/* Top Mock Window Bar */}
          <div className="h-10 bg-[#0D0C0A] border-b border-[#F5F0E8]/10 px-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
            </div>
            <span className="text-[11px] font-mono text-[#6B655C]">
              https://recoverai.internal/dashboard
            </span>
            <div className="w-10" />
          </div>

          {/* Inner Dashboard Mock Content */}
          <div className="p-6 space-y-6">
            {/* Quick KPI Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/10">
                <span className="text-[10px] font-mono text-[#6B655C] uppercase block">Revenue at Risk</span>
                <span className="text-xl font-mono font-bold text-[#F5F0E8]">₹1,95,890.00</span>
              </div>
              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#D79A43]/30">
                <span className="text-[10px] font-mono text-[#D79A43] uppercase block">Revenue Recovered</span>
                <span className="text-xl font-mono font-bold text-[#D79A43]">₹76,499.00</span>
              </div>
              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/10">
                <span className="text-[10px] font-mono text-[#6B655C] uppercase block">Active Cases</span>
                <span className="text-xl font-mono font-bold text-[#F5F0E8]">15 Cases</span>
              </div>
              <div className="p-4 rounded-xl bg-[#0D0C0A] border border-[#F5F0E8]/10">
                <span className="text-[10px] font-mono text-[#6B655C] uppercase block">Audit Proof</span>
                <span className="text-xl font-mono font-bold text-[#2A9D8F]">100% Valid</span>
              </div>
            </div>

            {/* Mock Table Snippet */}
            <div className="rounded-xl border border-[#F5F0E8]/10 overflow-hidden font-mono text-xs">
              <div className="bg-[#0D0C0A] p-3 text-[10px] text-[#6B655C] uppercase border-b border-[#F5F0E8]/10 flex justify-between">
                <span>Live Opportunity Queue</span>
                <span>FastAPI Reconciled</span>
              </div>
              <div className="divide-y divide-[#F5F0E8]/[0.06] bg-[#15130F]">
                <div className="p-3.5 flex items-center justify-between">
                  <span className="text-[#F5F0E8]">Case #case_8f912a • Ananya Sharma</span>
                  <span className="text-[#D79A43] font-bold">₹14,999.00</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40 text-[10px]">
                    RECOVERED
                  </span>
                </div>
                <div className="p-3.5 flex items-center justify-between">
                  <span className="text-[#F5F0E8]">Case #case_c4910b • Vikram Malhotra</span>
                  <span className="text-[#F5F0E8] font-bold">₹42,500.00</span>
                  <span className="px-2 py-0.5 rounded bg-orange-950/80 text-orange-300 border border-orange-700/60 text-[10px] animate-pulse">
                    PENDING APPROVAL
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Overlay Button */}
          <div className="absolute inset-0 bg-[#0D0C0A]/40 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Link
              href="/dashboard"
              className="px-6 py-3 rounded-xl bg-[#D79A43] text-[#0D0C0A] font-mono font-bold text-xs shadow-gold flex items-center gap-2"
            >
              <span>Explore Live Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
