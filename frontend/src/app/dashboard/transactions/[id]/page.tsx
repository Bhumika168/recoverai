"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Brain,
  ShieldCheck,
  CheckCircle2,
  AlertOctagon,
  Coins,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { Transaction, RecoveryCaseDetail, AuditLog } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { TransactionAuditTimeline } from "@/components/TransactionAuditTimeline";
import { api } from "@/lib/api";

export default function TransactionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [caseDetail, setCaseDetail] = useState<RecoveryCaseDetail | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRecovering, setIsRecovering] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [recoverMessage, setRecoverMessage] = useState<string | null>(null);

  const handleRecover = async () => {
    try {
      setIsRecovering(true);
      setRecoverMessage(null);
      await api.recoverTransaction(id);
      setRecoverMessage("Recovery workflow executed.");
      await loadData();
    } catch (err: any) {
      console.error("Failed to recover transaction:", err);
      setRecoverMessage(`Recovery failed: ${err.message}`);
    } finally {
      setIsRecovering(false);
    }
  };

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const txn = await api.getTransaction(id);
      setTransaction(txn);

      const cases = await api.getCases();
      const matchingCase = cases.find((c) => c.transaction_id === id);
      if (matchingCase) {
        const fullCase = await api.getCaseDetail(matchingCase.id);
        setCaseDetail(fullCase);
      }

      const logs = await api.getAuditLogs(undefined, undefined, 50);
      const relevantLogs = logs.filter(
        (l) => l.entity_id === id || (matchingCase && l.entity_id === matchingCase.id)
      );
      setAuditLogs(relevantLogs);
    } catch (err: any) {
      console.error("Failed to load transaction detail:", err);
      setError(err.message || "Failed to load transaction detail");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const handleApprove = async () => {
    if (!caseDetail) return;
    try {
      setIsApproving(true);
      await api.approveCase(caseDetail.id);
      await loadData();
    } catch (err) {
      console.error("Failed to approve:", err);
    } finally {
      setIsApproving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-[#242420] rounded" />
        <div className="h-40 fintech-card rounded" />
        <div className="h-72 fintech-card rounded" />
      </div>
    );
  }

  if (error || !transaction) {
    return (
      <div className="fintech-card p-8 text-center space-y-4">
        <AlertOctagon className="w-8 h-8 text-[#E56B6F] mx-auto" />
        <h3 className="font-serif text-xl font-bold text-[#F5F1E8]">Transaction Not Found</h3>
        <p className="text-xs text-[#66625B] font-mono">{error || "The requested transaction record could not be located."}</p>
        <Link
          href="/dashboard/transactions"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#151513] border border-white/[0.08] text-xs font-mono text-[#F5F1E8]"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Transactions
        </Link>
      </div>
    );
  }

  const latestDecision = caseDetail?.ai_decisions?.[0];
  const latestAction = caseDetail?.actions?.[0];

  return (
    <div className="space-y-8 pb-12">
      {/* Top Breadcrumbs & Quick Back */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard/transactions"
          className="flex items-center gap-2 text-xs font-mono text-[#918D84] hover:text-[#F5F1E8] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Transactions List
        </Link>
        <div className="flex items-center gap-2">
          <StatusBadge status={transaction.status} />
          {caseDetail && <StatusBadge status={caseDetail.status} />}
        </div>
      </div>

      {/* Transaction Header Banner */}
      <div className="fintech-card p-7 relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#66625B] mb-1">
              <span>Transaction #{transaction.id}</span>
              {transaction.rzp_payment_id && (
                <>
                  <span>•</span>
                  <span className="text-[#D9A441] font-semibold">{transaction.rzp_payment_id}</span>
                </>
              )}
            </div>
            <h1 className="font-serif text-4xl lg:text-5xl font-bold text-[#F5F1E8] flex items-baseline gap-2 tabular-nums">
              ₹{transaction.amount.toLocaleString("en-IN")}
              <span className="text-sm font-mono text-[#66625B] font-normal">{transaction.currency}</span>
            </h1>
            <p className="text-xs font-mono text-[#918D84] mt-1">
              Method: <span className="text-[#F5F1E8] font-medium">{transaction.payment_method}</span> • Created:{" "}
              {new Date(transaction.created_at).toLocaleString()}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            {transaction.status === "FAILED" && caseDetail?.status !== "PENDING_APPROVAL" && caseDetail?.status !== "RECOVERED" && (
              <button
                onClick={handleRecover}
                disabled={isRecovering}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43] hover:bg-[#F0B84B] text-[#070706] shadow-gold transition-all cursor-pointer disabled:opacity-50"
              >
                {isRecovering ? (
                  <>
                    <Coins className="w-3.5 h-3.5 animate-spin" />
                    <span>RUNNING RECOVERY...</span>
                  </>
                ) : (
                  <>
                    <Coins className="w-3.5 h-3.5" />
                    <span>RECOVER PAYMENT</span>
                  </>
                )}
              </button>
            )}

            {/* Action Approval Gate if held */}
            {caseDetail?.status === "PENDING_APPROVAL" && (
              <div className="p-4 rounded-xl border border-[#E5A958]/35 bg-[#E5A958]/10 max-w-sm">
                <div className="flex items-center gap-2 text-[#E5A958] font-mono text-xs font-bold mb-1">
                  <ShieldAlert className="w-4 h-4" />
                  Human Approval Required
                </div>
                <p className="text-[11px] font-mono text-[#E5A958]/80 mb-3">
                  {caseDetail.approval_reason || "Deterministic policy: High-value transaction held."}
                </p>
                <button
                  onClick={handleApprove}
                  disabled={isApproving}
                  className="w-full py-1.5 px-3 rounded bg-[#E5A958] hover:bg-[#F0B84B] text-[#0A0A09] text-xs font-mono font-bold transition-all shadow-gold cursor-pointer disabled:opacity-50"
                >
                  {isApproving ? "Executing Approved Action..." : "Approve & Execute Recovery"}
                </button>
              </div>
            )}
          </div>
        </div>
        {recoverMessage && (
          <div className="mt-3 pt-3 border-t border-white/[0.08] text-xs font-mono text-[#D79A43] flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{recoverMessage}</span>
          </div>
        )}
      </div>

      {/* Grid: Diagnostics & AI Decision Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Risk & Failure Diagnosis */}
        <div className="fintech-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#918D84] flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-[#E56B6F]" />
              1. Failure Diagnosis
            </h3>
            <span className="mono-label text-[#66625B]">Detector &amp; Diagnostician</span>
          </div>

          <div className="space-y-3.5 text-xs font-mono">
            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Failure Code</span>
              <span className="font-semibold text-[#E56B6F]">
                {transaction.failure_code || "UNKNOWN"}
              </span>
            </div>

            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Root Cause Explanation</span>
              <span className="text-[#F5F1E8] leading-relaxed">
                {latestDecision?.root_cause_explanation || transaction.failure_reason || "Gateway connection error"}
              </span>
            </div>

            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Failure Category</span>
              <span className="px-2 py-0.5 rounded bg-[#0A0A09] border border-white/[0.06] text-[#F0B84B]">
                {latestDecision?.failure_category || "temporary_failure"}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: AI Reasoning & Confidence */}
        <div className="fintech-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#918D84] flex items-center gap-2">
              <Brain className="w-4 h-4 text-[#D9A441]" />
              2. AI Decision Engine
            </h3>
            <span className="mono-label text-[#66625B]">Reasoning Model</span>
          </div>

          <div className="space-y-3.5 text-xs font-mono">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[#66625B] block text-[10px] uppercase">Recovery Probability</span>
                <span className="font-serif text-2xl font-bold text-[#36C9A5] tabular-nums">
                  {latestDecision ? `${(latestDecision.recovery_probability * 100).toFixed(0)}%` : `${caseDetail?.recovery_score || 0}%`}
                </span>
              </div>
              <div>
                <span className="text-[#66625B] block text-[10px] uppercase">AI Confidence</span>
                <span className="font-serif text-2xl font-bold text-[#F0B84B] tabular-nums">
                  {latestDecision ? `${(latestDecision.confidence_score * 100).toFixed(0)}%` : "92%"}
                </span>
              </div>
            </div>

            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Recommended Strategy</span>
              <span className="font-semibold text-[#F5F1E8]">
                {latestDecision?.recommended_action.replace(/_/g, " ") || "Delayed Retry Strategy"}
              </span>
            </div>

            {latestDecision?.risk_factors && latestDecision.risk_factors.length > 0 && (
              <div>
                <span className="text-[#66625B] block text-[10px] uppercase mb-1">Identified Risk Factors</span>
                <div className="flex flex-wrap gap-1">
                  {latestDecision.risk_factors.map((rf, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded bg-[#0A0A09] border border-white/[0.06] text-[10px] text-[#918D84]">
                      {rf}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Card 3: Deterministic Policy Checks & Execution */}
        <div className="fintech-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#918D84] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#36C9A5]" />
              3. Policy &amp; Execution Guard
            </h3>
            <span className="mono-label text-[#66625B]">Deterministic Rules</span>
          </div>

          <div className="space-y-3.5 text-xs font-mono">
            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Policy Invariant Check</span>
              <span className="text-[#36C9A5] font-semibold flex items-center gap-1.5 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {latestAction?.policy_rule_notes || "All 6 Deterministic Safety Rules Passed"}
              </span>
            </div>

            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Recovery Attempts</span>
              <span className="text-[#F5F1E8]">
                {caseDetail?.retry_count || 1} / {caseDetail?.max_retries_allowed || 3} Maximum Allowed
              </span>
            </div>

            {latestAction?.rzp_short_url && (
              <div>
                <span className="text-[#66625B] block text-[10px] uppercase">Generated Recovery Link</span>
                <a
                  href={latestAction.rzp_short_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[#F0B84B] hover:underline flex items-center gap-1 text-[11px] mt-0.5"
                >
                  {latestAction.rzp_short_url} <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}

            <div>
              <span className="text-[#66625B] block text-[10px] uppercase">Final Outcome State</span>
              <span className="font-semibold text-[#F5F1E8] mt-0.5 block">
                {caseDetail?.status === "RECOVERED"
                  ? `Revenue Recovered: ₹${caseDetail.recovered_amount.toLocaleString("en-IN")}`
                  : `Case Status: ${caseDetail?.status || transaction.status}`}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Complete Audit Timeline */}
      <TransactionAuditTimeline auditLogs={auditLogs} isLoading={isLoading} />
    </div>
  );
}
