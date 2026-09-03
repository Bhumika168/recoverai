"use client";

import React from "react";
import Link from "next/link";
import { Zap, ArrowUpRight, ShieldCheck } from "lucide-react";

export function LandingNav() {
  return (
    <header className="sticky top-0 z-50 bg-[#0A0A09]/90 backdrop-blur-md border-b border-white/[0.07] px-6 lg:px-12 py-3.5 flex items-center justify-between">
      {/* Brand Identity */}
      <Link href="/" className="flex items-center gap-3 group">
        <div className="w-8 h-8 rounded-lg bg-[#D9A441]/15 border border-[#D9A441]/35 flex items-center justify-center text-[#D9A441] shadow-gold-sm transition-all group-hover:scale-105">
          <Zap className="w-4 h-4 fill-[#D9A441]" />
        </div>
        <div className="flex items-center gap-2">
          <span className="font-serif text-xl font-bold text-[#F5F1E8] tracking-tight">
            Recover<span className="text-[#D9A441] italic font-normal">AI</span>
          </span>
          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#151513] text-[#918D84] border border-white/[0.08]">
            v2.4
          </span>
        </div>
      </Link>

      {/* Nav Links */}
      <nav className="hidden md:flex items-center gap-8 text-xs font-mono text-[#918D84]">
        <a href="#workflow" className="hover:text-[#F5F1E8] transition-colors">
          Workflow
        </a>
        <a href="#simulation" className="hover:text-[#F5F1E8] transition-colors">
          Interactive Demo
        </a>
        <a href="#safety" className="hover:text-[#F5F1E8] transition-colors">
          Deterministic Safety
        </a>
        <a href="#matrix" className="hover:text-[#F5F1E8] transition-colors">
          Error Matrix
        </a>
      </nav>

      {/* Primary Action Buttons */}
      <div className="flex items-center gap-3 text-xs font-mono">
        <Link
          href="/login"
          className="text-[#918D84] hover:text-[#F5F0E8] px-3 py-2 transition-colors hidden sm:inline"
        >
          Sign In
        </Link>
        <Link
          href="/signup"
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] transition-all shadow-gold cursor-pointer"
        >
          <span>Sign Up</span>
        </Link>
        <Link
          href="/dashboard"
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-[#151513] text-[#F5F0E8] hover:bg-[#1A1A18] border border-white/[0.09] hover:border-[#D79A43]/40 transition-all shadow-sm group"
        >
          <span>Console</span>
          <ArrowUpRight className="w-3.5 h-3.5 text-[#D79A43] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
        </Link>
      </div>
    </header>
  );
}
