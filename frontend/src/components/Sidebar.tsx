"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Receipt,
  RotateCcw,
  ShieldCheck,
  Zap,
  ArrowUpRight,
  CreditCard,
  Megaphone,
  Bell,
  Settings as SettingsIcon,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    {
      name: "OVERVIEW",
      href: "/dashboard",
      icon: LayoutDashboard,
      active: pathname === "/dashboard",
    },
    {
      name: "TRANSACTIONS",
      href: "/dashboard/transactions",
      icon: Receipt,
      active: pathname.startsWith("/dashboard/transactions"),
    },
    {
      name: "RECOVERY",
      href: "/dashboard/recovery",
      icon: RotateCcw,
      active: pathname === "/dashboard/recovery" || pathname.startsWith("/dashboard/recovery/cases"),
    },
    {
      name: "CAMPAIGNS",
      href: "/dashboard/recovery/campaigns",
      icon: Megaphone,
      active: pathname.startsWith("/dashboard/recovery/campaigns") || pathname.startsWith("/dashboard/recovery/templates"),
    },
    {
      name: "AUDIT LEDGER",
      href: "/dashboard/audit",
      icon: ShieldCheck,
      active: pathname.startsWith("/dashboard/audit"),
    },
    {
      name: "INTEGRATIONS",
      href: "/dashboard/settings/integrations",
      icon: CreditCard,
      active: pathname.startsWith("/dashboard/settings/integrations"),
    },
    {
      name: "NOTIFICATIONS",
      href: "/dashboard/notifications",
      icon: Bell,
      active: pathname.startsWith("/dashboard/notifications"),
    },
    {
      name: "SETTINGS",
      href: "/dashboard/settings",
      icon: SettingsIcon,
      active: pathname === "/dashboard/settings",
    },
  ];

  return (
    <aside className="w-60 bg-[#0A0A09] border-r border-white/[0.07] flex flex-col justify-between h-screen sticky top-0 z-30 select-none">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-white/[0.07]">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43] transition-all group-hover:scale-105">
              <Zap className="w-4 h-4 fill-[#D79A43]" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-serif text-lg font-bold text-[#F5F0E8] tracking-tight">
                  Recover<span className="text-[#D79A43] italic font-normal">AI</span>
                </span>
                <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-[#171614] text-[#918D84] border border-white/[0.08]">
                  v2.4
                </span>
              </div>
              <p className="text-[10px] font-mono text-[#66625B]">Revenue Recovery Engine</p>
            </div>
          </Link>
        </div>

        {/* Navigation Items */}
        <nav className="p-3.5 space-y-1.5">
          <div className="px-3 pt-2 pb-1 text-[10px] font-mono uppercase tracking-widest text-[#66625B]">
            System Modules
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono transition-all ${
                  item.active
                    ? "bg-[#D79A43]/[0.08] text-[#D79A43] border border-[#D79A43]/35 font-medium shadow-[0_0_15px_rgba(215,154,67,0.1)]"
                    : "text-[#918D84] hover:text-[#F5F0E8] hover:bg-[#141412] border border-transparent"
                }`}
              >
                <Icon className={`w-4 h-4 ${item.active ? "text-[#D79A43]" : "text-[#66625B]"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-white/[0.07] space-y-3">
        <div className="p-3 rounded-xl bg-[#11110F] border border-white/[0.07]">
          <div className="flex items-center gap-2 text-[11px] font-mono text-[#20B89A] font-semibold mb-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#20B89A] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#20B89A]" />
            </span>
            <span>RECOVERAI ENGINE ONLINE</span>
          </div>
          <div className="space-y-1 text-[10px] font-mono text-[#918D84]">
            <div className="flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-[#20B89A]" />
              <span>Policy guardrails active</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-[#20B89A]" />
              <span>Payment Provider connected</span>
            </div>
          </div>
        </div>

        <Link
          href="/"
          className="flex items-center justify-between px-2.5 py-1.5 text-[11px] font-mono text-[#918D84] hover:text-[#D79A43] transition-colors"
        >
          <span>Marketing Site</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </aside>
  );
}
