"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, Variants } from "framer-motion";
import {
  TrendingUp,
  Coins,
  Clock,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  Zap,
  CreditCard,
  FileSpreadsheet,
  PlusCircle,
  ArrowRight,
  ShieldCheck,
  Activity,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  ArrowUpRight,
  Database,
  Check,
  ChevronRight,
} from "lucide-react";
import { MetricCard } from "@/components/MetricCard";
import {
  RevenueTrendChart,
  FailureReasonDistributionChart,
  RecoveryFunnelChart,
} from "@/components/Charts";
import { DashboardKPIs, DashboardChartsData, RecoveryCase } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function DashboardOverviewPage() {
  const { user, organization } = useAuth();
  const [timeRange, setTimeRange] = useState("all");
  const [kpis, setKpis] = useState<any | null>(null);
  const [chartsData, setChartsData] = useState<DashboardChartsData | null>(null);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [topOpportunities, setTopOpportunities] = useState<any[]>([]);
  const [dataSources, setDataSources] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoMessage, setDemoMessage] = useState<string | null>(null);
  const [demoStats, setDemoStats] = useState<any | null>(null);
  const [guardrailCases, setGuardrailCases] = useState<{
    case50k?: string;
    caseStolen?: string;
    caseStopped?: string;
  }>({});

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [kpiRes, chartRes, actRes, oppRes, dsRes, casesRes] = await Promise.all([
        api.getKPIs(timeRange),
        api.getCharts(),
        api.getRecentActivity(8),
        api.getTopOpportunities(5),
        api.getDataSourcesStatus(),
        api.getCases(undefined, 100).catch(() => []),
      ]);

      setKpis(kpiRes);
      setChartsData(chartRes);
      setRecentActivity(actRes);
      setTopOpportunities(oppRes);
      setDataSources(dsRes);

      if (casesRes && casesRes.length > 0) {
        const c50k = casesRes.find((c: any) => c.amount_at_risk === 50000);
        const cStolen = casesRes.find((c: any) => c.amount_at_risk === 12000);
        const cStopped = casesRes.find((c: any) => c.amount_at_risk === 4200);
        setGuardrailCases({
          case50k: c50k?.id,
          caseStolen: cStolen?.id,
          caseStopped: cStopped?.id,
        });
      }
    } catch (err: any) {
      console.error("Dashboard fetch failed:", err);
      setError(err.message || "Failed to load dashboard data from backend");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoReset = async () => {
    try {
      setIsDemoRunning(true);
      setDemoMessage("Resetting 50-transaction deterministic dataset...");
      const res = await api.resetDemoDataset();
      setDemoMessage(res.message || "Demo dataset reset with 50 failed transactions.");
      await loadDashboardData();
    } catch (err: any) {
      setDemoMessage(`Reset failed: ${err.message}`);
    } finally {
      setIsDemoRunning(false);
    }
  };

  const handleDemoRun = async () => {
    try {
      setIsDemoRunning(true);
      setDemoMessage("Executing autonomous recovery across 50 transactions...");
      const res = await api.runDemoBatch();
      setDemoStats(res.data);
      setDemoMessage(res.message || "Batch recovery completed.");
      await loadDashboardData();
    } catch (err: any) {
      setDemoMessage(`Run failed: ${err.message}`);
    } finally {
      setIsDemoRunning(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [timeRange]);

  const dashboardContainerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.06,
        delayChildren: 0.04,
      },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 15 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 120,
        damping: 18,
        mass: 0.8,
      },
    },
  };

  const currencySymbol =
    organization?.currency === "USD"
      ? "$"
      : organization?.currency === "EUR"
      ? "€"
      : organization?.currency === "GBP"
      ? "£"
      : "₹";

  const isEmptyWorkspace =
    !isLoading &&
    kpis &&
    kpis.total_cases === 0 &&
    kpis.revenue_at_risk === 0 &&
    (kpis.transaction_summary?.total || 0) === 0;

  return (
    <motion.div
      variants={dashboardContainerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 pb-16 font-sans"
    >
      {/* 1. Dynamic Organization Header */}
      <motion.div
        variants={itemVariants}
        className="flex flex-col lg:flex-row lg:items-end justify-between pb-6 border-b border-white/[0.07] gap-4"
      >
        <div>
          <div className="flex items-center gap-2.5 mb-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30 text-[10px] font-mono font-bold">
              {organization?.name ? organization.name.toUpperCase() : "RECOVERAI WORKSPACE"}
            </span>
            <span className="text-[10px] font-mono text-[#66625B]">●</span>
            <span className="text-[11px] font-mono text-[#918D84]">
              {organization?.environment || "Production"}
            </span>
            {user?.email && (
              <>
                <span className="text-[10px] font-mono text-[#66625B]">●</span>
                <span className="text-[11px] font-mono text-[#66625B]">{user.email}</span>
              </>
            )}
          </div>

          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F0E8]">
            Recovery Control Center
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Real-time bounded revenue recovery • Deterministic policy governance
          </p>
        </div>

        {/* Date Filter & Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Time Range Selector */}
          <div className="flex items-center p-1 rounded-xl bg-[#11110F] border border-white/[0.08] text-xs font-mono">
            {[
              { key: "today", label: "Today" },
              { key: "7d", label: "7 Days" },
              { key: "30d", label: "30 Days" },
              { key: "90d", label: "90 Days" },
              { key: "all", label: "All Time" },
            ].map((r) => (
              <button
                key={r.key}
                onClick={() => setTimeRange(r.key)}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  timeRange === r.key
                    ? "bg-[#D79A43] text-black font-bold"
                    : "text-[#918D84] hover:text-[#F5F0E8]"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          <Link
            href="/dashboard/transactions/new"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono text-[#070706] font-bold bg-[#D79A43] hover:bg-[#F0B84B] transition-all shadow-gold cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>ADD TRANSACTION</span>
          </Link>

          <button
            onClick={loadDashboardData}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono text-[#918D84] hover:text-[#F5F0E8] bg-[#11110F] border border-white/[0.08] hover:border-[#D79A43]/40 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
            <span className="hidden sm:inline">REFRESH</span>
          </button>
        </div>
      </motion.div>

      {/* Error Notice */}
      {error && (
        <motion.div
          variants={itemVariants}
          className="p-4 rounded-xl border border-[#E56B6F]/40 bg-[#E56B6F]/10 text-[#E56B6F] flex items-center justify-between text-xs font-mono"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadDashboardData}
            className="px-3 py-1 rounded-lg bg-[#E56B6F]/20 hover:bg-[#E56B6F]/30 text-xs text-[#F5F0E8]"
          >
            Retry
          </button>
        </motion.div>
      )}

      {/* 2. Hackathon Demonstration Mode Control Bar */}
      <motion.div
        variants={itemVariants}
        className="p-5 rounded-2xl border border-[#D79A43]/30 bg-gradient-to-r from-[#171511] via-[#11110F] to-[#171511] shadow-2xl relative overflow-hidden"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-[#D79A43]/20 text-[#D79A43] border border-[#D79A43]/40 text-[10px] font-mono font-bold uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 animate-pulse" />
                HACKATHON DEMONSTRATION MODE
              </span>
              <span className="text-[11px] font-mono text-[#918D84]">
                Deterministic 50-Transaction Batch
              </span>
            </div>
            <p className="text-xs font-mono text-[#E6E4DF]">
              Run real-time root-cause diagnosis, deterministic policy evaluation, sandbox recovery, and SHA-256 audit ledger tracking.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handleDemoReset}
              disabled={isDemoRunning}
              className="px-3.5 py-2 rounded-xl text-xs font-mono font-bold bg-[#1A1916] hover:bg-[#252420] text-[#E6E4DF] border border-white/[0.12] hover:border-[#D79A43]/40 transition-all cursor-pointer disabled:opacity-50"
            >
              RESET 50 TRANSACTIONS
            </button>

            <button
              onClick={handleDemoRun}
              disabled={isDemoRunning}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#D79A43] hover:bg-[#F0B84B] text-[#070706] shadow-gold transition-all cursor-pointer disabled:opacity-50"
            >
              {isDemoRunning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>PROCESSING BATCH...</span>
                </>
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5 fill-current" />
                  <span>RUN RECOVERY BATCH</span>
                </>
              )}
            </button>
          </div>
        </div>

        {demoMessage && (
          <div className="mt-3 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs font-mono text-[#D79A43]">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{demoMessage}</span>
            </div>
            {demoStats && (
              <span className="text-[#918D84]">
                Analyzed: {demoStats.transactions_analyzed} • Recovered: {demoStats.transactions_recovered} • Blocked: {demoStats.transactions_blocked} • Approval Required: {demoStats.transactions_approval_required}
              </span>
            )}
          </div>
        )}

        {/* Guardrail Verification Proof Showcase */}
        <div className="mt-4 pt-4 border-t border-white/[0.08] space-y-2.5">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-[#918D84] uppercase tracking-wider font-bold">
              DETERMINISTIC POLICY GUARDRAIL PROOFS:
            </span>
            <span className="text-[#66625B]">Inspect policy decision, AI confidence & timeline</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
            {/* Guardrail A: ₹50k Approval */}
            <Link
              href={guardrailCases.case50k ? `/dashboard/recovery/cases/${guardrailCases.case50k}` : "/dashboard/recovery"}
              className="p-3.5 rounded-xl bg-[#141310] hover:bg-[#1C1A16] border border-[#D79A43]/30 hover:border-[#D79A43]/60 transition-all flex items-center justify-between group cursor-pointer"
            >
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#D79A43]" />
                  <span className="font-bold text-[#F5F0E8] text-xs">TXN-DEMO-035 • ₹50,000</span>
                </div>
                <p className="text-[10px] text-[#D79A43] font-bold">Rule 5: High-Value Gate (&gt; ₹25k)</p>
                <span className="text-[10px] text-[#918D84] block">Pending Approval → Verified Settle</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#918D84] group-hover:text-[#D79A43] transition-colors" />
            </Link>

            {/* Guardrail B: Stolen Card Block */}
            <Link
              href={guardrailCases.caseStolen ? `/dashboard/recovery/cases/${guardrailCases.caseStolen}` : "/dashboard/recovery"}
              className="p-3.5 rounded-xl bg-[#141310] hover:bg-[#1C1A16] border border-[#E56B6F]/30 hover:border-[#E56B6F]/60 transition-all flex items-center justify-between group cursor-pointer"
            >
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#E56B6F]" />
                  <span className="font-bold text-[#F5F0E8] text-xs">TXN-DEMO-039 • ₹12,000</span>
                </div>
                <p className="text-[10px] text-[#E56B6F] font-bold">Rule 2: Anti-Fraud Hard Decline</p>
                <span className="text-[10px] text-[#918D84] block">Blocked • 0 Retries Allowed</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#918D84] group-hover:text-[#E56B6F] transition-colors" />
            </Link>

            {/* Guardrail C: Stopping Rule */}
            <Link
              href={guardrailCases.caseStopped ? `/dashboard/recovery/cases/${guardrailCases.caseStopped}` : "/dashboard/recovery"}
              className="p-3.5 rounded-xl bg-[#141310] hover:bg-[#1C1A16] border border-[#F59E0B]/30 hover:border-[#F59E0B]/60 transition-all flex items-center justify-between group cursor-pointer"
            >
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#F59E0B]" />
                  <span className="font-bold text-[#F5F0E8] text-xs">TXN-DEMO-045 • ₹4,200</span>
                </div>
                <p className="text-[10px] text-[#F59E0B] font-bold">Rule 3: Maximum Retry Limit</p>
                <span className="text-[10px] text-[#918D84] block">Stopped • 3/3 Retries Reached</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#918D84] group-hover:text-[#F59E0B] transition-colors" />
            </Link>
          </div>
        </div>
      </motion.div>

      {/* 3. Core Metrics Strip */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Revenue at Risk */}
        <div className="lg:col-span-2">
          <MetricCard
            title="REVENUE AT RISK"
            value={kpis ? `${currencySymbol}${kpis.revenue_at_risk.toLocaleString()}` : `${currencySymbol}0`}
            subtitle="Eligible unrecovered volume"
            icon={AlertTriangle}
            variant="primary"
            isLoading={isLoading}
          />
        </div>

        {/* Verified Revenue Recovered */}
        <div className="lg:col-span-2">
          <MetricCard
            title="VERIFIED REVENUE RECOVERED"
            value={kpis ? `${currencySymbol}${kpis.revenue_recovered.toLocaleString()}` : `${currencySymbol}0`}
            subtitle="Captured & verified recovered funds"
            icon={Coins}
            variant="secondary"
            trend={
              kpis && kpis.recovery_rate_percentage !== null
                ? `${kpis.recovery_rate_percentage}% CONVERTED`
                : undefined
            }
            isLoading={isLoading}
          />
        </div>

        {/* Recovery Rate */}
        <div className="lg:col-span-1">
          <MetricCard
            title="RECOVERY RATE"
            value={kpis && kpis.recovery_rate_percentage !== null ? `${kpis.recovery_rate_percentage}%` : "—"}
            subtitle="Verified vs At Risk"
            icon={TrendingUp}
            isLoading={isLoading}
          />
        </div>

        {/* Active Cases / Escalations */}
        <div className="lg:col-span-1 flex flex-col justify-between gap-4">
          <MetricCard
            title="ACTIVE CASES"
            value={kpis ? kpis.active_recovery_cases : 0}
            icon={Clock}
            isLoading={isLoading}
          />
          <MetricCard
            title="ESCALATIONS"
            value={kpis ? kpis.human_escalations : 0}
            icon={ShieldAlert}
            isLoading={isLoading}
          />
        </div>
      </motion.div>

      {/* 3. Empty State for Fresh Organization */}
      {isEmptyWorkspace && (
        <motion.div
          variants={itemVariants}
          className="p-10 sm:p-14 rounded-3xl bg-[#11110F] border border-white/[0.08] text-center space-y-6 shadow-[0_16px_48px_rgba(0,0,0,0.6)] font-mono"
        >
          <div className="w-14 h-14 rounded-2xl bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43] mx-auto shadow-gold">
            <Zap className="w-7 h-7 fill-[#D79A43]" />
          </div>
          <div>
            <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#F5F0E8]">
              Your recovery intelligence starts here.
            </h2>
            <p className="text-xs text-[#918D84] mt-2 max-w-lg mx-auto">
              Connect a payment provider, import transaction history, or add your first transaction to begin automated revenue recovery.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto pt-2">
            <Link
              href="/dashboard/transactions/import"
              className="p-5 rounded-2xl bg-[#161614] border border-white/[0.08] hover:border-[#D79A43]/50 hover:bg-[#1C1C19] transition-all text-center group cursor-pointer"
            >
              <FileSpreadsheet className="w-5 h-5 text-[#D79A43] mx-auto mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-bold text-[#F5F0E8]">Import Transactions</div>
              <div className="text-[10px] text-[#66625B] mt-1">Upload CSV batch file</div>
            </Link>

            <Link
              href="/dashboard/transactions/new"
              className="p-5 rounded-2xl bg-[#161614] border border-white/[0.08] hover:border-[#D79A43]/50 hover:bg-[#1C1C19] transition-all text-center group cursor-pointer"
            >
              <PlusCircle className="w-5 h-5 text-[#D79A43] mx-auto mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-bold text-[#F5F0E8]">Add Transaction</div>
              <div className="text-[10px] text-[#66625B] mt-1">Manual entry test</div>
            </Link>

            <Link
              href="/dashboard/settings/integrations"
              className="p-5 rounded-2xl bg-[#161614] border border-white/[0.08] hover:border-[#D79A43]/50 hover:bg-[#1C1C19] transition-all text-center group cursor-pointer"
            >
              <CreditCard className="w-5 h-5 text-[#D79A43] mx-auto mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-bold text-[#F5F0E8]">Connect Data Source</div>
              <div className="text-[10px] text-[#66625B] mt-1">Payment Gateways & Webhooks</div>
            </Link>
          </div>
        </motion.div>
      )}

      {/* 4. Recovery Queue Summary & Data Sources */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-12 gap-5 font-mono text-xs">
        {/* Recovery Queue Breakdown (Clickable) */}
        <div className="lg:col-span-8 p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#D79A43]" />
              <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Recovery Pipeline Queue</h3>
            </div>
            <Link href="/dashboard/recovery" className="text-[11px] text-[#D79A43] hover:underline flex items-center gap-1">
              <span>View Recovery Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Link
              href="/dashboard/recovery?status=PENDING_APPROVAL"
              className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] hover:border-[#D79A43]/40 transition-colors"
            >
              <span className="text-[#918D84] text-[11px]">Awaiting Approval</span>
              <div className="font-sans font-bold text-lg text-[#D79A43] mt-1">
                {kpis?.queue_summary?.awaiting_approval || 0}
              </div>
            </Link>

            <Link
              href="/dashboard/recovery?status=ACTION_SCHEDULED"
              className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] hover:border-[#D79A43]/40 transition-colors"
            >
              <span className="text-[#918D84] text-[11px]">Action Scheduled</span>
              <div className="font-sans font-bold text-lg text-[#F5F0E8] mt-1">
                {kpis?.queue_summary?.action_scheduled || 0}
              </div>
            </Link>

            <Link
              href="/dashboard/recovery?status=IN_PROGRESS"
              className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] hover:border-[#D79A43]/40 transition-colors"
            >
              <span className="text-[#918D84] text-[11px]">In Progress</span>
              <div className="font-sans font-bold text-lg text-[#20B89A] mt-1">
                {kpis?.queue_summary?.in_progress || 0}
              </div>
            </Link>

            <Link
              href="/dashboard/recovery?status=ESCALATED"
              className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] hover:border-[#E56B6F]/40 transition-colors"
            >
              <span className="text-[#918D84] text-[11px]">Escalated</span>
              <div className="font-sans font-bold text-lg text-[#E56B6F] mt-1">
                {kpis?.queue_summary?.escalated || 0}
              </div>
            </Link>
          </div>
        </div>

        {/* Data Source & Ingestion Status */}
        <div className="lg:col-span-4 p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-[#20B89A]" />
              <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Data Sources</h3>
            </div>
            <Link href="/dashboard/settings/integrations" className="text-[11px] text-[#D79A43] hover:underline">
              Settings
            </Link>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[#918D84]">Payment Providers:</span>
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-bold ${
                  dataSources?.payment_providers?.connected ? "text-[#20B89A]" : "text-[#66625B]"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    dataSources?.payment_providers?.connected ? "bg-[#20B89A]" : "bg-[#66625B]"
                  }`}
                />
                {dataSources?.payment_providers?.connected
                  ? `Connected (${dataSources.payment_providers.providers.join(", ")})`
                  : "Not Connected"}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#918D84]">CSV Ingestion:</span>
              <span className="text-[#F5F0E8]">
                {dataSources?.csv_import?.last_import_at
                  ? new Date(dataSources.csv_import.last_import_at).toLocaleDateString()
                  : "Available"}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#918D84]">Manual Entry:</span>
              <span className="text-[#20B89A] font-bold">Available</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* 5. Revenue Trend & Recovery Funnel Charts */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 gap-6">
        <RevenueTrendChart data={chartsData || undefined} isLoading={isLoading} />
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecoveryFunnelChart data={chartsData || undefined} isLoading={isLoading} />
        <FailureReasonDistributionChart data={chartsData || undefined} isLoading={isLoading} />
      </motion.div>

      {/* 6. Top Opportunities & Recent Activity */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-12 gap-6 font-mono text-xs">
        {/* Top Recovery Opportunities */}
        <div className="lg:col-span-7 p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#D79A43]" />
              <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Top Recovery Opportunities</h3>
            </div>
            <Link href="/dashboard/recovery" className="text-[11px] text-[#D79A43] hover:underline">
              All Cases →
            </Link>
          </div>

          {topOpportunities.length === 0 ? (
            <div className="text-center py-10 text-[#66625B]">
              No active recovery opportunities at this time.
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {topOpportunities.map((opp) => (
                <div key={opp.case_id} className="py-3 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#F5F0E8]">
                        {currencySymbol}{opp.amount?.toLocaleString()}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-white/[0.05] text-[#918D84]">
                        {opp.status}
                      </span>
                      {opp.requires_approval && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#D79A43]/15 text-[#D79A43] font-bold">
                          Approval Required
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#918D84] truncate max-w-sm">{opp.strategy}</p>
                  </div>

                  <Link
                    href={`/dashboard/recovery/cases/${opp.case_id}`}
                    className="px-3 py-1.5 rounded-lg bg-[#141412] hover:bg-[#1A1917] border border-white/[0.08] text-[#D79A43] hover:border-[#D79A43]/40 flex items-center gap-1 shrink-0"
                  >
                    <span>Inspect</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live Recent Recovery Activity Feed */}
        <div className="lg:col-span-5 p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#20B89A]" />
              <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Recent Recovery Activity</h3>
            </div>
            <Link href="/dashboard/audit" className="text-[11px] text-[#D79A43] hover:underline">
              Ledger →
            </Link>
          </div>

          {recentActivity.length === 0 ? (
            <div className="text-center py-10 text-[#66625B]">
              No recovery activity recorded yet.
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((act) => (
                <div key={act.id} className="flex items-start gap-2.5 text-xs">
                  <div className="w-2 h-2 rounded-full bg-[#D79A43] mt-1.5 shrink-0" />
                  <div className="space-y-0.5 w-full">
                    <p className="text-[#F5F0E8] font-bold">{act.event_type}</p>
                    <p className="text-[11px] text-[#918D84]">{act.notes || "Action processed"}</p>
                    <span className="text-[10px] text-[#66625B]">
                      {act.timestamp ? new Date(act.timestamp).toLocaleTimeString() : "Just now"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {/* 7. Transaction Volume Summary Banner */}
      <motion.div
        variants={itemVariants}
        className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono text-xs"
      >
        <div className="space-y-1">
          <h4 className="font-sans font-bold text-sm text-[#F5F0E8]">Transaction Volume Summary</h4>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-[#918D84]">
            <span>Total: <strong className="text-[#F5F0E8]">{kpis?.transaction_summary?.total || 0}</strong></span>
            <span>•</span>
            <span>Successful: <strong className="text-[#20B89A]">{kpis?.transaction_summary?.successful || 0}</strong></span>
            <span>•</span>
            <span>Failed: <strong className="text-[#E56B6F]">{kpis?.transaction_summary?.failed || 0}</strong></span>
            <span>•</span>
            <span>Recovered: <strong className="text-[#D79A43]">{kpis?.transaction_summary?.recovered || 0}</strong></span>
          </div>
        </div>

        <Link
          href="/dashboard/transactions"
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#141412] hover:bg-[#1A1917] border border-white/[0.08] text-[#D79A43] hover:border-[#D79A43]/40 self-start sm:self-center"
        >
          <span>View All Transactions</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </motion.div>
    </motion.div>
  );
}
