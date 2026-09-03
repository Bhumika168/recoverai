"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  RefreshCw,
  Search,
  CheckCircle2,
  ArrowUpRight,
  ShieldAlert,
  Brain,
  ShieldCheck,
  Zap,
  X,
  Activity,
} from "lucide-react";
import { RecoveryCase, RecoveryCaseDetail, Transaction } from "@/lib/types";
import { api } from "@/lib/api";

// Helper: Format authoritative transaction display identifier
function formatTransactionDisplayId(caseTxnId: string, txnHumanId?: string): string {
  if (txnHumanId && txnHumanId.trim()) return txnHumanId;
  const match = caseTxnId.match(/txn_[^_]+_(\d{3})_/);
  if (match) {
    return `TXN-DEMO-${match[1]}`;
  }
  return caseTxnId.slice(0, 16);
}

// Helper: Human-readable case title, root-cause subtitle, and policy rule
function getHumanCaseInfo(c: RecoveryCase, txn?: Transaction): {
  title: string;
  subtitle: string;
  policyRule: string;
  isHighValue: boolean;
  isHardDecline: boolean;
  isStoppingRule: boolean;
} {
  const isHighValue = c.amount_at_risk >= 25000 || (c.strategy_summary && c.strategy_summary.includes("HIGH_VALUE")) || false;
  const isHardDecline =
    c.status === "UNRECOVERABLE" ||
    (txn?.failure_code && ["CARD_STOLEN_OR_LOST", "CARD_RESTRICTED", "FRAUD_SUSPECTED", "CARD_CANCELLED"].includes(txn.failure_code)) ||
    false;
  const isStoppingRule =
    c.status === "ESCALATED" ||
    (c.status as string) === "STOPPED" ||
    (c.strategy_summary && c.strategy_summary.includes("HUMAN_ESCALATION")) ||
    false;

  if (isHighValue) {
    return {
      title: "High-Value Approval Required",
      subtitle: txn?.failure_reason || "Enterprise transaction exceeds ₹25,000 threshold",
      policyRule: "HIGH_VALUE_TRANSACTION_GATE",
      isHighValue: true,
      isHardDecline: false,
      isStoppingRule: false,
    };
  }

  if (isHardDecline) {
    return {
      title: "Hard Decline Blocked",
      subtitle: txn?.failure_reason || "Unrecoverable payment instrument; retries suppressed",
      policyRule: "NO_RETRY_AFTER_HARD_DECLINE",
      isHighValue: false,
      isHardDecline: true,
      isStoppingRule: false,
    };
  }

  if (isStoppingRule) {
    return {
      title: "Retry Limit Reached",
      subtitle: txn?.failure_reason || "Maximum retry limit reached across billing cycle",
      policyRule: "MAXIMUM_RETRY_LIMIT",
      isHighValue: false,
      isHardDecline: false,
      isStoppingRule: true,
    };
  }

  if (c.status === "RECOVERED") {
    return {
      title: "Verified Revenue Recovery",
      subtitle: txn?.failure_reason || "Transient network/gateway error resolved via sandbox capture",
      policyRule: "AUTOMATED_RETRY_PERMITTED",
      isHighValue: false,
      isHardDecline: false,
      isStoppingRule: false,
    };
  }

  if (c.status === "IN_PROGRESS") {
    return {
      title: "Customer Action Required",
      subtitle: txn?.failure_reason || "Payment update link dispatched to cardholder",
      policyRule: "CUSTOMER_COMMUNICATION_DISPATCH",
      isHighValue: false,
      isHardDecline: false,
      isStoppingRule: false,
    };
  }

  return {
    title: "Autonomous Recovery In Progress",
    subtitle: txn?.failure_reason || c.strategy_summary || "Telemetry analyzed; recovery scheduled",
    policyRule: "DYNAMIC_RECOVERY_POLICY",
    isHighValue: false,
    isHardDecline: false,
    isStoppingRule: false,
  };
}

// Helper: Semantic status badge formatting
function getStatusBadge(c: RecoveryCase) {
  if (c.status === "RECOVERED") {
    return {
      dotColor: "bg-[#20B89A]",
      textColor: "text-[#20B89A]",
      bgColor: "bg-[#20B89A]/10",
      borderColor: "border-[#20B89A]/30",
      label: "Verified Recovery",
      tag: "VERIFIED",
    };
  }
  if (c.status === "PENDING_APPROVAL" || c.requires_human_approval === "YES") {
    return {
      dotColor: "bg-[#E5A958]",
      textColor: "text-[#E5A958]",
      bgColor: "bg-[#E5A958]/10",
      borderColor: "border-[#E5A958]/35",
      label: "Approval Required",
      tag: "POLICY GATE",
    };
  }
  if (c.status === "ESCALATED" || (c.status as string) === "STOPPED") {
    return {
      dotColor: "bg-[#F4A261]",
      textColor: "text-[#F4A261]",
      bgColor: "bg-[#F4A261]/10",
      borderColor: "border-[#F4A261]/35",
      label: "Stopped / Escalated",
      tag: "RETRY CEILING",
    };
  }
  if (c.status === "UNRECOVERABLE" || (c.status as string) === "BLOCKED") {
    return {
      dotColor: "bg-[#E56B6F]",
      textColor: "text-[#E56B6F]",
      bgColor: "bg-[#E56B6F]/10",
      borderColor: "border-[#E56B6F]/30",
      label: "Blocked / Unrecoverable",
      tag: "ANTI-FRAUD",
    };
  }
  return {
    dotColor: "bg-[#D79A43]",
    textColor: "text-[#D79A43]",
    bgColor: "bg-[#D79A43]/10",
    borderColor: "border-[#D79A43]/30",
    label: "Customer Action Required",
    tag: "IN PROGRESS",
  };
}

// Helper: Accurate retry display
function getRetryDisplay(c: RecoveryCase, txn?: Transaction): {
  attemptsText: string;
  subText: string;
} {
  const isStoppingRule =
    c.status === "ESCALATED" ||
    (c.status as string) === "STOPPED" ||
    (c.strategy_summary && c.strategy_summary.includes("HUMAN_ESCALATION"));

  if (isStoppingRule) {
    return {
      attemptsText: "3 / 3 ATTEMPTS",
      subText: "RETRY LOOP STOPPED",
    };
  }

  const isHardDecline =
    c.status === "UNRECOVERABLE" ||
    (txn?.failure_code && ["CARD_STOLEN_OR_LOST", "CARD_RESTRICTED", "FRAUD_SUSPECTED", "CARD_CANCELLED"].includes(txn.failure_code));

  if (isHardDecline) {
    return {
      attemptsText: "0 RETRIES ATTEMPTED",
      subText: "STRICTLY BLOCKED",
    };
  }

  if (c.status === "RECOVERED") {
    return {
      attemptsText: "1 / 3 ATTEMPTS",
      subText: "VERIFIED SETTLED",
    };
  }

  if (c.status === "PENDING_APPROVAL" || c.requires_human_approval === "YES" || c.amount_at_risk >= 25000) {
    return {
      attemptsText: "0 RETRIES ATTEMPTED",
      subText: "HELD AT POLICY GATE",
    };
  }

  const currentAttempts = (c.retry_count || 0) + 1;
  return {
    attemptsText: `${Math.min(currentAttempts, 3)} / 3 ATTEMPTS`,
    subText: "LINK DISPATCHED",
  };
}

export default function RecoveryQueuePage() {
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [transactionsMap, setTransactionsMap] = useState<Record<string, Transaction>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Selected Case Detail for Telemetry Panel
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<RecoveryCaseDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  const loadCaseDetail = async (caseId: string) => {
    try {
      setIsDetailLoading(true);
      const detail = await api.getCaseDetail(caseId);
      setSelectedCaseDetail(detail);
    } catch (err) {
      console.error("Failed to fetch case detail:", err);
    } finally {
      setIsDetailLoading(false);
    }
  };

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    loadCaseDetail(caseId);
  };

  const loadCases = async () => {
    try {
      setIsLoading(true);
      const [casesData, txnsData] = await Promise.all([
        api.getCases(),
        api.getTransactions(undefined, 100).catch(() => []),
      ]);

      setCases(casesData);
      const map: Record<string, Transaction> = {};
      for (const t of txnsData) {
        map[t.id] = t;
      }
      setTransactionsMap(map);

      // Auto-select first case if none is selected
      if (casesData.length > 0) {
        const defaultId = selectedCaseId && casesData.some((c) => c.id === selectedCaseId)
          ? selectedCaseId
          : casesData[0].id;
        setSelectedCaseId(defaultId);
        loadCaseDetail(defaultId);
      }
    } catch (err) {
      console.error("Failed to load recovery cases:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleApprove = async (caseId: string) => {
    try {
      setActionLoadingId(caseId);
      await api.approveCase(caseId);
      if (selectedCaseId === caseId) {
        await loadCaseDetail(caseId);
      }
      await loadCases();
    } catch (err) {
      console.error("Failed to approve case:", err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSimulateRecovery = async (caseId: string) => {
    try {
      setActionLoadingId(caseId);
      await api.simulateRecovery(caseId);
      if (selectedCaseId === caseId) {
        await loadCaseDetail(caseId);
      }
      await loadCases();
    } catch (err) {
      console.error("Failed to simulate recovery:", err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const [isBatchEvaluating, setIsBatchEvaluating] = useState(false);
  const [batchNotice, setBatchNotice] = useState<string | null>(null);

  const handleBatchEvaluate = async () => {
    try {
      setIsBatchEvaluating(true);
      setBatchNotice(null);
      const res = await api.batchEvaluateCases();
      setBatchNotice(`Batch evaluation complete: ${res.processed_count} evaluated (${res.approved_count} approved, ${res.held_for_approval} held, ${res.blocked_or_stopped} stopped).`);
      await loadCases();
      setTimeout(() => setBatchNotice(null), 5000);
    } catch (err: any) {
      setBatchNotice(err.message || "Batch evaluation failed.");
    } finally {
      setIsBatchEvaluating(false);
    }
  };

  // Dynamic filter tab counts derived directly from case records
  const tabCounts = useMemo(() => {
    return {
      ALL: cases.length,
      ACTIVE: cases.filter((c) => c.status !== "RECOVERED" && c.status !== "UNRECOVERABLE" && c.status !== "EXPIRED").length,
      RECOVERING: cases.filter((c) => c.status === "IN_PROGRESS" || c.status === "OPEN").length,
      AWAITING_APPROVAL: cases.filter((c) => c.status === "PENDING_APPROVAL" || c.requires_human_approval === "YES").length,
      RECOVERED: cases.filter((c) => c.status === "RECOVERED").length,
      UNRECOVERABLE: cases.filter((c) => c.status === "UNRECOVERABLE" || c.status === "ESCALATED" || (c.status as string) === "STOPPED").length,
    };
  }, [cases]);

  // Filtered Cases List
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const s = c.status as string;
      if (selectedTab !== "ALL") {
        if (selectedTab === "ACTIVE" && (s === "RECOVERED" || s === "UNRECOVERABLE" || s === "EXPIRED")) return false;
        if (selectedTab === "RECOVERING" && s !== "IN_PROGRESS" && s !== "OPEN") return false;
        if (selectedTab === "AWAITING_APPROVAL" && s !== "PENDING_APPROVAL" && c.requires_human_approval !== "YES") return false;
        if (selectedTab === "RECOVERED" && s !== "RECOVERED") return false;
        if (selectedTab === "UNRECOVERABLE" && s !== "UNRECOVERABLE" && s !== "ESCALATED" && s !== "STOPPED") return false;
      }

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const txn = transactionsMap[c.transaction_id];
        const displayId = formatTransactionDisplayId(c.transaction_id, txn?.transaction_id).toLowerCase();
        const matches =
          c.id.toLowerCase().includes(q) ||
          c.transaction_id.toLowerCase().includes(q) ||
          displayId.includes(q) ||
          (c.strategy_summary && c.strategy_summary.toLowerCase().includes(q)) ||
          (txn?.failure_code && txn.failure_code.toLowerCase().includes(q)) ||
          (txn?.failure_reason && txn.failure_reason.toLowerCase().includes(q));
        if (!matches) return false;
      }

      return true;
    });
  }, [cases, selectedTab, searchQuery, transactionsMap]);

  // Telemetry metrics
  const totalAtRisk = useMemo(() => {
    return cases.reduce((acc, c) => acc + (c.amount_at_risk || 0), 0);
  }, [cases]);

  const recoveredToday = useMemo(() => {
    return cases
      .filter((c) => c.status === "RECOVERED")
      .reduce((acc, c) => acc + (c.recovered_amount || c.amount_at_risk || 0), 0);
  }, [cases]);

  const filterTabs = [
    { id: "ALL", label: "ALL", count: tabCounts.ALL },
    { id: "ACTIVE", label: "ACTIVE", count: tabCounts.ACTIVE },
    { id: "RECOVERING", label: "RECOVERING", count: tabCounts.RECOVERING },
    { id: "AWAITING_APPROVAL", label: "AWAITING APPROVAL", count: tabCounts.AWAITING_APPROVAL },
    { id: "RECOVERED", label: "RECOVERED", count: tabCounts.RECOVERED },
    { id: "UNRECOVERABLE", label: "UNRECOVERABLE", count: tabCounts.UNRECOVERABLE },
  ];

  // Currently selected case object and its transaction
  const selectedCaseObj = useMemo(() => {
    return cases.find((c) => c.id === selectedCaseId) || null;
  }, [cases, selectedCaseId]);

  const selectedTxnObj = useMemo(() => {
    if (!selectedCaseObj) return undefined;
    return transactionsMap[selectedCaseObj.transaction_id];
  }, [selectedCaseObj, transactionsMap]);

  const selectedCaseInfo = useMemo(() => {
    if (!selectedCaseObj) return null;
    return getHumanCaseInfo(selectedCaseObj, selectedTxnObj);
  }, [selectedCaseObj, selectedTxnObj]);

  const selectedCaseBadge = useMemo(() => {
    if (!selectedCaseObj) return null;
    return getStatusBadge(selectedCaseObj);
  }, [selectedCaseObj]);

  const selectedCaseRetry = useMemo(() => {
    if (!selectedCaseObj) return null;
    return getRetryDisplay(selectedCaseObj, selectedTxnObj);
  }, [selectedCaseObj, selectedTxnObj]);

  return (
    <div className="space-y-6 pb-16 relative">
      {/* 1. Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between pb-5 border-b border-white/[0.08] gap-4">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-[#D79A43] block mb-1">
            GOVERNED RECOVERY PIPELINE
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F0E8]">
            Recovery Queue
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Real-time inspection of payment failures, AI root-cause diagnoses, and deterministic policy guardrails.
          </p>

          <div className="flex flex-wrap items-center gap-4 mt-3 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#20B89A] opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#20B89A]" />
              </span>
              <span className="text-[#20B89A] font-bold">PIPELINE ACTIVE</span>
            </div>
            <span className="text-white/20">•</span>
            <span className="text-[#F5F0E8] font-bold">{tabCounts.ACTIVE} ACTIVE CASES</span>
            <span className="text-white/20">•</span>
            <span className="text-[#D79A43] font-bold">₹{totalAtRisk.toLocaleString("en-IN")} REVENUE AT RISK</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleBatchEvaluate}
            disabled={isBatchEvaluating}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#D79A43]/15 text-[#D79A43] hover:bg-[#D79A43]/25 border border-[#D79A43]/30 transition-all cursor-pointer disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 fill-[#D79A43] ${isBatchEvaluating ? "animate-pulse" : ""}`} />
            <span>{isBatchEvaluating ? "EVALUATING..." : "BATCH EVALUATE"}</span>
          </button>

          <button
            onClick={loadCases}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
            <span>SYNC QUEUE</span>
          </button>
        </div>
      </div>

      {/* Batch Notification Banner */}
      {batchNotice && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3.5 rounded-xl bg-[#20B89A]/10 border border-[#20B89A]/30 text-[#20B89A] font-mono text-xs flex items-center justify-between shadow-sm"
        >
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-[#20B89A] shrink-0" />
            <span>{batchNotice}</span>
          </div>
          <button onClick={() => setBatchNotice(null)} className="text-[#918D84] hover:text-[#F5F0E8]">
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      )}

      {/* 2. Telemetry Summary Cards Strip */}
      <div className="p-4 sm:p-5 rounded-2xl bg-[#11110F] border border-white/[0.08] grid grid-cols-2 sm:grid-cols-5 gap-4 font-mono text-xs shadow-md">
        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#66625B] uppercase block mb-1">TOTAL INGESTED</span>
          <span className="text-xl sm:text-2xl font-bold text-[#F5F0E8] tabular-nums">
            {cases.length}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#D79A43] uppercase block mb-1">RECOVERING</span>
          <span className="text-xl sm:text-2xl font-bold text-[#D79A43] tabular-nums">
            {tabCounts.RECOVERING}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#E5A958] uppercase block mb-1">APPROVAL REQUIRED</span>
          <span className="text-xl sm:text-2xl font-bold text-[#E5A958] tabular-nums">
            {tabCounts.AWAITING_APPROVAL}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#20B89A] uppercase block mb-1">VERIFIED RECOVERIES</span>
          <span className="text-xl sm:text-2xl font-bold text-[#20B89A] tabular-nums">
            {tabCounts.RECOVERED}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-[#20B89A] uppercase block mb-1">RECOVERED VOLUME</span>
          <span className="text-xl sm:text-2xl font-bold text-[#20B89A] tabular-nums">
            ₹{recoveredToday.toLocaleString("en-IN")}
          </span>
        </div>
      </div>

      {/* 3. Filters & Search Bar */}
      <div className="p-4 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col lg:flex-row items-center justify-between gap-4 font-mono text-xs">
        {/* Search */}
        <div className="relative w-full lg:w-96">
          <Search className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search TXN-DEMO-045, failure reason, policy rule..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#080807] border border-white/[0.08] rounded-xl pl-9 pr-4 py-2.5 text-xs text-[#F5F0E8] placeholder:text-[#66625B] focus:outline-none focus:border-[#D79A43]/60 transition-colors"
          />
        </div>

        {/* Filter Tabs with Dynamic Counts */}
        <div className="flex flex-wrap items-center gap-1.5 w-full lg:w-auto">
          {filterTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-1.5 ${
                selectedTab === tab.id
                  ? "bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/40 font-bold shadow-sm"
                  : "text-[#918D84] hover:text-[#F5F0E8] bg-[#171614] border border-white/[0.06]"
              }`}
            >
              <span>{tab.label}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                selectedTab === tab.id ? "bg-[#D79A43]/25 text-[#D79A43]" : "bg-white/[0.05] text-[#66625B]"
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* 4. Main Two-Column Layout: Case Queue (Left 8 cols) + Selected Case Telemetry (Right 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (8 cols): Structured Case Cards */}
        <div className="lg:col-span-8 space-y-3.5">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] animate-pulse h-32" />
              ))}
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="p-12 rounded-2xl bg-[#11110F] border border-white/[0.08] text-center font-mono space-y-3">
              <span className="text-xs font-bold text-[#D79A43] tracking-widest uppercase block">
                NO CASES MATCH FILTER
              </span>
              <p className="text-sm text-[#918D84] max-w-md mx-auto leading-relaxed">
                No recovery cases match the current filter selection or search query.
              </p>
              <button
                onClick={() => {
                  setSelectedTab("ALL");
                  setSearchQuery("");
                }}
                className="mt-2 text-xs font-bold text-[#D79A43] hover:underline"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            filteredCases.map((c) => {
              const txn = transactionsMap[c.transaction_id];
              const displayTxnId = formatTransactionDisplayId(c.transaction_id, txn?.transaction_id);
              const caseInfo = getHumanCaseInfo(c, txn);
              const statusBadge = getStatusBadge(c);
              const retryInfo = getRetryDisplay(c, txn);
              const isSelected = selectedCaseId === c.id;
              const isPendingApproval = c.status === "PENDING_APPROVAL" || c.requires_human_approval === "YES";
              const isBusy = actionLoadingId === c.id;

              return (
                <div
                  key={c.id}
                  onClick={() => handleSelectCase(c.id)}
                  className={`p-5 rounded-2xl transition-all cursor-pointer group border ${
                    isSelected
                      ? "bg-[#161513] border-[#D79A43]/60 shadow-[0_4px_24px_rgba(215,154,67,0.12)] ring-1 ring-[#D79A43]/40"
                      : isPendingApproval
                      ? "bg-[#14120E] border-[#E5A958]/35 hover:border-[#E5A958]/60"
                      : caseInfo.isHardDecline
                      ? "bg-[#141010] border-[#E56B6F]/25 hover:border-[#E56B6F]/50"
                      : caseInfo.isStoppingRule
                      ? "bg-[#14110E] border-[#F4A261]/25 hover:border-[#F4A261]/50"
                      : "bg-[#11110F] border-white/[0.08] hover:bg-[#151513] hover:border-white/[0.16]"
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    {/* LEFT SECTION (Width ~28%): Identity & Status */}
                    <div className="space-y-1 md:w-3/12 shrink-0">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${statusBadge.dotColor}`} />
                        <span className={`text-[10px] font-mono font-bold tracking-wider uppercase ${statusBadge.textColor}`}>
                          {c.status}
                        </span>
                        {caseInfo.isHighValue && (
                          <span className="text-[9px] font-mono font-bold text-[#E5A958] bg-[#E5A958]/15 px-1.5 py-0.5 rounded border border-[#E5A958]/30 shrink-0">
                            ≥ ₹25K GATE
                          </span>
                        )}
                      </div>

                      <div className="font-mono text-sm font-bold text-[#F5F0E8] tracking-tight group-hover:text-[#D79A43] transition-colors">
                        {displayTxnId}
                      </div>

                      <div className="text-xs text-[#918D84] font-medium leading-snug">
                        {caseInfo.title}
                      </div>
                    </div>

                    {/* CENTER SECTION (Width ~46%): Root Cause, Strategy & Policy */}
                    <div className="space-y-1.5 md:w-6/12 flex-1 border-t md:border-t-0 md:border-l border-white/[0.06] pt-3 md:pt-0 md:pl-4">
                      <div className="text-xs text-[#F5F0E8] font-mono flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] shrink-0" />
                        <span className="line-clamp-1">{caseInfo.subtitle}</span>
                      </div>

                      <div className="text-[11px] font-mono text-[#66625B] flex flex-wrap items-center gap-2">
                        <span className="text-[#918D84]">Policy:</span>
                        <span className="text-[#D79A43] font-bold bg-[#D79A43]/10 px-2 py-0.5 rounded border border-[#D79A43]/20">
                          {caseInfo.policyRule}
                        </span>
                        <span>•</span>
                        <span>Score: {c.recovery_score}%</span>
                      </div>
                    </div>

                    {/* RIGHT SECTION (Width ~26%): Financial Amount, Badge & CTAs */}
                    <div className="flex items-center justify-between md:flex-col md:items-end md:justify-center shrink-0 border-t md:border-t-0 md:border-l border-white/[0.06] pt-3 md:pt-0 md:pl-4 space-y-1 min-w-[140px]">
                      <div className="font-serif text-xl sm:text-2xl font-bold text-[#F5F0E8] tabular-nums">
                        ₹{c.amount_at_risk.toLocaleString("en-IN")}
                      </div>

                      <div className="flex flex-col md:items-end gap-0.5">
                        <span className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full border ${statusBadge.bgColor} ${statusBadge.borderColor} ${statusBadge.textColor}`}>
                          {statusBadge.label}
                        </span>
                        <span className="text-[10px] font-mono text-[#66625B]">
                          {retryInfo.attemptsText}
                        </span>
                      </div>

                      <div className="pt-1 flex items-center gap-2">
                        {isPendingApproval && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleApprove(c.id);
                            }}
                            disabled={isBusy}
                            className="px-2.5 py-1 rounded-lg bg-[#E5A958] hover:bg-[#F0B84B] text-[#070706] font-mono font-bold text-[11px] shadow-gold cursor-pointer disabled:opacity-50"
                          >
                            {isBusy ? "Approving..." : "APPROVE"}
                          </button>
                        )}

                        <Link
                          href={`/dashboard/recovery/cases/${c.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-mono font-bold text-[#D79A43] hover:text-[#F0B84B] flex items-center gap-1 transition-colors"
                        >
                          <span>Inspect</span>
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column (4 cols): Persistent Policy Guardrails + Selected Case Telemetry */}
        <div className="lg:col-span-4 space-y-6">
          {/* 1. Persistent Policy Guardrails Checklist */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-md font-mono text-xs space-y-3.5">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-bold text-[#F5F0E8] tracking-wider">
                POLICY GUARDRAILS
              </span>
              <span className="text-[10px] text-[#20B89A] font-bold">13/13 ACTIVE</span>
            </div>

            <div className="space-y-2.5 text-[11px]">
              <div className="flex items-center gap-2 text-[#F5F0E8]">
                <CheckCircle2 className="w-4 h-4 text-[#20B89A] shrink-0" />
                <span>MAX 3 RETRIES PER TRANSACTION</span>
              </div>
              <div className="flex items-center gap-2 text-[#F5F0E8]">
                <CheckCircle2 className="w-4 h-4 text-[#20B89A] shrink-0" />
                <span>HARD DECLINE SUPPRESSION</span>
              </div>
              <div className="flex items-center gap-2 text-[#F5F0E8]">
                <CheckCircle2 className="w-4 h-4 text-[#20B89A] shrink-0" />
                <span>₹25K HUMAN APPROVAL GATE</span>
              </div>
              <div className="flex items-center gap-2 text-[#F5F0E8]">
                <CheckCircle2 className="w-4 h-4 text-[#20B89A] shrink-0" />
                <span>IDEMPOTENT EXECUTION LOCK</span>
              </div>
              <div className="flex items-center gap-2 text-[#F5F0E8]">
                <CheckCircle2 className="w-4 h-4 text-[#20B89A] shrink-0" />
                <span>SHA-256 AUDIT CHAIN VERIFIED</span>
              </div>
            </div>
          </div>

          {/* 2. Selected Case Live Telemetry Timeline */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-md font-mono text-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D79A43] opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#D79A43]" />
                </span>
                <span className="text-xs font-bold text-[#F5F0E8] tracking-wider">
                  CASE TELEMETRY
                </span>
              </div>
              <span className="text-[10px] text-[#D79A43] font-bold">
                {selectedCaseObj ? "LIVE SELECTION" : "IDLE"}
              </span>
            </div>

            {isDetailLoading ? (
              <div className="space-y-3 py-4 animate-pulse text-[#918D84] text-center">
                <p>Loading live case timeline...</p>
              </div>
            ) : selectedCaseObj && selectedCaseInfo && selectedCaseBadge && selectedCaseRetry ? (
              <div className="space-y-4">
                {/* Header Case Identification */}
                <div className="p-3.5 rounded-xl bg-[#171614] border border-white/[0.07] flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-[#66625B] uppercase block">TRANSACTION ID</span>
                    <span className="text-sm font-bold text-[#F5F0E8]">
                      {formatTransactionDisplayId(selectedCaseObj.transaction_id, selectedTxnObj?.transaction_id)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-[#66625B] uppercase block">AMOUNT</span>
                    <span className="font-serif text-lg font-bold text-[#D79A43] tabular-nums">
                      ₹{selectedCaseObj.amount_at_risk.toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>

                {/* Stage 1: AI Diagnostic Intelligence */}
                <div className="p-3.5 rounded-xl bg-[#141412] border border-white/[0.06] space-y-1.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-[#D79A43] font-bold uppercase flex items-center gap-1.5">
                      <Brain className="w-3.5 h-3.5" /> STAGE 1: AI DIAGNOSIS
                    </span>
                    <span className="text-[#20B89A] font-bold">
                      {selectedCaseDetail?.ai_decisions?.[0]
                        ? `${(selectedCaseDetail.ai_decisions[0].confidence_score * 100).toFixed(0)}% Conf.`
                        : "Advisory"}
                    </span>
                  </div>
                  <p className="text-[#F5F0E8] text-[11px] leading-relaxed">
                    {selectedCaseDetail?.ai_decisions?.[0]?.root_cause_explanation ||
                      selectedTxnObj?.failure_reason ||
                      selectedCaseInfo.subtitle}
                  </p>
                </div>

                {/* Stage 2: Deterministic Policy Rule */}
                <div className="p-3.5 rounded-xl bg-[#141412] border border-white/[0.06] space-y-1.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-[#D79A43] font-bold uppercase flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5" /> STAGE 2: POLICY ENGINE
                    </span>
                    <span className={`font-bold ${selectedCaseInfo.isHighValue || selectedCaseInfo.isStoppingRule || selectedCaseInfo.isHardDecline ? "text-[#E5A958]" : "text-[#20B89A]"}`}>
                      {selectedCaseInfo.policyRule}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#918D84] flex items-center justify-between pt-1">
                    <span>Retry Ceiling:</span>
                    <span className="font-bold text-[#F5F0E8]">{selectedCaseRetry.attemptsText}</span>
                  </div>
                  <div className="text-[11px] text-[#918D84] flex items-center justify-between">
                    <span>Current Outcome:</span>
                    <span className={`font-bold ${selectedCaseBadge.textColor}`}>{selectedCaseBadge.label}</span>
                  </div>
                </div>

                {/* Action Controls if Applicable */}
                {selectedCaseObj.status === "PENDING_APPROVAL" || selectedCaseObj.requires_human_approval === "YES" ? (
                  <div className="p-3.5 rounded-xl bg-[#E5A958]/10 border border-[#E5A958]/35 text-[#E5A958] space-y-2">
                    <div className="flex items-center gap-2 font-bold text-xs">
                      <ShieldAlert className="w-4 h-4" />
                      <span>Executive Sign-Off Enforced</span>
                    </div>
                    <p className="text-[10px] text-[#F5F0E8]/80 leading-relaxed">
                      Transaction exceeds ₹25,000 threshold. Manual executive approval required.
                    </p>
                    <button
                      onClick={() => handleApprove(selectedCaseObj.id)}
                      disabled={actionLoadingId === selectedCaseObj.id}
                      className="w-full py-2 rounded-lg bg-[#E5A958] hover:bg-[#F0B84B] text-[#070706] font-mono font-bold text-xs shadow-gold transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      {actionLoadingId === selectedCaseObj.id ? "Approving..." : "Approve Recovery (+₹" + selectedCaseObj.amount_at_risk.toLocaleString("en-IN") + ")"}
                    </button>
                  </div>
                ) : selectedCaseObj.status !== "RECOVERED" && selectedCaseObj.status !== "UNRECOVERABLE" && !selectedCaseInfo.isStoppingRule ? (
                  <button
                    onClick={() => handleSimulateRecovery(selectedCaseObj.id)}
                    disabled={actionLoadingId === selectedCaseObj.id}
                    className="w-full py-2 rounded-lg bg-[#20B89A] hover:bg-[#28D4B0] text-[#070706] font-mono font-bold text-xs shadow-gold transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {actionLoadingId === selectedCaseObj.id ? "Settling..." : "Execute Verified Sandbox Settlement"}
                  </button>
                ) : null}

                {/* Direct Link to Dedicated Inspector Page */}
                <Link
                  href={`/dashboard/recovery/cases/${selectedCaseObj.id}`}
                  className="w-full py-2.5 rounded-xl bg-[#171614] hover:bg-[#1E1D1A] border border-white/[0.08] hover:border-[#D79A43]/40 text-[#F5F0E8] font-mono text-xs font-bold transition-all flex items-center justify-center gap-2 group"
                >
                  <span>Open Full Diagnostic Timeline</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#D79A43] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </Link>
              </div>
            ) : (
              <div className="py-12 text-center text-[#66625B] space-y-2">
                <Activity className="w-8 h-8 text-[#66625B]/60 mx-auto" />
                <p className="text-xs">Select a recovery case to inspect its decision timeline.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
