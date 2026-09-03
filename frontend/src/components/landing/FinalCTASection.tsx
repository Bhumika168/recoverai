"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, Zap, ShieldCheck } from "lucide-react";

export function FinalCTASection() {
  return (
    <section className="py-24 lg:py-32 border-b border-white/[0.07] bg-[#0A0A09] relative overflow-hidden text-center">
      <div className="max-w-4xl mx-auto px-6 relative z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#151513] border border-white/[0.09] text-[11px] font-mono text-[#D9A441] mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-[#D9A441] animate-pulse" />
          <span>AUTONOMOUS REVENUE RECOVERY</span>
        </div>

        <h2 className="font-serif text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-[#F5F1E8] mb-6 leading-tight">
          There is revenue waiting <br />
          <span className="italic font-normal text-[#F0B84B]">to come back.</span>
        </h2>

        <p className="max-w-xl mx-auto text-sm sm:text-base font-mono text-[#918D84] leading-relaxed mb-10">
          Deploy bounded AI recovery workflows for your payment transactions in minutes with cryptographic auditability.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#D9A441] text-[#0A0A09] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center justify-center gap-2 group"
          >
            <span>Launch Merchant Dashboard</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a
            href="#simulation"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#151513] text-[#F5F1E8] hover:bg-[#1A1A18] border border-white/[0.10] hover:border-[#D9A441]/40 font-mono text-xs font-medium transition-all shadow-sm"
          >
            <span>Replay Simulation</span>
          </a>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter() {
  return (
    <footer className="py-12 bg-[#0A0A09] text-[#66625B] font-mono text-xs border-t border-white/[0.06]">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-lg bg-[#D9A441]/15 border border-[#D9A441]/35 flex items-center justify-center text-[#D9A441]">
            <Zap className="w-3 h-3 fill-[#D9A441]" />
          </div>
          <span className="text-[#F5F0E8] font-bold">
            Recover<span className="text-[#D9A441]">AI</span>
          </span>
          <span>• Autonomous Financial Infrastructure</span>
        </div>

        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="hover:text-[#F5F1E8] transition-colors">
            Merchant Console
          </Link>
          <Link href="/dashboard/transactions" className="hover:text-[#F5F1E8] transition-colors">
            Transactions
          </Link>
          <Link href="/dashboard/audit" className="hover:text-[#F5F1E8] transition-colors">
            SHA-256 Ledger
          </Link>
        </div>
      </div>
    </footer>
  );
}
