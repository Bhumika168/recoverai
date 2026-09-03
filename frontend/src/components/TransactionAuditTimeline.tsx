"use client";

import React from "react";
import {
  Brain,
  ShieldCheck,
  Send,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Fingerprint,
  ShieldAlert,
} from "lucide-react";
import { AuditLog } from "@/lib/types";

interface TimelineProps {
  auditLogs: AuditLog[];
  isLoading?: boolean;
}

export function TransactionAuditTimeline({ auditLogs, isLoading }: TimelineProps) {
  if (isLoading) {
    return (
      <div className="fintech-card p-6 space-y-4 animate-pulse">
        <div className="h-5 w-40 bg-[#242420] rounded" />
        <div className="h-20 bg-[#1A1A18] rounded" />
        <div className="h-20 bg-[#1A1A18] rounded" />
      </div>
    );
  }

  if (!auditLogs || auditLogs.length === 0) {
    return (
      <div className="fintech-card p-6 text-center text-[#66625B] text-xs font-mono">
        No audit entries recorded for this transaction.
      </div>
    );
  }

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case "RISK_DETECTED":
        return <AlertOctagon className="w-4 h-4 text-[#E5A958]" />;
      case "FAILURE_DIAGNOSED":
        return <Brain className="w-4 h-4 text-[#D9A441]" />;
      case "STRATEGY_DECIDED":
        return <Brain className="w-4 h-4 text-[#F0B84B]" />;
      case "POLICY_EVALUATED":
        return <ShieldCheck className="w-4 h-4 text-blue-400" />;
      case "ACTION_EXECUTED":
        return <Send className="w-4 h-4 text-[#D9A441]" />;
      case "RECOVERY_VERIFIED":
      case "PAYMENT_LINK_PAID":
        return <CheckCircle2 className="w-4 h-4 text-[#36C9A5]" />;
      case "POLICY_REJECTED":
        return <ShieldAlert className="w-4 h-4 text-[#E56B6F]" />;
      default:
        return <Clock className="w-4 h-4 text-[#918D84]" />;
    }
  };

  return (
    <div className="fintech-card p-6">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/[0.06]">
        <div>
          <span className="mono-label text-[#D9A441] block mb-1">State Machine</span>
          <h3 className="font-serif text-2xl font-bold text-[#F5F1E8] flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-[#D9A441]" />
            Immutable Audit Ledger &amp; Decision Trail
          </h3>
          <p className="text-xs text-[#66625B] font-mono mt-0.5">
            Cryptographically chained SHA-256 state transitions
          </p>
        </div>
        <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#36C9A5]/10 text-[#36C9A5] border border-[#36C9A5]/25">
          SHA-256 Validated
        </span>
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-[1px] before:bg-white/[0.08]">
        {auditLogs.map((log) => {
          const dt = new Date(log.created_at || log.timestamp_iso);
          return (
            <div key={log.id} className="relative group">
              {/* Node Beacon */}
              <div className="absolute -left-[27px] top-1 w-6 h-6 rounded-full bg-[#0A0A09] border border-white/[0.12] flex items-center justify-center shadow-sm group-hover:border-[#D9A441]/60 transition-colors">
                {getEventIcon(log.event_type)}
              </div>

              {/* Event Content */}
              <div className="fintech-card-elevated p-4 hover:border-[#D9A441]/30 transition-all">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <span className="text-xs font-mono font-bold text-[#F5F1E8]">
                      {log.event_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-[11px] font-mono text-[#66625B] ml-2">
                      by <span className="text-[#F0B84B]">{log.actor}</span>
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#66625B] whitespace-nowrap">
                    {dt.toLocaleDateString()} {dt.toLocaleTimeString()}
                  </span>
                </div>

                {log.notes && (
                  <p className="text-xs text-[#918D84] font-mono mb-2.5 leading-relaxed">
                    {log.notes}
                  </p>
                )}

                {/* State Transition Diff */}
                {log.state_after && Object.keys(log.state_after).length > 0 && (
                  <div className="bg-[#0A0A09] rounded p-2.5 border border-white/[0.06] text-[11px] font-mono text-[#918D84] overflow-x-auto">
                    <div className="text-[10px] text-[#66625B] uppercase tracking-wider mb-1 font-semibold">
                      State Mutation:
                    </div>
                    <pre className="text-[#918D84] leading-tight whitespace-pre-wrap">
                      {JSON.stringify(log.state_after, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Cryptographic Hash Badge */}
                <div className="mt-2.5 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-[#66625B]">
                  <span className="truncate max-w-xs">
                    SHA256: <span className="text-[#918D84]">{log.sha256_hash.slice(0, 24)}...</span>
                  </span>
                  <span className="text-[#66625B]">
                    Prev: {log.prev_hash ? `${log.prev_hash.slice(0, 10)}...` : "GENESIS"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
