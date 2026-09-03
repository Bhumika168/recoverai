"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { RefreshCw, User as UserIcon, LogOut, Settings as SettingsIcon, Building2, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface NavbarProps {
  onDataRefresh?: () => void;
}

export function Navbar({ onDataRefresh }: NavbarProps) {
  const { user, organization, logout } = useAuth();
  const [isSeeding, setIsSeeding] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleRefresh = async () => {
    try {
      setIsSeeding(true);
      if (onDataRefresh) await onDataRefresh();
      setFeedback("Synced with ledger");
      setTimeout(() => setFeedback(null), 3000);
    } catch {
      setFeedback("Sync failed");
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      setIsSeeding(false);
    }
  };

  // Close menu on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="h-14 border-b border-white/[0.07] bg-[#070706]/90 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-30 select-none">
      {/* Left: Live Gateway Telemetry Engine */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5 text-xs font-mono">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#20B89A] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#20B89A]" />
          </span>
          <span className="text-[#20B89A] font-bold tracking-wider">LIVE GATEWAY ENGINE</span>
          <span className="text-white/20">•</span>
          <span className="text-[#918D84]">{organization?.name || "RecoverAI Workspace"}</span>
        </div>
      </div>

      {/* Right: Sync & User Menu */}
      <div className="flex items-center gap-3.5">
        {feedback && (
          <span className="text-xs font-mono text-[#D79A43] bg-[#D79A43]/10 border border-[#D79A43]/30 px-2.5 py-0.5 rounded-lg">
            {feedback}
          </span>
        )}

        <button
          onClick={handleRefresh}
          disabled={isSeeding}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium text-[#918D84] hover:text-[#F5F0E8] bg-[#11110F] border border-white/[0.08] hover:border-[#D79A43]/40 transition-all shadow-sm cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? "animate-spin text-[#D79A43]" : ""}`} />
          <span>{isSeeding ? "SYNCING..." : "SYNC DATA"}</span>
        </button>

        <div className="h-4 w-[1px] bg-white/[0.08]" />

        {/* User Menu Trigger */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#11110F] border border-white/[0.08] hover:border-[#D79A43]/40 text-xs font-mono text-[#F5F0E8] transition-all cursor-pointer"
          >
            <div className="w-5 h-5 rounded-full bg-[#D79A43]/20 border border-[#D79A43]/40 flex items-center justify-center text-[10px] text-[#D79A43] font-bold">
              {user?.full_name?.charAt(0) || "A"}
            </div>
            <div className="flex flex-col text-left leading-tight hidden sm:block">
              <span className="text-[11px] font-bold truncate max-w-[120px]">
                {user?.full_name || "Operator"}
              </span>
              <span className="text-[9px] text-[#66625B] truncate max-w-[120px]">
                {organization?.name || "Workspace"}
              </span>
            </div>
            <ChevronDown className="w-3 h-3 text-[#66625B]" />
          </button>

          {/* Dropdown Menu */}
          {isMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] py-2 z-50 font-mono text-xs backdrop-blur-xl">
              <div className="px-4 py-2.5 border-b border-white/[0.06]">
                <span className="text-[10px] text-[#66625B] uppercase block">Signed in as</span>
                <span className="text-xs font-bold text-[#F5F0E8] block truncate">
                  {user?.full_name || "Operator"}
                </span>
                <span className="text-[10px] text-[#918D84] block truncate">
                  {user?.email || "operator@recoverai.local"}
                </span>
                <div className="mt-1.5 pt-1.5 border-t border-white/[0.04] flex items-center justify-between text-[10px]">
                  <span className="text-[#66625B]">Org: {organization?.slug || "workspace"}</span>
                  <span className="text-[#20B89A] font-bold">{organization?.role || "OWNER"}</span>
                </div>
              </div>

              <div className="py-1">
                <Link
                  href="/dashboard/settings"
                  onClick={() => setIsMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2 text-[#918D84] hover:text-[#F5F0E8] hover:bg-white/[0.04] transition-colors"
                >
                  <UserIcon className="w-3.5 h-3.5 text-[#D79A43]" />
                  <span>Profile & Team</span>
                </Link>

                <Link
                  href="/dashboard/settings"
                  onClick={() => setIsMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2 text-[#918D84] hover:text-[#F5F0E8] hover:bg-white/[0.04] transition-colors"
                >
                  <SettingsIcon className="w-3.5 h-3.5 text-[#20B89A]" />
                  <span>Organization Settings</span>
                </Link>
              </div>

              <div className="pt-1 border-t border-white/[0.06]">
                <button
                  onClick={async () => {
                    setIsMenuOpen(false);
                    await logout();
                  }}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-[#E56B6F] hover:bg-[#E56B6F]/10 transition-colors text-left cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Log out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
