"use client";

import React from "react";
import { motion } from "framer-motion";
import { LucideIcon, Sparkles } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  secondaryValue?: string;
  icon?: LucideIcon;
  variant?: "primary" | "secondary" | "standard";
  trend?: string;
  isPositiveTrend?: boolean;
  isLoading?: boolean;
}

export function MetricCard({
  title,
  value,
  subtitle,
  secondaryValue,
  icon: Icon = Sparkles,
  variant = "standard",
  trend,
  isPositiveTrend = true,
  isLoading = false,
}: MetricCardProps) {
  if (isLoading) {
    return (
      <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] animate-pulse space-y-3">
        <div className="h-3.5 w-24 bg-white/[0.05] rounded" />
        <div className="h-9 w-40 bg-white/[0.05] rounded" />
        <div className="h-3 w-32 bg-white/[0.05] rounded" />
      </div>
    );
  }

  // Large Primary Hero Card (Revenue at Risk - 2x Visual Weight)
  if (variant === "primary") {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        transition={{ type: "spring", stiffness: 350, damping: 25 }}
        className="p-7 rounded-2xl relative overflow-hidden bg-[#11110F] border border-white/[0.09] hover:border-[#D79A43]/40 transition-colors shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-col justify-between h-full"
      >
        {/* Subtle Ambient Gold Hue */}
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-[#D79A43]/[0.05] blur-3xl rounded-full pointer-events-none" />

        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono uppercase tracking-widest text-[#918D84]">
              {title}
            </span>
            <div className="p-2 rounded-xl bg-[#171614] border border-white/[0.08] text-[#D79A43]">
              <Icon className="w-4 h-4" />
            </div>
          </div>
          <div className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold text-[#F5F0E8] tracking-tight tabular-nums mb-2">
            {value}
          </div>
        </div>

        <div className="pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono">
          <span className="text-[#918D84]">{subtitle || "Identified failure & drop-off volume"}</span>
          {trend && (
            <span className={isPositiveTrend ? "text-[#20B89A] font-bold" : "text-[#E56B6F] font-bold"}>
              {trend}
            </span>
          )}
        </div>
      </motion.div>
    );
  }

  // Secondary Highlighted Card (Revenue Recovered / Gold + Emerald)
  if (variant === "secondary") {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        transition={{ type: "spring", stiffness: 350, damping: 25 }}
        className="p-6 rounded-2xl relative overflow-hidden bg-[#11110F] border border-[#D79A43]/30 hover:border-[#D79A43]/60 transition-colors shadow-[0_8px_32px_rgba(0,0,0,0.4)] flex flex-col justify-between h-full"
      >
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-mono uppercase tracking-widest text-[#D79A43] font-bold">
              {title}
            </span>
            <div className="p-1.5 rounded-lg bg-[#D79A43]/15 text-[#D79A43]">
              <Icon className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="font-serif text-3xl sm:text-4xl font-bold text-[#D79A43] tracking-tight tabular-nums mb-1">
            {value}
          </div>
        </div>

        <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono">
          <span className="text-[#918D84]">{subtitle}</span>
          {trend && (
            <span className="text-[#20B89A] font-bold bg-[#20B89A]/10 px-2 py-0.5 rounded border border-[#20B89A]/30">
              {trend}
            </span>
          )}
        </div>
      </motion.div>
    );
  }

  // Standard Compact Metric Card
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 350, damping: 25 }}
      className="p-5 rounded-2xl bg-[#11110F] border border-white/[0.08] hover:border-white/[0.15] transition-colors flex flex-col justify-between h-full"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[#66625B]">
          {title}
        </span>
        <Icon className="w-3.5 h-3.5 text-[#66625B]" />
      </div>

      <div className="font-mono text-2xl font-bold text-[#F5F0E8] tracking-tight tabular-nums mb-1">
        {value}
      </div>

      {subtitle && (
        <span className="text-[10px] font-mono text-[#918D84]">{subtitle}</span>
      )}
    </motion.div>
  );
}
