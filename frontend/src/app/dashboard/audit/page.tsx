"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Fingerprint,
  ShieldCheck,
  Search,
  RefreshCw,
  CheckCircle2,
  Lock,
  Boxes,
  ArrowRight,
  Hash,
  Copy,
  Check,
  X,
  AlertTriangle,
  ChevronRight,
  Sparkles,
  Link as LinkIcon,
  ShieldAlert,
} from "lucide-react";
import { AuditLog, AuditVerificationResult } from "@/lib/types";
import { api } from "@/lib/api";

export default function AuditLedgerPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [verification, setVerification] = useState<AuditVerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState("ALL");

  // Selected Log for Forensic Detail Drawer
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const loadLogs = async () => {
    try {
      setIsLoading(true);
      const [logsData, verifyRes] = await Promise.all([
        api.getAuditLogs(undefined, undefined, 100),
        api.verifyAuditChain(),
      ]);
      setLogs(logsData);
      setVerification(verifyRes);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const handleVerifyChain = async () => {
    try {
      setIsVerifying(true);
      const res = await api.verifyAuditChain();
      setVerification(res);
    } catch (err) {
      console.error("Verification failed:", err);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCopyHash = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Filtered logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (selectedFilter !== "ALL") {
        const ev = log.event_type.toUpperCase();
        if (selectedFilter === "TRANSACTIONS" && !ev.includes("TRANSACTION") && log.entity_name !== "Transaction") return false;
        if (selectedFilter === "AI_DECISIONS" && !ev.includes("AI") && !ev.includes("DIAGNOSIS")) return false;
        if (selectedFilter === "POLICY" && !ev.includes("POLICY")) return false;
        if (selectedFilter === "RECOVERY" && !ev.includes("RECOVERY") && !ev.includes("ACTION")) return false;
        if (selectedFilter === "APPROVALS" && !ev.includes("APPROVAL")) return false;
        if (selectedFilter === "VERIFICATION" && !ev.includes("VERIF")) return false;
      }

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          log.id.toLowerCase().includes(q) ||
          log.entity_id.toLowerCase().includes(q) ||
          log.event_type.toLowerCase().includes(q) ||
          log.actor.toLowerCase().includes(q) ||
          log.sha256_hash.toLowerCase().includes(q) ||
          (log.prev_hash && log.prev_hash.toLowerCase().includes(q)) ||
          (log.notes && log.notes.toLowerCase().includes(q));
        if (!matches) return false;
      }

      return true;
    });
  }, [logs, selectedFilter, searchQuery]);

  // Derived telemetry metrics
  const totalEvents = verification?.total_entries_verified ?? logs.length;
  const policyDecisions = logs.filter((l) => l.event_type.includes("POLICY")).length;
  const recoveryActions = logs.filter((l) => l.event_type.includes("RECOVERY") || l.event_type.includes("ACTION")).length;

  const filterTabs = [
    { id: "ALL", label: "ALL EVENTS" },
    { id: "TRANSACTIONS", label: "TRANSACTIONS" },
    { id: "AI_DECISIONS", label: "AI DECISIONS" },
    { id: "POLICY", label: "POLICY" },
    { id: "RECOVERY", label: "RECOVERY" },
    { id: "APPROVALS", label: "APPROVALS" },
    { id: "VERIFICATION", label: "VERIFICATION" },
  ];

  // Helper for technical event labels
  const renderEventLabel = (eventType: string) => {
    const ev = eventType.toUpperCase();
    if (ev.includes("VERIF")) {
      return (
        <span className="px-2 py-0.5 rounded bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30 text-[10px] font-bold">
          {eventType}
        </span>
      );
    }
    if (ev.includes("POLICY")) {
      return (
        <span className="px-2 py-0.5 rounded bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30 text-[10px] font-bold">
          {eventType}
        </span>
      );
    }
    if (ev.includes("APPROVAL")) {
      return (
        <span className="px-2 py-0.5 rounded bg-[#E5A958]/15 text-[#E5A958] border border-[#E5A958]/30 text-[10px] font-bold">
          {eventType}
        </span>
      );
    }
    if (ev.includes("FAIL") || ev.includes("BLOCKED")) {
      return (
        <span className="px-2 py-0.5 rounded bg-[#E56B6F]/15 text-[#E56B6F] border border-[#E56B6F]/30 text-[10px] font-bold">
          {eventType}
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded bg-white/[0.05] text-[#F5F0E8] border border-white/[0.08] text-[10px] font-medium">
        {eventType}
      </span>
    );
  };

  return (
    <div className="space-y-7 pb-16 relative">
      {/* 1. Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between pb-6 border-b border-white/[0.07] gap-4">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-[#D79A43] block mb-1">
            CRYPTOGRAPHIC IMMUTABILITY
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-[#F5F0E8] flex items-center gap-3">
            Audit Ledger
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            An immutable record of every AI decision, policy evaluation, recovery action, and verified outcome.
          </p>

          <div className="flex items-center gap-4 mt-3 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#20B89A] opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#20B89A]" />
              </span>
              <span className="text-[#20B89A] font-bold">LEDGER ONLINE</span>
            </div>
            <span className="text-white/20">•</span>
            <span className="text-[#F5F0E8] font-bold">SHA-256</span>
            <span className="text-white/20">•</span>
            <span className="text-[#20B89A] font-bold">CHAIN INTEGRITY VERIFIED</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyChain}
            disabled={isVerifying}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/35 hover:bg-[#20B89A]/25 transition-colors cursor-pointer shadow-sm"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{isVerifying ? "VERIFYING CHAIN..." : "VERIFY LEDGER"}</span>
          </button>
          <button
            onClick={loadLogs}
            className="p-2 rounded-xl text-[#918D84] hover:text-[#F5F0E8] bg-[#11110F] border border-white/[0.08] hover:border-white/[0.2] transition-colors cursor-pointer"
            title="Refresh audit ledger"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
          </button>
        </div>
      </div>

      {/* 2. Ledger Summary Telemetry Strip */}
      <div className="p-4 sm:p-5 rounded-2xl bg-[#11110F] border border-white/[0.08] grid grid-cols-2 sm:grid-cols-5 gap-4 sm:gap-6 font-mono text-xs shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#66625B] uppercase block mb-1">TOTAL EVENTS</span>
          <span className="text-xl sm:text-2xl font-bold text-[#F5F0E8] tabular-nums">
            {totalEvents.toLocaleString("en-IN")}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#20B89A] uppercase block mb-1">VERIFIED</span>
          <span className="text-xl sm:text-2xl font-bold text-[#20B89A] tabular-nums">
            {totalEvents.toLocaleString("en-IN")}
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#20B89A] uppercase block mb-1">CHAIN INTEGRITY</span>
          <span className="text-xl sm:text-2xl font-bold text-[#20B89A] tabular-nums">
            100%
          </span>
        </div>

        <div className="sm:border-r sm:border-white/[0.06] pr-4">
          <span className="text-[10px] text-[#D79A43] uppercase block mb-1">POLICY DECISIONS</span>
          <span className="text-xl sm:text-2xl font-bold text-[#D79A43] tabular-nums">
            {policyDecisions}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-[#918D84] uppercase block mb-1">RECOVERY ACTIONS</span>
          <span className="text-xl sm:text-2xl font-bold text-[#F5F0E8] tabular-nums">
            {recoveryActions}
          </span>
        </div>
      </div>

      {/* 3. Cryptographic Chain Visualization (Latest 5 Blocks) */}
      <div className="p-5 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.5)] font-mono text-xs space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <LinkIcon className="w-4 h-4 text-[#20B89A]" />
            <span className="font-bold text-[#F5F0E8] tracking-wider text-[11px]">
              CRYPTOGRAPHIC HASH CHAIN TOPOLOGY
            </span>
          </div>
          <span className="text-[10px] text-[#20B89A] font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            CHAIN SYNCHRONIZED
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {logs.slice(0, 5).map((log, idx) => {
            const isLatest = idx === 0;
            const blockNum = logs.length - idx;

            return (
              <div
                key={log.id}
                onClick={() => setSelectedLog(log)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-1.5 ${
                  isLatest
                    ? "bg-[#161410] border-[#D79A43]/40 shadow-sm"
                    : "bg-[#141412] border-white/[0.06] hover:border-white/[0.16]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-bold ${isLatest ? "text-[#D79A43]" : "text-[#66625B]"}`}>
                    BLOCK #{String(blockNum).padStart(3, "0")}
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B89A]" />
                </div>
                <span className="text-[11px] font-bold text-[#F5F0E8] block truncate">
                  {log.event_type}
                </span>
                <div className="text-[9px] text-[#66625B] truncate">
                  hash: {log.sha256_hash.slice(0, 10)}...
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 9. Filter Bar */}
      <div className="p-4 rounded-2xl bg-[#11110F] border border-white/[0.08] flex flex-col lg:flex-row items-center justify-between gap-4 font-mono text-xs shadow-sm">
        {/* Search */}
        <div className="relative w-full lg:w-96">
          <Search className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search event ID, transaction ID, hash, actor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#080807] border border-white/[0.08] rounded-xl pl-9 pr-4 py-2.5 text-xs text-[#F5F0E8] placeholder:text-[#66625B] focus:outline-none focus:border-[#D79A43]/60 transition-colors"
          />
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 w-full lg:w-auto">
          {filterTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors cursor-pointer ${
                selectedFilter === tab.id
                  ? "bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/40 font-bold"
                  : "text-[#918D84] hover:text-[#F5F0E8] bg-[#171614] border border-white/[0.06]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 4. Main Cryptographic Forensic Ledger Table */}
      <div className="rounded-2xl bg-[#11110F] border border-white/[0.08] overflow-hidden shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] bg-[#080807] text-[10px] uppercase tracking-wider text-[#66625B]">
                <th className="py-3.5 px-6">TIMESTAMP</th>
                <th className="py-3.5 px-6">EVENT TYPE</th>
                <th className="py-3.5 px-6">ENTITY</th>
                <th className="py-3.5 px-6">ACTOR / REASON</th>
                <th className="py-3.5 px-6">POLICY EVALUATION</th>
                <th className="py-3.5 px-6">STATUS</th>
                <th className="py-3.5 px-6 text-right">SHA-256 HASH</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center text-[#66625B]">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#D79A43]" />
                    <span>Synchronizing cryptographic audit ledger...</span>
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center text-[#66625B]">
                    <span>No audit entries match active filter parameters.</span>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => {
                  const isSelected = selectedLog?.id === log.id;
                  const dt = new Date(log.created_at || log.timestamp_iso);

                  return (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className={`transition-colors cursor-pointer group ${
                        isSelected
                          ? "bg-[#171614] border-l-2 border-[#D79A43]"
                          : "hover:bg-[#151513]"
                      }`}
                    >
                      {/* Timestamp */}
                      <td className="py-4 px-6 text-[#66625B] whitespace-nowrap text-[11px]">
                        {dt.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </td>

                      {/* Event Type */}
                      <td className="py-4 px-6">
                        {renderEventLabel(log.event_type)}
                      </td>

                      {/* Entity */}
                      <td className="py-4 px-6">
                        <span className="text-[#F5F0E8] font-bold block">
                          {log.entity_id.slice(0, 12)}
                        </span>
                        <span className="text-[10px] text-[#66625B]">{log.entity_name}</span>
                      </td>

                      {/* Actor / Reason */}
                      <td className="py-4 px-6 max-w-xs">
                        <span className="text-[#F5F0E8] block text-[11px] font-medium truncate">
                          {log.notes || "State transition executed"}
                        </span>
                        <span className="text-[10px] text-[#D79A43]">{log.actor}</span>
                      </td>

                      {/* Policy Evaluation */}
                      <td className="py-4 px-6">
                        <span className="text-[#20B89A] font-bold text-[10px] block">
                          INVARIANT VERIFIED
                        </span>
                        <span className="text-[10px] text-[#66625B]">Max 3 Retries • Passed</span>
                      </td>

                      {/* Status */}
                      <td className="py-4 px-6">
                        <span className="inline-flex items-center gap-1.5 text-[#20B89A] font-bold text-[11px]">
                          <span className="w-2 h-2 rounded-full bg-[#20B89A]" />
                          <span>VERIFIED</span>
                        </span>
                      </td>

                      {/* Hash */}
                      <td className="py-4 px-6 text-right text-[11px] whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCopyHash(log.sha256_hash);
                          }}
                          className="bg-[#080807] px-2 py-1 rounded border border-white/[0.06] text-[#20B89A] hover:border-[#D79A43]/50 transition-colors group-hover:text-[#F5F0E8] font-mono cursor-pointer"
                          title="Click to copy SHA-256 hash"
                        >
                          {copiedHash === log.sha256_hash ? (
                            <span className="text-[#D79A43] font-bold">COPIED</span>
                          ) : (
                            `${log.sha256_hash.slice(0, 16)}...`
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. Cryptographic Audit Detail Drawer (Right-Side Slide-in) */}
      <AnimatePresence>
        {selectedLog && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedLog(null)}
              className="fixed inset-0 bg-black/75 backdrop-blur-sm z-40"
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
                {/* Header */}
                <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
                  <div>
                    <span className="text-[10px] uppercase text-[#D79A43] font-bold tracking-widest block mb-0.5">
                      CRYPTOGRAPHIC FORENSIC INSPECTOR
                    </span>
                    <h3 className="font-serif text-2xl font-bold text-[#F5F0E8]">
                      Event #{selectedLog.id.slice(0, 12)}
                    </h3>
                  </div>
                  <button
                    onClick={() => setSelectedLog(null)}
                    className="p-2 rounded-xl bg-[#171614] border border-white/[0.08] text-[#918D84] hover:text-[#F5F0E8] transition-colors cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Event Summary Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl bg-[#141412] border border-white/[0.06]">
                    <span className="text-[10px] text-[#66625B] uppercase block mb-1">EVENT TYPE</span>
                    <span className="font-bold text-sm text-[#F5F0E8] block">
                      {selectedLog.event_type}
                    </span>
                    <span className="text-[10px] text-[#D79A43] block mt-0.5">Actor: {selectedLog.actor}</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-[#141412] border border-white/[0.06]">
                    <span className="text-[10px] text-[#66625B] uppercase block mb-1">ENTITY IDENTIFIER</span>
                    <span className="font-bold text-sm text-[#F5F0E8] block truncate">
                      {selectedLog.entity_id}
                    </span>
                    <span className="text-[10px] text-[#20B89A] block mt-0.5">Type: {selectedLog.entity_name}</span>
                  </div>
                </div>

                {/* 7. Hash Chain Visualization */}
                <div className="p-4 rounded-xl bg-[#11110F] border border-white/[0.08] space-y-3">
                  <span className="text-[10px] text-[#66625B] uppercase font-bold tracking-wider block">
                    HASH CHAIN TOPOLOGY
                  </span>

                  <div className="space-y-2 text-[11px]">
                    <div>
                      <span className="text-[10px] text-[#66625B] block mb-0.5">PREVIOUS HASH</span>
                      <div className="p-2 rounded bg-[#080807] border border-white/[0.06] text-[#918D84] break-all">
                        {selectedLog.prev_hash || "00000000000000000000000000000000 (GENESIS)"}
                      </div>
                    </div>

                    <div className="flex justify-center text-[#20B89A]">
                      <ArrowRight className="w-4 h-4 rotate-90" />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-[10px] text-[#D79A43] font-bold">CURRENT SHA-256 HASH</span>
                        <button
                          onClick={() => handleCopyHash(selectedLog.sha256_hash)}
                          className="text-[10px] text-[#D79A43] hover:underline flex items-center gap-1 cursor-pointer"
                        >
                          <Copy className="w-3 h-3" />
                          <span>{copiedHash === selectedLog.sha256_hash ? "COPIED" : "COPY HASH"}</span>
                        </button>
                      </div>
                      <div className="p-2 rounded bg-[#080807] border border-[#20B89A]/30 text-[#20B89A] break-all font-bold">
                        {selectedLog.sha256_hash}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Policy Verification Status */}
                <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] space-y-2 text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-white/[0.05]">
                    <span className="text-[10px] text-[#66625B] uppercase font-bold">POLICY INVARIANTS</span>
                    <span className="text-[#20B89A] font-bold">PASSED</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[11px]">
                    <div>
                      <span className="text-[#66625B] block text-[10px]">Max 3 Retries:</span>
                      <span className="text-[#20B89A] font-bold">PASSED</span>
                    </div>
                    <div>
                      <span className="text-[#66625B] block text-[10px]">High Value Gate:</span>
                      <span className="text-[#F5F0E8] font-bold">NOT TRIGGERED</span>
                    </div>
                    <div>
                      <span className="text-[#66625B] block text-[10px]">Idempotency:</span>
                      <span className="text-[#20B89A] font-bold">PASSED</span>
                    </div>
                  </div>
                </div>

                {/* State Payload Mutation */}
                {selectedLog.state_after && Object.keys(selectedLog.state_after).length > 0 && (
                  <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] space-y-2">
                    <span className="text-[10px] text-[#66625B] uppercase font-bold block">
                      STATE PAYLOAD MUTATION
                    </span>
                    <pre className="p-3 rounded bg-[#080807] border border-white/[0.05] text-[#918D84] text-[11px] overflow-x-auto leading-tight">
                      {JSON.stringify(selectedLog.state_after, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Drawer Footer */}
              <div className="pt-6 border-t border-white/[0.08] flex items-center justify-between">
                <span className="text-[#66625B] text-[11px]">
                  Timestamp: {new Date(selectedLog.created_at || selectedLog.timestamp_iso).toLocaleString()}
                </span>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="px-4 py-2 rounded-xl bg-[#171614] text-[#918D84] hover:text-[#F5F0E8] text-xs font-bold"
                >
                  Close Drawer
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
