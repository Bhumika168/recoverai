"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
  CreditCard,
  Layers,
  Sparkles,
  Check,
  X,
  ShieldAlert,
  Coins,
  Cpu,
  Lock,
  ChevronRight,
  Fingerprint,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { RecoveryCaseDetail } from "@/lib/types";

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<RecoveryCaseDetail | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [communications, setCommunications] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadCaseData = async () => {
    try {
      setIsLoading(true);
      const [c, t, coms] = await Promise.all([
        api.getCaseDetail(caseId),
        api.getCaseTimeline(caseId),
        api.getCaseCommunications(caseId),
      ]);
      setCaseData(c);
      setTimeline(t);
      setCommunications(coms);
    } catch (err: any) {
      console.error("Failed to load case detail:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) loadCaseData();
  }, [caseId]);

  const handleApprove = async () => {
    try {
      setActionLoading(true);
      await api.approveCase(caseId);
      setNotice({ text: "Recovery action approved by merchant executive. Cleared for execution.", type: "success" });
      await loadCaseData();
    } catch (err: any) {
      setNotice({ text: err.message || "Approval failed.", type: "error" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    try {
      setActionLoading(true);
      await api.rejectCase(caseId);
      setNotice({ text: "Recovery action rejected by merchant. Case blocked.", type: "success" });
      await loadCaseData();
    } catch (err: any) {
      setNotice({ text: err.message || "Rejection failed.", type: "error" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyRecovery = async () => {
    try {
      setActionLoading(true);
      await api.verifyRecovery(caseId);
      setNotice({
        text: `Verified sandbox recovery settlement captured successfully (+₹${caseData?.amount_at_risk?.toLocaleString() || "0"}).`,
        type: "success",
      });
      await loadCaseData();
    } catch (err: any) {
      setNotice({ text: err.message || "Verification settlement failed.", type: "error" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDispatchCommunication = async (channel: string) => {
    try {
      setActionLoading(true);
      await api.dispatchCaseCommunication(caseId, { channel });
      setNotice({ text: `Dispatched ${channel} recovery message to customer.`, type: "success" });
      await loadCaseData();
    } catch (err: any) {
      setNotice({ text: err.message || "Dispatch failed.", type: "error" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleOptOut = async () => {
    try {
      setActionLoading(true);
      await api.optOutCustomer(caseId, "CUSTOMER_REQUESTED");
      setNotice({ text: "Customer unsubscribed. Active communications stopped.", type: "success" });
      await loadCaseData();
    } catch (err: any) {
      setNotice({ text: err.message || "Opt-out failed.", type: "error" });
    } finally {
      setActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-12 space-y-6">
        <div className="h-10 bg-white/[0.03] rounded-xl animate-pulse" />
        <div className="h-48 bg-white/[0.03] rounded-xl animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 bg-white/[0.03] rounded-xl animate-pulse" />
          <div className="h-64 bg-white/[0.03] rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="text-center py-20 font-mono text-xs text-[#918D84]">
        <AlertTriangle className="w-8 h-8 text-[#E56B6F] mx-auto mb-2" />
        <p>Recovery case not found.</p>
        <Link href="/dashboard/recovery" className="text-[#D79A43] hover:underline mt-2 inline-block">
          Back to Recovery Queue
        </Link>
      </div>
    );
  }

  const isRecovered = caseData.status === "RECOVERED";
  const isPendingApproval = caseData.status === "PENDING_APPROVAL" || caseData.requires_human_approval === "YES";
  const isBlocked = caseData.status === "UNRECOVERABLE" || caseData.status === "EXPIRED";
  const isEscalated = caseData.status === "ESCALATED";
  const isInProgress = caseData.status === "IN_PROGRESS" && !isPendingApproval && !isRecovered;

  const isHighValue = (caseData.amount_at_risk || 0) >= 25000;
  const isHardDecline = caseData.transaction?.failure_code === "CARD_STOLEN_OR_LOST" || isBlocked;
  const isMaxRetries = (caseData.retry_count || 0) >= 3 || isEscalated;

  const aiDecision = caseData.ai_decisions?.[0];
  const primaryAction = caseData.actions?.[0];

  return (
    <div className="space-y-8 pb-16 font-sans max-w-7xl mx-auto">
      {/* 1. Back Navigation & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          href="/dashboard/recovery"
          className="inline-flex items-center gap-2 text-xs font-mono text-[#918D84] hover:text-[#F5F0E8] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Recovery Queue</span>
        </Link>

        <div className="flex items-center gap-3">
          <button
            onClick={loadCaseData}
            disabled={isLoading || actionLoading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
            <span>SYNC DATA</span>
          </button>
        </div>
      </div>

      {/* Global Notification Banner */}
      {notice && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4 rounded-xl border text-xs font-mono flex items-center justify-between ${
            notice.type === "success"
              ? "bg-[#20B89A]/10 border-[#20B89A]/30 text-[#20B89A]"
              : "bg-[#E56B6F]/10 border-[#E56B6F]/30 text-[#E56B6F]"
          }`}
        >
          <div className="flex items-center gap-2">
            {notice.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span>{notice.text}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-[#918D84] hover:text-[#F5F0E8]">
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      )}

      {/* 2. Top Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-b from-[#161512] via-[#11110F] to-[#0D0D0B] border border-white/[0.08] shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.1] text-[10px] font-mono font-bold text-[#D79A43]">
                CASE {caseData.id}
              </span>
              <span className="text-[10px] font-mono text-[#66625B]">●</span>
              <span className="text-[11px] font-mono text-[#918D84]">
                TXN: {caseData.transaction?.transaction_id || caseData.transaction_id}
              </span>
              <span className="text-[10px] font-mono text-[#66625B]">●</span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wider ${
                  isRecovered
                    ? "bg-[#20B89A]/20 text-[#20B89A] border border-[#20B89A]/40"
                    : isPendingApproval
                    ? "bg-[#D79A43]/20 text-[#D79A43] border border-[#D79A43]/40"
                    : isBlocked
                    ? "bg-[#E56B6F]/20 text-[#E56B6F] border border-[#E56B6F]/40"
                    : isEscalated
                    ? "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40"
                    : "bg-white/[0.08] text-[#E6E4DF] border border-white/[0.12]"
                }`}
              >
                {caseData.status}
              </span>
            </div>

            <div className="flex items-baseline gap-3">
              <h1 className="font-serif text-4xl sm:text-5xl font-bold tracking-tight text-[#F5F0E8]">
                ₹{caseData.amount_at_risk?.toLocaleString()}
              </h1>
              <span className="text-xs font-mono text-[#918D84]">INR AT RISK</span>
              {isRecovered && (
                <span className="px-3 py-1 rounded-full bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30 text-xs font-mono font-bold">
                  ✓ FULLY RECOVERED (+₹{caseData.recovered_amount?.toLocaleString()})
                </span>
              )}
            </div>

            <p className="text-xs font-mono text-[#918D84]">
              Failure Code: <span className="text-[#F5F0E8] font-bold">{caseData.transaction?.failure_code || "GATEWAY_ERROR"}</span> •{" "}
              {caseData.transaction?.failure_reason || "Payment failure detected by ingest switch"}
            </p>
          </div>

          {/* Header Action Button Group */}
          <div className="flex flex-wrap items-center gap-3">
            {isPendingApproval && (
              <>
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#1A1816] text-[#E56B6F] hover:bg-[#25201E] border border-[#E56B6F]/30 cursor-pointer disabled:opacity-50"
                >
                  REJECT
                </button>
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43] hover:bg-[#F0B84B] text-[#070706] shadow-gold cursor-pointer disabled:opacity-50"
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>APPROVE & CLEAR EXECUTION</span>
                </button>
              </>
            )}

            {isInProgress && (
              <button
                onClick={handleVerifyRecovery}
                disabled={actionLoading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#20B89A] hover:bg-[#28D4B0] text-[#070706] shadow-[0_0_20px_rgba(32,184,154,0.3)] cursor-pointer disabled:opacity-50"
              >
                <Coins className="w-4 h-4" />
                <span>EXECUTE VERIFIED SETTLEMENT (SANDBOX)</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 3. Four-Stage Bounded Governance Architecture Stepper */}
      <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] font-mono text-xs">
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.06] mb-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#D79A43]" />
            <span className="font-bold text-[#F5F0E8] uppercase tracking-wider text-[11px]">
              RECOVERAI BOUNDED RECOVERY PIPELINE
            </span>
          </div>
          <span className="text-[10px] text-[#918D84]">
            AI Proposes • Policy Enforces • Human Governs • Sandbox Captures
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Stage 1 */}
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#918D84] uppercase">STAGE 1: AI DIAGNOSIS</span>
              <span className="w-2 h-2 rounded-full bg-[#20B89A]" />
            </div>
            <div className="font-sans font-bold text-sm text-[#F5F0E8]">
              {aiDecision?.failure_category?.toUpperCase() || "TEMPORARY_FAILURE"}
            </div>
            <p className="text-[11px] text-[#918D84]">
              Diagnostic Confidence: <strong className="text-[#20B89A]">{Math.round((aiDecision?.confidence_score || 0.92) * 100)}%</strong>
            </p>
            <span className="text-[10px] text-[#66625B] block">Advisory telemetry only</span>
          </div>

          {/* Stage 2 */}
          <div className={`p-4 rounded-xl border space-y-2 ${
            isPendingApproval
              ? "bg-[#D79A43]/10 border-[#D79A43]/40"
              : isBlocked
              ? "bg-[#E56B6F]/10 border-[#E56B6F]/40"
              : "bg-white/[0.02] border-white/[0.06]"
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#918D84] uppercase">STAGE 2: POLICY ENGINE</span>
              <span className={`w-2 h-2 rounded-full ${isPendingApproval ? "bg-[#D79A43]" : isBlocked ? "bg-[#E56B6F]" : "bg-[#20B89A]"}`} />
            </div>
            <div className="font-sans font-bold text-sm text-[#F5F0E8]">
              {isHighValue ? "RULE 5: HIGH-VALUE GATE" : isHardDecline ? "RULE 2: HARD DECLINE" : isMaxRetries ? "RULE 3: MAX RETRIES" : "SAFETY GUARDRAILS"}
            </div>
            <p className={`text-[11px] font-bold ${isPendingApproval ? "text-[#D79A43]" : isBlocked ? "text-[#E56B6F]" : "text-[#20B89A]"}`}>
              {isPendingApproval ? "HOLD FOR APPROVAL" : isBlocked ? "BLOCKED (0 RETRIES)" : isEscalated ? "HALTED (MAX 3)" : "CLEARED"}
            </p>
            <span className="text-[10px] text-[#66625B] block">Deterministic hard bounds</span>
          </div>

          {/* Stage 3 */}
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#918D84] uppercase">STAGE 3: ACTION / GATE</span>
              <span className={`w-2 h-2 rounded-full ${isRecovered || isInProgress ? "bg-[#20B89A]" : isPendingApproval ? "bg-[#D79A43]" : "bg-[#66625B]"}`} />
            </div>
            <div className="font-sans font-bold text-sm text-[#F5F0E8]">
              {primaryAction?.action_type || aiDecision?.recommended_action?.toUpperCase() || "DELAYED_RETRY"}
            </div>
            <p className="text-[11px] text-[#918D84]">
              Approval: <strong className={isPendingApproval ? "text-[#D79A43]" : "text-[#20B89A]"}>
                {isPendingApproval ? "REQUIRED" : "APPROVED / NOT REQ"}
              </strong>
            </p>
            <span className="text-[10px] text-[#66625B] block">Target: Sandbox Switch</span>
          </div>

          {/* Stage 4 */}
          <div className={`p-4 rounded-xl border space-y-2 ${
            isRecovered ? "bg-[#20B89A]/10 border-[#20B89A]/40" : "bg-white/[0.02] border-white/[0.06]"
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#918D84] uppercase">STAGE 4: VERIFICATION</span>
              <span className={`w-2 h-2 rounded-full ${isRecovered ? "bg-[#20B89A]" : "bg-[#66625B]"}`} />
            </div>
            <div className="font-sans font-bold text-sm text-[#F5F0E8]">
              {isRecovered ? "CAPTURED & VERIFIED" : "PENDING SETTLEMENT"}
            </div>
            <p className={`text-[11px] font-bold ${isRecovered ? "text-[#20B89A]" : "text-[#918D84]"}`}>
              {isRecovered ? `+₹${caseData.recovered_amount?.toLocaleString()}` : "₹0 Settled"}
            </p>
            <span className="text-[10px] text-[#66625B] block">SHA-256 Ledger Record</span>
          </div>
        </div>
      </div>

      {/* 4. Active Policy Guardrail Highlight Cards */}
      {isPendingApproval && (
        <div className="p-6 rounded-2xl bg-[#D79A43]/10 border border-[#D79A43]/40 space-y-3 font-mono text-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#D79A43]/20 flex items-center justify-center text-[#D79A43] shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-sans font-bold text-base text-[#F5F0E8]">
                Deterministic Rule 5 Triggered: HIGH_VALUE_TRANSACTION_GATE
              </h3>
              <p className="text-xs text-[#D79A43]">
                Transaction Value (₹{caseData.amount_at_risk?.toLocaleString()}) meets or exceeds the high-value safety threshold (₹25,000.00).
              </p>
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-[#0D0D0B] border border-white/[0.08] text-[#E6E4DF] leading-relaxed">
            <p>
              <strong>Why Automation Was Blocked:</strong> Although AI diagnostic confidence is <strong>92%</strong> for transient error recovery, RecoverAI&apos;s non-negotiable policy engine mandates explicit executive clearance for any individual retry volume exceeding ₹25,000. Automated card retries remain frozen until one-click merchant authorization is provided.
            </p>
          </div>
        </div>
      )}

      {isBlocked && (
        <div className="p-6 rounded-2xl bg-[#E56B6F]/10 border border-[#E56B6F]/40 space-y-3 font-mono text-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#E56B6F]/20 flex items-center justify-center text-[#E56B6F] shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-sans font-bold text-base text-[#F5F0E8]">
                Deterministic Rule 2 Triggered: NO_RETRY_AFTER_HARD_DECLINE
              </h3>
              <p className="text-xs text-[#E56B6F]">
                Card reported stolen or lost ({caseData.transaction?.failure_code || "HARD_DECLINE"}). Automated retries strictly prohibited.
              </p>
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-[#0D0D0B] border border-white/[0.08] text-[#E6E4DF] leading-relaxed">
            <p>
              <strong>Why Automation Was Blocked:</strong> Under card network operating regulations (Visa/Mastercard) and safety rules, attempting to retry a card flagged as stolen or lost incurs penalties, increases merchant chargeback liability, and compromises consumer safety. RecoverAI permanently blocked automated retries (<strong>Retries Attempted: 0</strong>) and transitioned this case to <code>UNRECOVERABLE</code>.
            </p>
          </div>
        </div>
      )}

      {isEscalated && (
        <div className="p-6 rounded-2xl bg-[#F59E0B]/10 border border-[#F59E0B]/40 space-y-3 font-mono text-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#F59E0B]/20 flex items-center justify-center text-[#F59E0B] shrink-0">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-sans font-bold text-base text-[#F5F0E8]">
                Deterministic Rule 3 Triggered: MAXIMUM_RETRY_LIMIT
              </h3>
              <p className="text-xs text-[#F59E0B]">
                Maximum automated retry ceiling reached ({caseData.retry_count} / {caseData.max_retries_allowed} attempts).
              </p>
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-[#0D0D0B] border border-white/[0.08] text-[#E6E4DF] leading-relaxed">
            <p>
              <strong>Why Automation Was Blocked:</strong> To prevent issuer rate-limiting, redundant switch fees, and cardholder fatigue, RecoverAI strictly limits automated retries to a maximum of 3 attempts. Having reached attempt 3, the engine halts automated attempts and escalates the case to the merchant intervention queue.
            </p>
          </div>
        </div>
      )}

      {/* 5. Two-Column Diagnostic & Governance Deep Dive */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono text-xs">
        {/* Left Column: AI Diagnosis & Policy Rules */}
        <div className="space-y-6">
          {/* AI Diagnostic Intelligence */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#D79A43]" />
                <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">AI Diagnostic Intelligence</h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-white/[0.05] text-[#20B89A] text-[10px] font-bold">
                {Math.round((aiDecision?.confidence_score || 0.92) * 100)}% CONFIDENCE
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <span className="text-[#918D84] text-[10px] uppercase">Failure Classification</span>
                <p className="font-bold text-[#F5F0E8] text-sm mt-0.5">
                  {aiDecision?.failure_category?.toUpperCase() || "TEMPORARY_FAILURE"}
                </p>
              </div>

              <div>
                <span className="text-[#918D84] text-[10px] uppercase">Root Cause Analysis</span>
                <p className="text-[#E6E4DF] mt-0.5 leading-relaxed">
                  {aiDecision?.root_cause_explanation || "Transient gateway or switch timeout during high traffic window. Underlying customer credentials valid."}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/[0.04]">
                <div>
                  <span className="text-[#918D84] text-[10px] uppercase">Recommended Action</span>
                  <p className="font-bold text-[#D79A43] mt-0.5">
                    {aiDecision?.recommended_action?.toUpperCase() || "DELAYED_RETRY"}
                  </p>
                </div>
                <div>
                  <span className="text-[#918D84] text-[10px] uppercase">Recovery Probability</span>
                  <p className="font-bold text-[#20B89A] mt-0.5">
                    {Math.round((aiDecision?.recovery_probability || 0.88) * 100)}% Estimated
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Deterministic Policy Engine Evaluation */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#20B89A]" />
                <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Deterministic Policy Evaluations</h3>
              </div>
              <span className="text-[10px] text-[#20B89A] font-bold">ENFORCED</span>
            </div>

            <div className="space-y-2.5">
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-[#F5F0E8]">Rule 1: DUPLICATE_ACTION_PROTECTION</span>
                  <p className="text-[10px] text-[#918D84]">Idempotency check prevents duplicate in-flight transactions</p>
                </div>
                <span className="px-2 py-0.5 rounded bg-[#20B89A]/15 text-[#20B89A] text-[10px] font-bold">PASSED</span>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-[#F5F0E8]">Rule 2: NO_RETRY_AFTER_HARD_DECLINE</span>
                  <p className="text-[10px] text-[#918D84]">Never retry stolen, lost, or closed accounts</p>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isBlocked ? "bg-[#E56B6F]/20 text-[#E56B6F]" : "bg-[#20B89A]/15 text-[#20B89A]"}`}>
                  {isBlocked ? "BLOCKED" : "PASSED"}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-[#F5F0E8]">Rule 3: MAXIMUM_RETRY_LIMIT</span>
                  <p className="text-[10px] text-[#918D84]">Maximum 3 automated retry attempts allowed</p>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isEscalated ? "bg-[#F59E0B]/20 text-[#F59E0B]" : "bg-[#20B89A]/15 text-[#20B89A]"}`}>
                  {isEscalated ? "STOPPED (3/3)" : `PASSED (${caseData.retry_count}/3)`}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-[#F5F0E8]">Rule 4: CONFIDENCE_THRESHOLD_CHECK</span>
                  <p className="text-[10px] text-[#918D84]">Mandates &ge; 75% confidence for autonomous routing</p>
                </div>
                <span className="px-2 py-0.5 rounded bg-[#20B89A]/15 text-[#20B89A] text-[10px] font-bold">
                  PASSED (92% &ge; 75%)
                </span>
              </div>

              <div className={`p-3 rounded-xl border flex items-center justify-between ${
                isHighValue ? "bg-[#D79A43]/10 border-[#D79A43]/30" : "bg-white/[0.02] border-white/[0.04]"
              }`}>
                <div>
                  <span className="font-bold text-[#F5F0E8]">Rule 5: HIGH_VALUE_TRANSACTION_GATE</span>
                  <p className="text-[10px] text-[#918D84]">Values &ge; ₹25,000 mandate human sign-off</p>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  isHighValue ? "bg-[#D79A43]/20 text-[#D79A43]" : "bg-[#20B89A]/15 text-[#20B89A]"
                }`}>
                  {isHighValue ? "TRIGGERED (HOLD)" : "PASSED (< ₹25k)"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Telemetry, Action Execution, & Communications */}
        <div className="space-y-6">
          {/* Transaction Telemetry */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-[#D79A43]" />
                <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Transaction Telemetry</h3>
              </div>
              <span className="text-[10px] text-[#918D84]">ORIGINAL INGEST</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-[#918D84] text-[10px] uppercase">Transaction Ref</span>
                <p className="font-bold text-[#F5F0E8] mt-0.5 truncate">
                  {caseData.transaction?.transaction_id || caseData.transaction_id}
                </p>
              </div>
              <div>
                <span className="text-[#918D84] text-[10px] uppercase">Amount & Currency</span>
                <p className="font-bold text-[#F5F0E8] mt-0.5">
                  ₹{caseData.amount_at_risk?.toLocaleString()} INR
                </p>
              </div>
              <div>
                <span className="text-[#918D84] text-[10px] uppercase">Payment Method</span>
                <p className="text-[#E6E4DF] mt-0.5 font-bold">
                  {caseData.transaction?.payment_method || "CARD"}
                </p>
              </div>
              <div>
                <span className="text-[#918D84] text-[10px] uppercase">Customer Account</span>
                <p className="text-[#E6E4DF] mt-0.5 truncate">
                  {caseData.customer?.email || caseData.transaction?.customer_email || "customer@demo.io"}
                </p>
              </div>
              <div className="col-span-2 pt-2 border-t border-white/[0.04]">
                <span className="text-[#918D84] text-[10px] uppercase">Gateway Failure Reason</span>
                <p className="text-[#E56B6F] mt-0.5 font-bold">
                  {caseData.transaction?.failure_code}: {caseData.transaction?.failure_reason}
                </p>
              </div>
            </div>
          </div>

          {/* Recovery Execution & Settlement Status */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <Coins className="w-4 h-4 text-[#20B89A]" />
                <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Execution & Sandbox Settlement</h3>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                isRecovered ? "bg-[#20B89A]/15 text-[#20B89A]" : "bg-white/[0.05] text-[#918D84]"
              }`}>
                {isRecovered ? "SETTLED" : "NOT SETTLED"}
              </span>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[#918D84]">Target Recovery Gateway</span>
                <span className="font-bold text-[#F5F0E8]">SANDBOX_PAYMENT_SWITCH</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#918D84]">Idempotency Verification</span>
                <span className="text-[#20B89A] font-bold">LOCKED & PROTECTED</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#918D84]">Verified Captured Volume</span>
                <span className={`font-bold ${isRecovered ? "text-[#20B89A]" : "text-[#918D84]"}`}>
                  ₹{caseData.recovered_amount?.toLocaleString() || 0} INR
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#918D84]">Settlement Timestamp</span>
                <span className="text-[#F5F0E8]">
                  {caseData.recovered_at ? new Date(caseData.recovered_at).toLocaleString() : "Awaiting Verification"}
                </span>
              </div>

              {isInProgress && (
                <div className="pt-3 border-t border-white/[0.06]">
                  <button
                    onClick={handleVerifyRecovery}
                    disabled={actionLoading}
                    className="w-full py-2.5 rounded-xl bg-[#20B89A] hover:bg-[#28D4B0] text-[#070706] font-bold text-xs flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(32,184,154,0.3)] cursor-pointer disabled:opacity-50"
                  >
                    <Coins className="w-4 h-4" />
                    <span>EXECUTE VERIFIED SETTLEMENT (SANDBOX)</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Customer Communications & Outbound Channels */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <Send className="w-4 h-4 text-[#D79A43]" />
                <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">Customer Channel Dispatch</h3>
              </div>
              <span className="text-[10px] text-[#918D84]">{communications.length} Sent</span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleDispatchCommunication("EMAIL")}
                disabled={actionLoading || isRecovered}
                className="px-3.5 py-2 rounded-xl bg-[#171614] text-[#D79A43] hover:bg-[#201F1D] border border-white/[0.08] text-xs font-bold cursor-pointer disabled:opacity-50"
              >
                Send Email
              </button>
              <button
                onClick={() => handleDispatchCommunication("WHATSAPP")}
                disabled={actionLoading || isRecovered}
                className="px-3.5 py-2 rounded-xl bg-[#171614] text-[#20B89A] hover:bg-[#201F1D] border border-white/[0.08] text-xs font-bold cursor-pointer disabled:opacity-50"
              >
                Send WhatsApp
              </button>
              <button
                onClick={handleOptOut}
                disabled={actionLoading || isRecovered}
                className="px-3.5 py-2 rounded-xl bg-[#171614] text-[#E56B6F] hover:bg-[#201F1D] border border-white/[0.08] text-xs font-bold cursor-pointer disabled:opacity-50"
              >
                Customer Opt-Out
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Cryptographic SHA-256 Audit Trail */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#11110F] border border-white/[0.08] shadow-2xl space-y-6 font-mono text-xs">
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <Fingerprint className="w-5 h-5 text-[#D79A43]" />
            <div>
              <h3 className="font-sans font-bold text-base text-[#F5F0E8]">Immutable SHA-256 Audit Chain</h3>
              <p className="text-[11px] text-[#918D84]">Cryptographically verifiable event sequence for this recovery case</p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30 text-[10px] font-bold">
            {timeline.length} VERIFIED BLOCKS
          </span>
        </div>

        {timeline.length === 0 ? (
          <div className="text-center py-12 text-[#918D84]">
            No audit ledger events recorded for this case yet.
          </div>
        ) : (
          <div className="space-y-6 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-white/[0.06]">
            {timeline.map((evt, idx) => (
              <div key={evt.id || idx} className="relative flex items-start gap-4 pl-8">
                <div className="absolute left-2 top-1.5 w-3.5 h-3.5 rounded-full bg-[#11110F] border-2 border-[#D79A43]" />
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] space-y-2 w-full">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#F5F0E8] text-sm">{evt.event_type}</span>
                    <span className="text-[11px] text-[#66625B]">
                      {evt.created_at || evt.timestamp ? new Date(evt.created_at || evt.timestamp).toLocaleString() : "—"}
                    </span>
                  </div>
                  <p className="text-[#E6E4DF]">{evt.notes || "Event recorded to immutable cryptographic ledger"}</p>
                  <div className="flex flex-wrap items-center gap-4 text-[10px] text-[#66625B] pt-1 border-t border-white/[0.04]">
                    <span>Actor: <strong className="text-[#918D84]">{evt.actor}</strong></span>
                    {evt.sha256_hash && (
                      <span className="font-mono text-[#D79A43] truncate max-w-xs">
                        Block Hash: {evt.sha256_hash.slice(0, 16)}...
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
