"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldAlert,
  Check,
  RefreshCw,
  ArrowRight,
  Inbox,
} from "lucide-react";
import { api } from "@/lib/api";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");

  const loadNotifications = async () => {
    try {
      setIsLoading(true);
      const res = await api.getNotifications(100);
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch (err: any) {
      console.error("Failed to load notifications:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const handleMarkRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all read:", err);
    }
  };

  const filteredNotifications = notifications.filter((n) => {
    if (activeFilter === "ALL") return true;
    if (activeFilter === "UNREAD") return !n.is_read;
    return n.severity === activeFilter;
  });

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
            <span>OPERATIONAL ALERTS</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
            Merchant Notifications
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Real-time alerts for recovered revenue, high-value approval gates, and exhausted campaigns.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#D79A43] hover:bg-[#171614] border border-[#D79A43]/30 transition-colors cursor-pointer"
            >
              <Check className="w-3.5 h-3.5" />
              <span>MARK ALL AS READ</span>
            </button>
          )}

          <button
            onClick={loadNotifications}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs font-mono">
        {[
          { key: "ALL", label: "ALL ALERTS" },
          { key: "UNREAD", label: `UNREAD (${unreadCount})` },
          { key: "CRITICAL", label: "CRITICAL" },
          { key: "WARNING", label: "WARNINGS" },
          { key: "INFO", label: "INFO" },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setActiveFilter(f.key)}
            className={`px-3.5 py-2 rounded-xl border transition-all cursor-pointer ${
              activeFilter === f.key
                ? "bg-[#D79A43]/15 text-[#D79A43] border-[#D79A43]/40 font-bold"
                : "bg-[#11110F] text-[#918D84] border-white/[0.06] hover:text-[#F5F0E8]"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Notifications List */}
      <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl">
        {isLoading ? (
          <div className="space-y-3 py-6">
            <div className="h-14 bg-white/[0.03] rounded-xl animate-pulse" />
            <div className="h-14 bg-white/[0.03] rounded-xl animate-pulse" />
            <div className="h-14 bg-white/[0.03] rounded-xl animate-pulse" />
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="text-center py-16 space-y-3 font-mono text-xs text-[#918D84]">
            <Inbox className="w-8 h-8 text-[#66625B] mx-auto mb-2" />
            <p>No notifications match your selected filter.</p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.04] space-y-1">
            {filteredNotifications.map((n) => {
              const isUnread = !n.is_read;
              const isCritical = n.severity === "CRITICAL";
              const isWarning = n.severity === "WARNING";

              return (
                <div
                  key={n.id}
                  className={`p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all ${
                    isUnread ? "bg-white/[0.02]" : "opacity-80"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                        isCritical
                          ? "bg-[#E56B6F]/15 text-[#E56B6F] border border-[#E56B6F]/30"
                          : isWarning
                          ? "bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30"
                          : "bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30"
                      }`}
                    >
                      {isCritical ? (
                        <ShieldAlert className="w-4 h-4" />
                      ) : isWarning ? (
                        <AlertTriangle className="w-4 h-4" />
                      ) : (
                        <Info className="w-4 h-4" />
                      )}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-sans font-bold text-sm text-[#F5F0E8]">{n.title}</h4>
                        {isUnread && (
                          <span className="w-2 h-2 rounded-full bg-[#D79A43]" title="Unread alert" />
                        )}
                      </div>
                      <p className="text-xs font-mono text-[#918D84]">{n.message}</p>
                      <span className="text-[10px] font-mono text-[#66625B]">
                        {n.created_at ? new Date(n.created_at).toLocaleString() : "Just now"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    {n.related_case_id && (
                      <Link
                        href={`/dashboard/recovery/cases/${n.related_case_id}`}
                        className="flex items-center gap-1 text-xs font-mono text-[#D79A43] hover:underline"
                      >
                        <span>View Case</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}

                    {isUnread && (
                      <button
                        onClick={() => handleMarkRead(n.id)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-mono text-[#918D84] hover:text-[#F5F0E8] hover:bg-white/[0.05] cursor-pointer"
                      >
                        Mark Read
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
