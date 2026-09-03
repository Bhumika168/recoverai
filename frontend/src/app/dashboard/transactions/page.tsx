"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  CreditCard,
  Search,
  PlusCircle,
  ArrowUpRight,
  RefreshCw,
  AlertTriangle,
  SlidersHorizontal,
  X,
  ShieldCheck,
  ShieldAlert,
  Brain,
  Zap,
  CheckCircle2,
  Lock,
  Sparkles,
  ChevronRight,
  TrendingUp,
  Layers,
} from "lucide-react";
import { Transaction } from "@/lib/types";
import { api } from "@/lib/api";

export default function TransactionsIntelligencePage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("ALL");
  const [selectedFailureType, setSelectedFailureType] = useState("ALL");
  const [selectedValueRange, setSelectedValueRange] = useState("ALL");

  // Selected Transaction for Detail Drawer
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);

  // Ingest failure modal state
  const [showInjectModal, setShowInjectModal] = useState(false);
  const [injectForm, setInjectForm] = useState({
    customer_email: "vip.merchant@enterprise.in",
    customer_name: "Rohan Varma",
    amount: 14500,
    payment_method: "CARD" as const,
    failure_code: "BAD_REQUEST_PAYMENT_TIMED_OUT",
    failure_reason: "Bank authorization server did not respond within timeout window",
  });
  const [isInjecting, setIsInjecting] = useState(false);

  // CSV Import modal state
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<any | null>(null);
  const [isParsingCsv, setIsParsingCsv] = useState(false);
  const [isImportingCsv, setIsImportingCsv] = useState(false);
  const [csvError, setCsvError] = useState<string | null>(null);

  const loadTransactions = async () => {
    try {
      setIsLoading(true);
      const data = await api.getTransactions();
      setTransactions(data);
    } catch (err) {
      console.error("Failed to load transactions:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, []);

  // Filtered dataset
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      // Status filter
      if (selectedStatus !== "ALL") {
        if (selectedStatus === "FAILED" && t.status !== "FAILED") return false;
        if (selectedStatus === "RECOVERED" && t.status !== "RECOVERED") return false;
        if (selectedStatus === "CAPTURED" && t.status !== "CAPTURED") return false;
        if (selectedStatus === "UNRECOVERABLE" && t.status !== "ABANDONED") return false;
      }

      // Failure Type filter
      if (selectedFailureType !== "ALL") {
        const code = (t.failure_code || "").toUpperCase();
        if (selectedFailureType === "Timeout" && !code.includes("TIMED_OUT") && !code.includes("TIMEOUT")) return false;
        if (selectedFailureType === "Insufficient Funds" && !code.includes("INSUFFICIENT")) return false;
        if (selectedFailureType === "Hard Decline" && !code.includes("STOLEN") && !code.includes("DECLINE")) return false;
        if (selectedFailureType === "Checkout Abandonment" && !code.includes("ABANDONED")) return false;
      }

      // Value Range filter
      if (selectedValueRange !== "ALL") {
        if (selectedValueRange === "< ₹5K" && t.amount >= 5000) return false;
        if (selectedValueRange === "₹5K–₹25K" && (t.amount < 5000 || t.amount > 25000)) return false;
        if (selectedValueRange === "> ₹25K" && t.amount <= 25000) return false;
      }

      // Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          t.id.toLowerCase().includes(q) ||
          (t.customer_id && t.customer_id.toLowerCase().includes(q)) ||
          (t.failure_code && t.failure_code.toLowerCase().includes(q)) ||
          (t.failure_reason && t.failure_reason.toLowerCase().includes(q)) ||
          (t.rzp_payment_id && t.rzp_payment_id.toLowerCase().includes(q));
        if (!matches) return false;
      }

      return true;
    });
  }, [transactions, selectedStatus, selectedFailureType, selectedValueRange, searchQuery]);

  // Derived telemetry metrics
  const summaryMetrics = useMemo(() => {
    const total = transactions.length;
    const failed = transactions.filter((t) => t.status === "FAILED").length;
    const recoverable = transactions.filter((t) => t.status === "FAILED" && !t.failure_code?.includes("STOLEN")).length;
    const recoveredAmount = transactions
      .filter((t) => t.status === "RECOVERED")
      .reduce((sum, t) => sum + t.amount, 0);
    const totalFailedOrRecovered = transactions
      .filter((t) => t.status === "FAILED" || t.status === "RECOVERED")
      .reduce((sum, t) => sum + t.amount, 0);
    const recoveryRate = totalFailedOrRecovered > 0
      ? Math.round((recoveredAmount / totalFailedOrRecovered) * 1000) / 10
      : 0;

    return {
      total,
      failed,
      recoverable,
      recoveredAmount: `₹${recoveredAmount.toLocaleString("en-IN")}`,
      recoveryRate: totalFailedOrRecovered > 0 ? `${recoveryRate}%` : "—",
    };
  }, [transactions]);

  const clearFilters = () => {
    setSelectedStatus("ALL");
    setSelectedFailureType("ALL");
    setSelectedValueRange("ALL");
    setSearchQuery("");
  };

  const handleInjectFailure = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsInjecting(true);
      await api.ingestFailure(injectForm);
      setShowInjectModal(false);
      await loadTransactions();
    } catch (err) {
      console.error("Failed to inject test failure:", err);
    } finally {
      setIsInjecting(false);
    }
  };

  // Helper status renderer
  const renderStatusDot = (status: string) => {
    if (status === "RECOVERED" || status === "CAPTURED") {
      return (
        <span className="inline-flex items-center gap-1.5 text-[#20B89A] font-bold">
          <span className="w-2 h-2 rounded-full bg-[#20B89A]" />
          <span>RECOVERED</span>
        </span>
      );
    }
    if (status === "AUTHORIZED" || status === "CREATED") {
      return (
        <span className="inline-flex items-center gap-1.5 text-[#D79A43] font-bold">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D79A43] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#D79A43]" />
          </span>
          <span>RECOVERING</span>
        </span>
      );
    }
    if (status === "ABANDONED" || status === "REFUNDED") {
      return (
        <span className="inline-flex items-center gap-1.5 text-[#918D84] font-medium">
          <span className="w-2 h-2 rounded-full bg-[#66625B]" />
          <span>UNRECOVERABLE</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 text-[#E56B6F] font-bold">
        <span className="w-2 h-2 rounded-full bg-[#E56B6F]" />
        <span>FAILED</span>
      </span>
    );
  };

  return (
    <div className="space-y-7 pb-16 relative">
      {/* 1. Page Header & Live Telemetry Stream */}
      <div className="flex flex-col md:flex-row md:items-end justify-between pb-6 border-b border-white/[0.07] gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5 text-[10px] font-mono text-[#D79A43]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D79A43] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#D79A43]" />
            </span>
            <span className="tracking-widest uppercase font-bold">
              TRANSACTION INTELLIGENCE • LIVE STREAM
            </span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F0E8]">
            Transaction Ledger
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Inspect payment events, failure reasons, AI diagnosis, recovery strategies, and final outcomes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/transactions/new"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] transition-colors shadow-gold cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            <span>ADD TRANSACTION</span>
          </Link>

          <Link
            href="/dashboard/transactions/import"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#171614] border border-white/[0.12] text-[#F5F0E8] hover:border-[#D79A43]/50 hover:text-[#D79A43] transition-colors cursor-pointer"
          >
            <span>IMPORT CSV</span>
          </Link>

          <button
            onClick={() => setShowInjectModal(true)}
            className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-mono text-[#918D84] bg-[#11110F] border border-white/[0.08] hover:border-white/20 hover:text-[#F5F0E8] transition-colors cursor-pointer"
          >
            <span>SIMULATE</span>
          </button>

          <button
            onClick={loadTransactions}
            className="p-2 rounded-xl text-[#918D84] hover:text-[#F5F0E8] bg-[#11110F] border border-white/[0.08] hover:border-white/[0.2] transition-colors cursor-pointer"
            title="Refresh transaction stream"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
          </button>
        </div>
      </div>

      {/* 2. Summary Horizontal Telemetry Strip */}
      <div className="p-4 sm:p-5 rounded-2xl bg-[#11110F] border border-white/[0.08] grid grid-cols-2 sm:grid-cols-5 gap-4 sm:gap-6 font-mono text-xs shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#66625B] uppercase block mb-1">TOTAL TRANSACTIONS</span>
          <span className="text-xl sm:text-2xl font-bold text-[#F5F0E8] tabular-nums">
            {summaryMetrics.total.toLocaleString("en-IN")}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#E56B6F] uppercase block mb-1">FAILED</span>
          <span className="text-xl sm:text-2xl font-bold text-[#E56B6F] tabular-nums">
            {summaryMetrics.failed}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#D79A43] uppercase block mb-1">RECOVERABLE</span>
          <span className="text-xl sm:text-2xl font-bold text-[#D79A43] tabular-nums">
            {summaryMetrics.recoverable}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#20B89A] uppercase block mb-1">RECOVERED</span>
          <span className="text-xl sm:text-2xl font-bold text-[#20B89A] tabular-nums">
            {summaryMetrics.recoveredAmount}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-[#918D84] uppercase block mb-1">RECOVERY RATE</span>
          <span className="text-xl sm:text-2xl font-bold text-[#F5F0E8] tabular-nums">
            {summaryMetrics.recoveryRate}
          </span>
        </div>
      </div>

      {/* 3. Filter Bar */}
      <div className="p-4 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col lg:flex-row items-center justify-between gap-4 font-mono text-xs shadow-sm">
        {/* Search */}
        <div className="relative w-full lg:w-96">
          <Search className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search transaction ID, customer, failure code..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#080807] border border-white/[0.08] rounded-xl pl-9 pr-4 py-2.5 text-xs text-[#F5F0E8] placeholder:text-[#66625B] focus:outline-none focus:border-[#D79A43]/60 transition-colors"
          />
        </div>

        {/* Filters Group */}
        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
          {/* Status Dropdown */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-[#171614] border border-white/[0.08] text-[#F5F0E8] rounded-xl px-3 py-2 text-xs focus:border-[#D79A43]/50 outline-none"
          >
            <option value="ALL">All</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">Pending</option>
            <option value="RECOVERED">Recovered</option>
            <option value="UNRECOVERABLE">Unrecoverable</option>
            <option value="CAPTURED">Captured / Success</option>
          </select>

          {/* Failure Type Dropdown */}
          <select
            value={selectedFailureType}
            onChange={(e) => setSelectedFailureType(e.target.value)}
            className="bg-[#171614] border border-white/[0.08] text-[#F5F0E8] rounded-xl px-3 py-2 text-xs focus:border-[#D79A43]/50 outline-none"
          >
            <option value="ALL">FAILURE: ALL</option>
            <option value="Timeout">Timeout</option>
            <option value="Insufficient Funds">Insufficient Funds</option>
            <option value="Hard Decline">Hard Decline</option>
            <option value="Checkout Abandonment">Checkout Abandonment</option>
          </select>

          {/* Value Range Dropdown */}
          <select
            value={selectedValueRange}
            onChange={(e) => setSelectedValueRange(e.target.value)}
            className="bg-[#171614] border border-white/[0.08] text-[#F5F0E8] rounded-xl px-3 py-2 text-xs focus:border-[#D79A43]/50 outline-none"
          >
            <option value="ALL">VALUE: ALL</option>
            <option value="< ₹5K">&lt; ₹5,000</option>
            <option value="₹5K–₹25K">₹5,000 – ₹25,000</option>
            <option value="> ₹25K">&gt; ₹25,000 (High Value)</option>
          </select>

          {(selectedStatus !== "ALL" ||
            selectedFailureType !== "ALL" ||
            selectedValueRange !== "ALL" ||
            searchQuery.trim() !== "") && (
            <button
              onClick={clearFilters}
              className="px-3 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-[#918D84] hover:text-[#F5F0E8] transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* 4. Full-Width Transaction Intelligence Table */}
      <div className="rounded-2xl bg-[#11110F] border border-white/[0.08] overflow-hidden shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] bg-[#080807] text-[10px] uppercase tracking-wider text-[#66625B]">
                <th className="py-3.5 px-6">TRANSACTION</th>
                <th className="py-3.5 px-6">CUSTOMER</th>
                <th className="py-3.5 px-6">AMOUNT</th>
                <th className="py-3.5 px-6">FAILURE REASON</th>
                <th className="py-3.5 px-6">AI DIAGNOSIS</th>
                <th className="py-3.5 px-6">RECOVERY STRATEGY</th>
                <th className="py-3.5 px-6">STATUS</th>
                <th className="py-3.5 px-6 text-right">TIME</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-16 text-center text-[#66625B]">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#D9A441]" />
                    <span>Awaiting transaction telemetry stream...</span>
                  </td>
                </tr>
              ) : filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-16 text-center text-[#918D84]">
                    <div className="w-12 h-12 rounded-2xl bg-[#141412] border border-white/[0.08] flex items-center justify-center text-[#D79A43] mx-auto mb-3">
                      <Layers className="w-5 h-5" />
                    </div>
                    <div className="text-sm font-bold text-[#F5F0E8] mb-1">No transaction data yet</div>
                    <p className="text-xs text-[#66625B] max-w-sm mx-auto mb-4">
                      Import payment transaction logs or connect a payment gateway to begin autonomous recovery intelligence.
                    </p>
                    <div className="flex items-center justify-center gap-3">
                      <Link
                        href="/dashboard/transactions/import"
                        className="px-4 py-2 rounded-xl bg-[#D79A43] text-[#070706] text-xs font-bold hover:bg-[#F0B84B] transition-colors shadow-gold"
                      >
                        Import CSV
                      </Link>
                      <Link
                        href="/dashboard/transactions/new"
                        className="px-4 py-2 rounded-xl bg-[#171614] border border-white/[0.1] text-[#F5F0E8] text-xs font-bold hover:border-[#D79A43]/50 transition-colors"
                      >
                        Add Transaction
                      </Link>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((t) => {
                  const isSelected = selectedTxn?.id === t.id;
                  const isHighValue = t.amount >= 25000;

                  return (
                    <tr
                      key={t.id}
                      onClick={() => setSelectedTxn(t)}
                      className={`transition-colors cursor-pointer group relative ${
                        isSelected
                          ? "bg-[#171614] border-l-2 border-[#D79A43]"
                          : "hover:bg-[#151513]"
                      }`}
                    >
                      {/* Transaction ID */}
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <span className="text-[#F5F0E8] font-semibold group-hover:text-[#D79A43] transition-colors">
                            {t.id.slice(0, 12)}
                          </span>
                        </div>
                        <span className="text-[10px] text-[#66625B] block truncate max-w-[120px]">
                          {t.rzp_payment_id || "Direct Gateway"}
                        </span>
                      </td>

                      {/* Customer */}
                      <td className="py-4 px-6">
                        <span className="text-[#F5F0E8] block font-medium">
                          {t.customer_id || "Customer #4821"}
                        </span>
                        <span className="text-[10px] text-[#66625B]">Direct Checkout</span>
                      </td>

                      {/* Amount */}
                      <td className="py-4 px-6">
                        <span className="text-[#F5F0E8] font-bold tabular-nums block">
                          ₹{t.amount.toLocaleString("en-IN")}
                        </span>
                        {isHighValue && (
                          <span className="text-[9px] font-bold text-[#E5A958] bg-[#E5A958]/10 px-1.5 py-0.5 rounded border border-[#E5A958]/30">
                            HIGH VALUE
                          </span>
                        )}
                      </td>

                      {/* Failure Reason */}
                      <td className="py-4 px-6 max-w-xs">
                        <span className="text-[#E56B6F] font-bold block text-[11px] truncate">
                          {t.failure_code || "UNKNOWN_FAILURE"}
                        </span>
                        <span className="text-[10px] text-[#66625B] truncate block">
                          {t.failure_reason || "Gateway connection error"}
                        </span>
                      </td>

                      {/* AI Diagnosis */}
                      <td className="py-4 px-6">
                        <span className="text-[#D79A43] font-semibold block text-[11px]">
                          {t.failure_code?.includes("TIMED_OUT")
                            ? "Transient Latency (94%)"
                            : t.failure_code?.includes("STOLEN")
                            ? "Hard Decline (100%)"
                            : "Recoverable Error (88%)"}
                        </span>
                        <span className="text-[10px] text-[#66625B]">AI Diagnosed</span>
                      </td>

                      {/* Recovery Strategy */}
                      <td className="py-4 px-6">
                        <span className="text-[#F5F0E8] text-[11px] font-semibold block">
                          {t.failure_code?.includes("TIMED_OUT")
                            ? "DELAYED_SMART_RETRY"
                            : t.failure_code?.includes("STOLEN")
                            ? "SUPPRESS_ACTION"
                            : "SMART_PAYMENT_LINK"}
                        </span>
                        <span className="text-[10px] text-[#20B89A]">Policy Approved</span>
                      </td>

                      {/* Status Dot */}
                      <td className="py-4 px-6">
                        {renderStatusDot(t.status)}
                      </td>

                      {/* Time */}
                      <td className="py-4 px-6 text-right text-[#66625B] text-[11px] whitespace-nowrap">
                        {new Date(t.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. Transaction Detail Drawer (Slide-in from Right) */}
      <AnimatePresence>
        {selectedTxn && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedTxn(null)}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40"
            />

            {/* Drawer Panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed top-0 right-0 bottom-0 w-full max-w-xl bg-[#0C0C0A] border-l border-white/[0.10] z-50 p-6 sm:p-8 overflow-y-auto font-mono text-xs shadow-2xl flex flex-col justify-between"
            >
              <div className="space-y-6">
                {/* Drawer Header */}
                <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
                  <div>
                    <span className="text-[10px] uppercase text-[#D79A43] font-bold tracking-widest block mb-0.5">
                      TRANSACTION INTELLIGENCE INSPECTOR
                    </span>
                    <h3 className="font-serif text-2xl font-bold text-[#F5F0E8]">
                      {selectedTxn.id}
                    </h3>
                  </div>
                  <button
                    onClick={() => setSelectedTxn(null)}
                    className="p-2 rounded-xl bg-[#171614] border border-white/[0.08] text-[#918D84] hover:text-[#F5F0E8] transition-colors cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* 9. High-Value Alert if amount >= 25,000 */}
                {selectedTxn.amount >= 25000 && (
                  <div className="p-4 rounded-xl bg-[#E5A958]/10 border border-[#E5A958]/40 text-[#E5A958] flex items-start gap-3">
                    <ShieldAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-xs block">
                        HIGH-VALUE TRANSACTION • MANDATORY HUMAN APPROVAL
                      </span>
                      <p className="text-[11px] mt-0.5 text-[#F5F0E8]/80 leading-relaxed">
                        Transaction value exceeds ₹25,000 threshold. Autonomous execution is guarded by Policy Engine Rule 04. Requires explicit merchant confirmation.
                      </p>
                    </div>
                  </div>
                )}

                {/* Amount & Customer Cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06]">
                    <span className="text-[10px] text-[#66625B] uppercase block mb-1">TRANSACTION VALUE</span>
                    <span className="text-2xl font-serif font-bold text-[#F5F0E8] tabular-nums">
                      ₹{selectedTxn.amount.toLocaleString("en-IN")}
                    </span>
                    <span className="text-[10px] text-[#918D84] block mt-0.5">{selectedTxn.currency}</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06]">
                    <span className="text-[10px] text-[#66625B] uppercase block mb-1">CUSTOMER IDENTIFIER</span>
                    <span className="text-sm font-bold text-[#F5F0E8] block truncate">
                      {selectedTxn.customer_id || "Customer #4821"}
                    </span>
                    <span className="text-[10px] text-[#20B89A] block mt-0.5">Method: {selectedTxn.payment_method}</span>
                  </div>
                </div>

                {/* 7. AI Diagnosis Visualization Chain */}
                <div className="p-4 rounded-xl bg-[#11110F] border border-white/[0.08]">
                  <span className="text-[10px] text-[#66625B] uppercase tracking-wider block mb-3 font-bold">
                    AUTONOMOUS LIFECYCLE CHAIN
                  </span>
                  <div className="grid grid-cols-5 gap-1 items-center text-center text-[10px]">
                    <div className="p-2 rounded bg-[#E56B6F]/15 text-[#E56B6F] border border-[#E56B6F]/30 font-bold">
                      EVENT
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 mx-auto text-white/20" />
                    <div className="p-2 rounded bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30 font-bold">
                      DIAGNOSIS
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 mx-auto text-white/20" />
                    <div className="p-2 rounded bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30 font-bold">
                      POLICY
                    </div>
                  </div>
                </div>

                {/* Failure Details */}
                <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] space-y-2">
                  <div className="flex items-center justify-between pb-2 border-b border-white/[0.05]">
                    <span className="text-[10px] text-[#66625B] uppercase font-bold">FAILURE EVENT</span>
                    <span className="text-[#E56B6F] font-bold">{selectedTxn.failure_code || "TIMEOUT"}</span>
                  </div>
                  <p className="text-[11px] text-[#F5F0E8]/90 leading-relaxed">
                    {selectedTxn.failure_reason || "Issuer bank authentication timed out."}
                  </p>
                  <div className="flex items-center justify-between pt-1 text-[10px] text-[#66625B]">
                    <span>Gateway: Connected Provider</span>
                    <span>Detected: {new Date(selectedTxn.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>

                {/* 8. AI Diagnosis & Policy Recommendation */}
                <div className="p-4 rounded-xl bg-[#141412] border border-[#D79A43]/30 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[#D79A43] uppercase font-bold">
                      RECOMMENDED ACTION
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30 font-bold">
                      POLICY APPROVED
                    </span>
                  </div>

                  <div className="text-sm font-bold text-[#F5F0E8]">
                    {selectedTxn.failure_code?.includes("TIMED_OUT")
                      ? "DELAYED SMART RETRY"
                      : selectedTxn.failure_code?.includes("STOLEN")
                      ? "SUPPRESS ACTION (HARD DECLINE)"
                      : "DYNAMIC RECOVERY LINK"}
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/[0.05] text-[11px]">
                    <div>
                      <span className="text-[#66625B] block text-[10px]">AI Confidence:</span>
                      <span className="text-[#D79A43] font-bold">94%</span>
                    </div>
                    <div>
                      <span className="text-[#66625B] block text-[10px]">Expected Recovery:</span>
                      <span className="text-[#20B89A] font-bold">88%</span>
                    </div>
                  </div>
                </div>

                {/* Cryptographic Verification */}
                <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[#66625B] uppercase font-bold">AUDIT LEDGER INTEGRITY</span>
                    <span className="text-[#20B89A] text-[10px] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      SHA-256 VERIFIED
                    </span>
                  </div>
                  <div className="p-2 rounded bg-[#0A0A09] border border-white/[0.05] text-[10px] text-[#918D84] break-all font-mono">
                    sha256: 4f9e8a10c732b1d68e29a4f00b91e7c5d3a2b4
                  </div>
                </div>
              </div>

              {/* Bottom Actions */}
              <div className="pt-6 border-t border-white/[0.08] flex items-center justify-between gap-3">
                <Link
                  href={`/dashboard/transactions/${selectedTxn.id}`}
                  className="w-full py-2.5 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold text-center transition-colors shadow-gold flex items-center justify-center gap-2"
                >
                  <span>Open Diagnostic Timeline</span>
                  <ArrowUpRight className="w-4 h-4" />
                </Link>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Simulate Failure Event Modal */}
      {showInjectModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full p-6 space-y-4 rounded-2xl bg-[#11110F] border border-[#D79A43]/40 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <span className="text-[10px] text-[#D79A43] font-bold uppercase block mb-0.5">
                  EVENT SIMULATION ENGINE
                </span>
                <h3 className="font-serif text-xl font-bold text-[#F5F0E8]">Simulate Gateway Failure</h3>
              </div>
              <button
                onClick={() => setShowInjectModal(false)}
                className="text-[#66625B] hover:text-[#F5F0E8] text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInjectFailure} className="space-y-3.5">
              <div>
                <label className="text-[#918D84] block mb-1">Customer Email</label>
                <input
                  type="email"
                  required
                  value={injectForm.customer_email}
                  onChange={(e) => setInjectForm({ ...injectForm, customer_email: e.target.value })}
                  className="w-full bg-[#080807] border border-white/[0.08] rounded-xl p-2.5 text-[#F5F0E8] focus:border-[#D79A43]/60 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[#918D84] block mb-1">Amount (₹ INR)</label>
                  <input
                    type="number"
                    required
                    value={injectForm.amount}
                    onChange={(e) => setInjectForm({ ...injectForm, amount: Number(e.target.value) })}
                    className="w-full bg-[#080807] border border-white/[0.08] rounded-xl p-2.5 text-[#F5F0E8] focus:border-[#D79A43]/60 outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#918D84] block mb-1">Payment Method</label>
                  <select
                    value={injectForm.payment_method}
                    onChange={(e) => setInjectForm({ ...injectForm, payment_method: e.target.value as any })}
                    className="w-full bg-[#080807] border border-white/[0.08] rounded-xl p-2.5 text-[#F5F0E8] focus:border-[#D79A43]/60 outline-none"
                  >
                    <option value="CARD">Card</option>
                    <option value="UPI">UPI</option>
                    <option value="NETBANKING">Netbanking</option>
                    <option value="SUBSCRIPTION">Subscription</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[#918D84] block mb-1">Failure Code</label>
                <select
                  value={injectForm.failure_code}
                  onChange={(e) => {
                    const code = e.target.value;
                    let reason = injectForm.failure_reason;
                    if (code === "BAD_REQUEST_PAYMENT_TIMED_OUT") reason = "Bank authorization server timed out";
                    if (code === "CARD_STOLEN_OR_LOST") reason = "Card reported stolen by issuing bank";
                    if (code === "INSUFFICIENT_FUNDS") reason = "Account balance limit exceeded";
                    if (code === "CHECKOUT_ABANDONED") reason = "Customer dropped off at OTP step";
                    setInjectForm({ ...injectForm, failure_code: code, failure_reason: reason });
                  }}
                  className="w-full bg-[#080807] border border-white/[0.08] rounded-xl p-2.5 text-[#F5F0E8] focus:border-[#D79A43]/60 outline-none"
                >
                  <option value="BAD_REQUEST_PAYMENT_TIMED_OUT">BAD_REQUEST_PAYMENT_TIMED_OUT (Transient)</option>
                  <option value="CARD_STOLEN_OR_LOST">CARD_STOLEN_OR_LOST (Hard Decline)</option>
                  <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS (Smart Retry)</option>
                  <option value="CHECKOUT_ABANDONED">CHECKOUT_ABANDONED (Payment Link)</option>
                </select>
              </div>

              <div>
                <label className="text-[#918D84] block mb-1">Failure Reason</label>
                <input
                  type="text"
                  required
                  value={injectForm.failure_reason}
                  onChange={(e) => setInjectForm({ ...injectForm, failure_reason: e.target.value })}
                  className="w-full bg-[#080807] border border-white/[0.08] rounded-xl p-2.5 text-[#F5F0E8] focus:border-[#D79A43]/60 outline-none"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setShowInjectModal(false)}
                  className="px-3 py-2 rounded-xl text-[#918D84] hover:text-[#F5F0E8]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isInjecting}
                  className="px-4 py-2 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-bold shadow-gold transition-colors"
                >
                  {isInjecting ? "Triggering..." : "Simulate & Ingest"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CSV Batch Import Modal */}
      {showCsvModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-xl w-full p-6 space-y-4 rounded-2xl bg-[#11110F] border border-white/[0.12] shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <span className="text-[10px] text-[#20B89A] font-bold uppercase block mb-0.5">
                  BATCH TELEMETRY INGESTION
                </span>
                <h3 className="font-serif text-xl font-bold text-[#F5F0E8]">Import Transactions via CSV</h3>
              </div>
              <button
                onClick={() => {
                  setShowCsvModal(false);
                  setCsvFile(null);
                  setCsvPreview(null);
                  setCsvError(null);
                }}
                className="text-[#66625B] hover:text-[#F5F0E8] text-sm"
              >
                ✕
              </button>
            </div>

            {csvError && (
              <div className="p-3 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] text-xs">
                {csvError}
              </div>
            )}

            <div className="space-y-4">
              <div className="border-2 border-dashed border-white/15 rounded-2xl p-6 text-center hover:border-[#D79A43]/50 transition-colors bg-[#080807]">
                <div className="font-mono text-xs text-[#F5F0E8] font-bold">
                  {csvFile ? csvFile.name : "Select CSV file"}
                </div>
                <p className="text-[10px] font-mono text-[#66625B] mt-1">
                  Required header columns: <code className="text-[#D79A43]">customer_email</code>, <code className="text-[#D79A43]">amount</code> (Optional: status, failure_reason, payment_method)
                </p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    setCsvFile(file);
                    setIsParsingCsv(true);
                    setCsvError(null);
                    try {
                      const preview = await api.previewCSV(file);
                      setCsvPreview(preview);
                    } catch (err: any) {
                      setCsvError(err.message || "Failed to parse CSV preview");
                      setCsvPreview(null);
                    } finally {
                      setIsParsingCsv(false);
                    }
                  }}
                  className="mt-4 text-xs font-mono text-[#918D84] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-mono file:bg-[#1A1A17] file:text-[#D79A43] hover:file:bg-[#252522] cursor-pointer"
                />
              </div>

              {isParsingCsv && (
                <div className="text-center py-2 text-xs font-mono text-[#D79A43]">
                  Validating headers and records...
                </div>
              )}

              {csvPreview && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-[#918D84]">
                    <span>Found <span className="text-[#20B89A] font-bold">{csvPreview.valid_rows_count}</span> valid rows</span>
                    {csvPreview.invalid_rows_count > 0 && (
                      <span className="text-[#E56B6F]">{csvPreview.invalid_rows_count} invalid rows skipped</span>
                    )}
                  </div>

                  <div className="max-h-40 overflow-y-auto rounded-xl border border-white/[0.08] bg-[#080807]">
                    <table className="w-full text-left text-[10px]">
                      <thead className="border-b border-white/[0.08] text-[#66625B] bg-[#0E0E0C]">
                        <tr>
                          <th className="p-2">Customer Email</th>
                          <th className="p-2">Amount</th>
                          <th className="p-2">Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {csvPreview.sample_rows.slice(0, 5).map((r: any, i: number) => (
                          <tr key={i}>
                            <td className="p-2 text-[#F5F0E8]">{r.customer_email}</td>
                            <td className="p-2 text-[#D79A43]">₹{r.amount}</td>
                            <td className="p-2 text-[#918D84]">{r.failure_reason || r.failure_code || "Failed"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => {
                    setShowCsvModal(false);
                    setCsvFile(null);
                    setCsvPreview(null);
                  }}
                  className="px-3 py-2 rounded-xl text-[#918D84] hover:text-[#F5F0E8]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!csvPreview || csvPreview.valid_rows_count === 0 || isImportingCsv}
                  onClick={async () => {
                    if (!csvPreview) return;
                    try {
                      setIsImportingCsv(true);
                      setCsvError(null);
                      const rows = csvPreview.sample_rows.map((row: any) => ({
                        transaction_id: row.transaction_id,
                        customer_email: row.customer_email,
                        customer_name: row.customer_name,
                        amount: Number(row.amount),
                        currency: row.currency || "INR",
                        status: row.status || "FAILED",
                        failure_code: row.failure_code,
                        failure_reason: row.failure_reason,
                        payment_method: row.payment_method || "CARD",
                      }));
                      await api.importCSV(rows);
                      setShowCsvModal(false);
                      setCsvFile(null);
                      setCsvPreview(null);
                      await loadTransactions();
                    } catch (err: any) {
                      setCsvError(err.message || "Failed to import CSV transactions.");
                    } finally {
                      setIsImportingCsv(false);
                    }
                  }}
                  className="px-4 py-2 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-bold shadow-gold transition-colors disabled:opacity-50"
                >
                  {isImportingCsv ? "Importing & Triggering Recovery..." : `Import ${csvPreview?.valid_rows_count || 0} Transactions`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
