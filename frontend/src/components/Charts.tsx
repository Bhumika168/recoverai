"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Brain,
  ShieldCheck,
  Zap,
  CheckCircle2,
  TrendingUp,
  Activity,
  ArrowRight,
} from "lucide-react";
import { DashboardChartsData } from "@/lib/types";

interface ChartsProps {
  data?: DashboardChartsData;
  isLoading?: boolean;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-3.5 bg-[#171614] border border-white/[0.12] rounded-xl shadow-2xl text-xs font-mono">
        <p className="text-[#F5F0E8] font-bold mb-2 pb-1 border-b border-white/[0.08]">{label}</p>
        {payload.map((item: any, idx: number) => (
          <div key={idx} className="flex items-center justify-between gap-5 py-0.5">
            <span className="flex items-center gap-1.5 text-[#918D84]">
              <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: item.color || item.fill }} />
              {item.name}:
            </span>
            <span className="text-[#F5F0E8] font-bold">
              {typeof item.value === "number" && item.value >= 100
                ? `₹${item.value.toLocaleString("en-IN")}`
                : item.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// 5. Telemetry Chart: Revenue Recovery Trajectory
export function RevenueTrendChart({ data, isLoading }: ChartsProps) {
  if (isLoading) {
    return <div className="h-80 rounded-2xl bg-[#11110F] border border-white/[0.08] animate-pulse" />;
  }

  const chartData = data?.recovery_trend || [];

  return (
    <div className="p-6 sm:p-7 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/[0.06] mb-5 gap-2">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-[#D79A43] block mb-1">
            TELEMETRY ANALYSIS
          </span>
          <h3 className="font-serif text-2xl sm:text-3xl font-bold text-[#F5F0E8] tracking-tight">
            Revenue Recovery Trajectory
          </h3>
        </div>
        <div className="flex items-center gap-5 text-xs font-mono">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-[#D79A43]" />
            <span className="text-[#918D84]">At Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-[#20B89A]" />
            <span className="text-[#20B89A] font-bold">Recovered</span>
          </div>
        </div>
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <defs>
              <linearGradient id="trendRisk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#D79A43" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#D79A43" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="trendRecovered" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#20B89A" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#20B89A" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="2 2" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="name"
              stroke="#66625B"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
            />
            <YAxis
              stroke="#66625B"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `₹${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="at_risk"
              name="Revenue At Risk"
              stroke="#D79A43"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#trendRisk)"
            />
            <Area
              type="monotone"
              dataKey="recovered"
              name="Revenue Recovered"
              stroke="#20B89A"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#trendRecovered)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// 6. Visual 5-Stage Recovery Funnel Pipeline
export function RecoveryFunnelChart({ data, isLoading }: ChartsProps) {
  if (isLoading) {
    return <div className="h-80 rounded-2xl bg-[#11110F] border border-white/[0.08] animate-pulse" />;
  }

  const funnelData = data?.recovery_funnel || [
    { stage: "Detected", count: 24 },
    { stage: "Diagnosed", count: 22 },
    { stage: "Policy Cleared", count: 20 },
    { stage: "Dispatched", count: 18 },
    { stage: "Recovered", count: 8 },
  ];

  const stages = [
    { id: "01", name: "01 DETECT", label: "Detected", icon: AlertTriangle, color: "text-[#D79A43]", border: "border-[#D79A43]/40" },
    { id: "02", name: "02 DIAGNOSE", label: "Diagnosed", icon: Brain, color: "text-[#D79A43]", border: "border-[#D79A43]/40" },
    { id: "03", name: "03 POLICY", label: "Policy Guard", icon: ShieldCheck, color: "text-[#D79A43]", border: "border-[#D79A43]/40" },
    { id: "04", name: "04 RECOVER", label: "Recover Dispatched", icon: Zap, color: "text-[#D79A43]", border: "border-[#D79A43]/40" },
    { id: "05", name: "05 VERIFY", label: "Verified & Settled", icon: CheckCircle2, color: "text-[#20B89A]", border: "border-[#20B89A]/50" },
  ];

  return (
    <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
      <div className="pb-4 border-b border-white/[0.06] mb-4">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[#918D84] block mb-1">
          STAGE PROGRESSION
        </span>
        <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#F5F0E8]">
          Autonomous Recovery Funnel
        </h3>
      </div>

      {/* 5 Connected Interactive Pipeline Nodes */}
      <div className="space-y-3 my-auto">
        {stages.map((stg, idx) => {
          const Icon = stg.icon;
          const count = funnelData[idx]?.count || 0;
          const isFinal = idx === 4;

          return (
            <div
              key={stg.id}
              className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                isFinal
                  ? "bg-[#20B89A]/10 border-[#20B89A]/40 shadow-[0_0_15px_rgba(32,184,154,0.15)]"
                  : "bg-[#171614] border-white/[0.07] hover:border-white/[0.15]"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-1.5 rounded-lg bg-white/[0.04] ${stg.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-[11px] font-mono font-bold text-[#F5F0E8] block">
                    {stg.name}
                  </span>
                  <span className="text-[9px] font-mono text-[#918D84]">
                    {stg.label}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className={`text-xs font-mono font-bold ${isFinal ? "text-[#20B89A]" : "text-[#D79A43]"}`}>
                  {count} cases
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 7. Failure Reason Breakdown with Percentages
export function FailureReasonDistributionChart({ data, isLoading }: ChartsProps) {
  if (isLoading) {
    return <div className="h-80 rounded-2xl bg-[#11110F] border border-white/[0.08] animate-pulse" />;
  }

  const rawData = data?.failure_distribution || [
    { name: "Temporary Failure", count: 18, color: "#D79A43" },
    { name: "Insufficient Funds", count: 4, color: "#E5A958" },
    { name: "Hard Decline", count: 2, color: "#E56B6F" },
  ];

  const total = rawData.reduce((acc, curr) => acc + curr.count, 0) || 1;

  return (
    <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
      <div className="pb-4 border-b border-white/[0.06] mb-4">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[#918D84] block mb-1">
          DIAGNOSTIC BREAKDOWN
        </span>
        <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#F5F0E8]">
          Failure Reason Distribution
        </h3>
      </div>

      <div className="space-y-4 my-auto">
        {rawData.map((entry, idx) => {
          const pct = Math.round((entry.count / total) * 100);
          return (
            <div key={idx} className="space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#F5F0E8] font-semibold">{entry.name}</span>
                <span className="text-[#D79A43] font-bold">{pct}% ({entry.count})</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/[0.05] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: entry.color || "#D79A43" }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-4 border-t border-white/[0.05] flex items-center justify-between text-[10px] font-mono text-[#66625B]">
        <span>Total Analyzed: {total} Events</span>
        <span className="text-[#20B89A]">100% Classified</span>
      </div>
    </div>
  );
}

// 8. Technical Panel: Recovery Action Breakdown
export function RecoveryActionDistributionChart({ data, isLoading }: ChartsProps) {
  if (isLoading) {
    return <div className="h-80 rounded-2xl bg-[#11110F] border border-white/[0.08] animate-pulse" />;
  }

  const actions = [
    { action: "Delayed Smart Retry", cases: 12, rate: "42.5%", speed: "< 15 min" },
    { action: "Dynamic Recovery Link", cases: 8, rate: "37.8%", speed: "< 2 hours" },
    { action: "Subscription Retry", cases: 3, rate: "28.0%", speed: "Next cycle" },
    { action: "Method Switch", cases: 1, rate: "20.0%", speed: "Immediate" },
  ];

  return (
    <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
      <div className="pb-4 border-b border-white/[0.06] mb-4">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[#918D84] block mb-1">
          STRATEGY EXECUTION
        </span>
        <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#F5F0E8]">
          Recovery Action Breakdown
        </h3>
      </div>

      <div className="space-y-3 my-auto">
        {actions.map((act, idx) => (
          <div
            key={idx}
            className="p-3 rounded-xl bg-[#171614] border border-white/[0.07] flex items-center justify-between font-mono text-xs"
          >
            <div>
              <span className="text-[#F5F0E8] font-semibold block">{act.action}</span>
              <span className="text-[10px] text-[#66625B]">{act.speed}</span>
            </div>
            <div className="text-right">
              <span className="text-[#D79A43] font-bold block">{act.cases} cases</span>
              <span className="text-[10px] text-[#20B89A]">{act.rate} rate</span>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-4 border-t border-white/[0.05] flex items-center justify-between text-[10px] font-mono text-[#66625B]">
        <span>Enforced: Bounded Catalog</span>
        <span className="text-[#20B89A]">Idempotent Locks</span>
      </div>
    </div>
  );
}
