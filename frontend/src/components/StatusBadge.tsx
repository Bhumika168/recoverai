import React from "react";
import { CaseStatus, TransactionStatus } from "@/lib/types";

interface StatusBadgeProps {
  status: CaseStatus | TransactionStatus | string;
  className?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, className = "", size = "md" }: StatusBadgeProps) {
  const statusStr = String(status).toUpperCase();

  let styles = "bg-[#1A1A18] text-[#918D84] border-white/[0.08]";
  let dotColor = "bg-[#918D84]";

  switch (statusStr) {
    case "RECOVERED":
    case "CAPTURED":
    case "COMPLETED":
      styles = "bg-[#36C9A5]/10 text-[#36C9A5] border-[#36C9A5]/25";
      dotColor = "bg-[#36C9A5]";
      break;
    case "IN_PROGRESS":
    case "SCHEDULED":
    case "AUTOMATIC":
    case "AUTHORIZED":
      styles = "bg-[#D9A441]/10 text-[#F0B84B] border-[#D9A441]/25";
      dotColor = "bg-[#D9A441]";
      break;
    case "PENDING_APPROVAL":
      styles = "bg-[#E5A958]/15 text-[#E5A958] border-[#E5A958]/35 animate-pulse";
      dotColor = "bg-[#E5A958]";
      break;
    case "ESCALATED":
    case "BLOCKED":
      styles = "bg-[#E56B6F]/12 text-[#E56B6F] border-[#E56B6F]/30";
      dotColor = "bg-[#E56B6F]";
      break;
    case "UNRECOVERABLE":
    case "FAILED":
    case "CANCELLED":
    case "REJECTED":
      styles = "bg-[#E56B6F]/10 text-[#E56B6F]/90 border-[#E56B6F]/20";
      dotColor = "bg-[#E56B6F]";
      break;
    case "OPEN":
    case "CREATED":
      styles = "bg-blue-500/10 text-blue-300 border-blue-500/20";
      dotColor = "bg-blue-400";
      break;
    case "ABANDONED":
      styles = "bg-purple-500/10 text-purple-300 border-purple-500/20";
      dotColor = "bg-purple-400";
      break;
  }

  const padding = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md font-mono font-medium border ${padding} ${styles} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span>{statusStr.replace(/_/g, " ")}</span>
    </span>
  );
}
