"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, CheckCircle, RefreshCw, AlertCircle } from "lucide-react";
import { RecoveryCase } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { api } from "@/lib/api";

interface RecentCasesTableProps {
  cases: RecoveryCase[];
  isLoading?: boolean;
  onActionComplete?: () => void;
}

export function RecentCasesTable({ cases, isLoading, onActionComplete }: RecentCasesTableProps) {
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const handleApprove = async (e: React.MouseEvent, caseId: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      setActionLoadingId(caseId);
      await api.approveCase(caseId);
      if (onActionComplete) onActionComplete();
    } catch (err) {
      console.error("Failed to approve case:", err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleTrigger = async (e: React.MouseEvent, caseId: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      setActionLoadingId(caseId);
      await api.triggerCaseRecovery(caseId);
      if (onActionComplete) onActionComplete();
    } catch (err) {
      console.error("Failed to trigger recovery:", err);
    } finally {
      setActionLoadingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="fintech-card p-6 space-y-4">
        <div className="h-6 w-48 bg-[#242420] rounded animate-pulse" />
        <div className="space-y-2.5">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-[#1A1A18] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!cases || cases.length === 0) {
    return (
      <div className="fintech-card p-8 text-center">
        <div className="w-10 h-10 rounded-full bg-[#1A1A18] border border-white/[0.08] flex items-center justify-center mx-auto mb-3 text-[#66625B]">
          <AlertCircle className="w-5 h-5" />
        </div>
        <h4 className="font-serif text-lg font-bold text-[#F5F1E8]">No Recovery Cases Found</h4>
        <p className="text-xs font-mono text-[#918D84] mt-1">
          Click &ldquo;Sync / Re-seed&rdquo; in the navigation bar to populate demonstration records.
        </p>
      </div>
    );
  }

  return (
    <div className="fintech-card overflow-hidden">
      <div className="p-6 border-b border-white/[0.07] flex items-center justify-between">
        <div>
          <span className="mono-label text-[#D9A441] block mb-1">Live Queue Feed</span>
          <h3 className="font-serif text-2xl font-bold text-[#F5F1E8]">Recent Recovery Opportunities</h3>
        </div>
        <Link
          href="/dashboard/recovery"
          className="text-xs font-mono text-[#F0B84B] hover:text-[#D9A441] flex items-center gap-1 transition-colors"
        >
          <span>Full Operations Queue</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead>
            <tr className="border-b border-white/[0.06] bg-[#11110F] text-[10px] uppercase tracking-wider text-[#66625B]">
              <th className="py-3.5 px-6">Case Reference</th>
              <th className="py-3.5 px-6">Amount at Risk</th>
              <th className="py-3.5 px-6">Recovery Score</th>
              <th className="py-3.5 px-6">Status</th>
              <th className="py-3.5 px-6">Autonomous Strategy</th>
              <th className="py-3.5 px-6 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {cases.map((c) => {
              const isPendingApproval = c.status === "PENDING_APPROVAL";
              const isRecovered = c.status === "RECOVERED";
              const isBusy = actionLoadingId === c.id;

              return (
                <tr key={c.id} className="hover:bg-[#1A1A18]/60 transition-colors group">
                  <td className="py-4 px-6">
                    <Link
                      href={`/dashboard/transactions/${c.transaction_id}`}
                      className="font-medium text-[#F5F1E8] hover:text-[#F0B84B] flex items-center gap-1.5"
                    >
                      <span>#{c.id.slice(0, 8)}...</span>
                      <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-[#D9A441]" />
                    </Link>
                    <span className="text-[10px] text-[#66625B]">
                      {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </td>

                  <td className="py-4 px-6 font-semibold text-[#F5F1E8] tabular-nums">
                    ₹{c.amount_at_risk.toLocaleString("en-IN")}
                    {isRecovered && (
                      <span className="block text-[10px] text-[#36C9A5] font-normal">
                        Recovered ₹{c.recovered_amount.toLocaleString("en-IN")}
                      </span>
                    )}
                  </td>

                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <div className="w-12 bg-[#0A0A09] rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            c.recovery_score >= 80
                              ? "bg-[#36C9A5]"
                              : c.recovery_score >= 50
                              ? "bg-[#D9A441]"
                              : "bg-[#E56B6F]"
                          }`}
                          style={{ width: `${Math.min(100, Math.max(10, c.recovery_score))}%` }}
                        />
                      </div>
                      <span className="text-xs text-[#F5F1E8] tabular-nums">{c.recovery_score}%</span>
                    </div>
                  </td>

                  <td className="py-4 px-6">
                    <StatusBadge status={c.status} size="sm" />
                  </td>

                  <td className="py-4 px-6 max-w-xs truncate text-[#918D84]">
                    <span>{c.strategy_summary || "Autonomous pipeline evaluating..."}</span>
                    {c.requires_human_approval === "YES" && (
                      <span className="block text-[10px] text-[#E5A958] font-medium mt-0.5">
                        Approval: {c.approval_reason || "High value threshold"}
                      </span>
                    )}
                  </td>

                  <td className="py-4 px-6 text-right">
                    {isPendingApproval ? (
                      <button
                        onClick={(e) => handleApprove(e, c.id)}
                        disabled={isBusy}
                        className="px-2.5 py-1 rounded bg-[#E5A958]/20 hover:bg-[#E5A958]/30 text-[#E5A958] border border-[#E5A958]/40 text-[11px] font-mono font-medium transition-all"
                      >
                        {isBusy ? "Approving..." : "Approve Recovery"}
                      </button>
                    ) : c.status === "OPEN" || c.status === "ESCALATED" ? (
                      <button
                        onClick={(e) => handleTrigger(e, c.id)}
                        disabled={isBusy}
                        className="px-2.5 py-1 rounded bg-[#D9A441]/15 hover:bg-[#D9A441]/25 text-[#F0B84B] border border-[#D9A441]/30 text-[11px] font-mono font-medium transition-all"
                      >
                        {isBusy ? "Executing..." : "Trigger AI"}
                      </button>
                    ) : (
                      <Link
                        href={`/dashboard/transactions/${c.transaction_id}`}
                        className="text-[#66625B] hover:text-[#F5F1E8] text-[11px]"
                      >
                        Inspect →
                      </Link>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
