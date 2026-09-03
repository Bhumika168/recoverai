"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertTriangle,
  X,
  Clock,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";

export default function WebhookEventsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  const loadEvents = async () => {
    try {
      setIsLoading(true);
      const data = await api.getWebhookEvents(100);
      setEvents(data);
    } catch (err: any) {
      console.error("Failed to load webhook events:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Back Link */}
      <Link
        href="/dashboard/settings/integrations"
        className="inline-flex items-center gap-2 text-xs font-mono text-[#918D84] hover:text-[#F5F0E8] transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Payment Providers</span>
      </Link>

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#20B89A] mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#20B89A] animate-pulse" />
            <span>REAL-TIME INGESTION LOG</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
            Webhook Events Log
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Cryptographically signed events ingested from connected payment gateways.
          </p>
        </div>

        <button
          onClick={loadEvents}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
          <span>REFRESH LOGS</span>
        </button>
      </div>

      {/* Events Table */}
      <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl">
        {isLoading ? (
          <div className="space-y-3 py-8">
            <div className="h-10 bg-white/[0.03] rounded-lg animate-pulse" />
            <div className="h-10 bg-white/[0.03] rounded-lg animate-pulse" />
            <div className="h-10 bg-white/[0.03] rounded-lg animate-pulse" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-16 space-y-3 font-mono text-xs text-[#918D84]">
            <Activity className="w-8 h-8 text-[#66625B] mx-auto mb-2" />
            <p>No webhook events received yet.</p>
            <p className="text-[11px] text-[#66625B]">
              Connect a payment provider or dispatch a test webhook to see incoming events.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-[11px] text-[#918D84] uppercase">
                  <th className="pb-3">Timestamp</th>
                  <th className="pb-3">Provider</th>
                  <th className="pb-3">Event Type</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Latency</th>
                  <th className="pb-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {events.map((e) => (
                  <tr key={e.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 text-[#918D84]">
                      {e.received_at ? new Date(e.received_at).toLocaleTimeString() : "—"}
                    </td>
                    <td className="py-3 font-bold text-[#F5F0E8]">{e.provider}</td>
                    <td className="py-3 text-[#D79A43]">{e.event_type}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          e.processing_status === "PROCESSED"
                            ? "bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30"
                            : e.processing_status === "DUPLICATE"
                            ? "bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30"
                            : "bg-[#E56B6F]/15 text-[#E56B6F] border border-[#E56B6F]/30"
                        }`}
                      >
                        {e.processing_status}
                      </span>
                    </td>
                    <td className="py-3 text-[#918D84]">{e.processing_time_ms ? `${e.processing_time_ms.toFixed(1)}ms` : "—"}</td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => setSelectedEvent(e)}
                        className="text-[11px] text-[#D79A43] hover:underline cursor-pointer"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspect Modal */}
      <AnimatePresence>
        {selectedEvent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg p-6 rounded-2xl bg-[#11110F] border border-white/[0.1] shadow-2xl space-y-4 font-mono text-xs"
            >
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <h3 className="font-sans font-bold text-base text-[#F5F0E8]">Webhook Event Detail</h3>
                <button onClick={() => setSelectedEvent(null)} className="p-1 text-[#918D84] hover:text-[#F5F0E8]">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-[#918D84]">
                  <span>Event ID:</span>
                  <span className="text-[#F5F0E8]">{selectedEvent.id}</span>
                </div>
                <div className="flex justify-between text-[#918D84]">
                  <span>Provider:</span>
                  <span className="text-[#F5F0E8] font-bold">{selectedEvent.provider}</span>
                </div>
                <div className="flex justify-between text-[#918D84]">
                  <span>Event Type:</span>
                  <span className="text-[#D79A43]">{selectedEvent.event_type}</span>
                </div>
                <div className="flex justify-between text-[#918D84]">
                  <span>Status:</span>
                  <span className="text-[#20B89A]">{selectedEvent.processing_status}</span>
                </div>
                {selectedEvent.error_message && (
                  <div className="p-3 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F]">
                    {selectedEvent.error_message}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-white/[0.06] text-right">
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="px-4 py-2 rounded-xl bg-[#171614] text-[#F5F0E8] hover:bg-[#201F1D] border border-white/[0.08]"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
