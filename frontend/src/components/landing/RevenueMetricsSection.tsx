"use client";

import React, { useEffect, useState } from "react";
import { TrendingUp, Coins, AlertTriangle, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

export function RevenueMetricsSection() {
  const [metrics, setMetrics] = useState({
    atRisk: "₹12.4L",
    recovered: "₹4.86L",
    rate: "39.2%",
    isLive: false,
  });

  useEffect(() => {
    async function fetchLiveMetrics() {
      try {
        const kpis = await api.getKPIs();
        if (kpis && kpis.revenue_at_risk > 0) {
          const atRiskL = (kpis.revenue_at_risk / 100000).toFixed(2);
          const recL = (kpis.revenue_recovered / 100000).toFixed(2);
          setMetrics({
            atRisk: `₹${atRiskL}L`,
            recovered: `₹${recL}L`,
            rate: `${kpis.recovery_rate_percentage}%`,
            isLive: true,
          });
        }
      } catch {
        // keep benchmark demo values
      }
    }
    fetchLiveMetrics();
  }, []);

  return (
    <section className="py-24 px-6 lg:px-16 border-t border-[#F5F0E8]/[0.08] bg-[#0D0C0A]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#15130F] border border-[#F5F0E8]/10 text-xs font-mono text-[#D79A43] mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43]" />
            <span>{metrics.isLive ? "LIVE RECOVERAI ENGINE" : "RECOVERY BENCHMARKS"}</span>
          </div>
          <h2 className="font-editorial text-3xl sm:text-5xl font-bold text-[#F5F0E8] leading-tight">
            Measurable financial impact in numbers.
          </h2>
          <p className="text-xs font-mono text-[#9E978C] mt-2">
            Automated recovery directly transforms bottom-line net revenue without increasing customer acquisition costs.
          </p>
        </div>

        {/* 3 Giant Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="editorial-card p-8 text-center rounded-2xl border-[#F5F0E8]/10 space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[#6B655C] block">
              Revenue at Risk
            </span>
            <div className="font-editorial text-4xl sm:text-6xl font-bold text-[#F5F0E8]">
              {metrics.atRisk}
            </div>
            <p className="text-xs font-mono text-[#9E978C]">
              Identified across failed checkouts, drop-offs &amp; timeouts
            </p>
          </div>

          <div className="editorial-card p-8 text-center rounded-2xl border-[#D79A43]/40 bg-[#15130F] space-y-3 shadow-gold relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#D79A43]/15 rounded-full blur-2xl pointer-events-none" />
            <span className="text-xs font-mono uppercase tracking-widest text-[#D79A43] block font-semibold">
              Revenue Recovered
            </span>
            <div className="font-editorial text-4xl sm:text-6xl font-bold text-[#D79A43]">
              {metrics.recovered}
            </div>
            <p className="text-xs font-mono text-[#F5F0E8]">
              Successfully captured and verified by autonomous agent
            </p>
          </div>

          <div className="editorial-card p-8 text-center rounded-2xl border-[#F5F0E8]/10 space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[#6B655C] block">
              Benchmark Recovery Rate
            </span>
            <div className="font-editorial text-4xl sm:text-6xl font-bold text-[#2A9D8F]">
              {metrics.rate}
            </div>
            <p className="text-xs font-mono text-[#9E978C]">
              Average recovery conversion across transient failure categories
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
