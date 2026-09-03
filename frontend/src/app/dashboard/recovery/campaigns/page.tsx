"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Megaphone,
  Plus,
  RefreshCw,
  Play,
  Pause,
  Archive,
  CheckCircle2,
  AlertTriangle,
  X,
  Mail,
  MessageSquare,
  Smartphone,
  Layers,
  ArrowRight,
  TrendingUp,
  Percent,
  Sliders,
} from "lucide-react";
import { api } from "@/lib/api";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Create Campaign Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [recoveryType, setRecoveryType] = useState("FAILED_PAYMENT");
  const [targetSegment, setTargetSegment] = useState("ALL_FAILURES");
  const [minAmount, setMinAmount] = useState("0");
  const [maxAmount, setMaxAmount] = useState("1000000");
  const [maxAttempts, setMaxAttempts] = useState("3");
  const [retryDelay, setRetryDelay] = useState("24");
  const [channels, setChannels] = useState<string[]>(["EMAIL", "WHATSAPP", "SMS"]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadCampaigns = async () => {
    try {
      setIsLoading(true);
      const data = await api.getCampaigns();
      setCampaigns(data);
    } catch (err: any) {
      console.error("Failed to load campaigns:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setModalError(null);

      await api.createCampaign({
        name,
        description,
        recovery_type: recoveryType,
        target_segment: targetSegment,
        min_amount: parseFloat(minAmount) || 0,
        max_amount: parseFloat(maxAmount) || 1000000,
        max_recovery_attempts: parseInt(maxAttempts) || 3,
        retry_delay_hours: parseInt(retryDelay) || 24,
        channels,
        is_active: true,
      });

      setNotice({ text: `Campaign '${name}' created and activated!`, type: "success" });
      setShowCreateModal(false);
      setName("");
      setDescription("");
      await loadCampaigns();
    } catch (err: any) {
      setModalError(err.message || "Failed to create campaign.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePause = async (id: string, campName: string) => {
    try {
      await api.pauseCampaign(id);
      setNotice({ text: `Campaign '${campName}' paused.`, type: "success" });
      await loadCampaigns();
    } catch (err: any) {
      setNotice({ text: err.message || "Failed to pause campaign.", type: "error" });
    }
  };

  const handleResume = async (id: string, campName: string) => {
    try {
      await api.resumeCampaign(id);
      setNotice({ text: `Campaign '${campName}' resumed.`, type: "success" });
      await loadCampaigns();
    } catch (err: any) {
      setNotice({ text: err.message || "Failed to resume campaign.", type: "error" });
    }
  };

  const handleArchive = async (id: string, campName: string) => {
    try {
      await api.archiveCampaign(id);
      setNotice({ text: `Campaign '${campName}' archived.`, type: "success" });
      await loadCampaigns();
    } catch (err: any) {
      setNotice({ text: err.message || "Failed to archive campaign.", type: "error" });
    }
  };

  const toggleChannel = (ch: string) => {
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((item) => item !== ch) : [...prev, ch]
    );
  };

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
            <span>AUTONOMOUS CAMPAIGN SEQUENCER</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
            Recovery Campaigns
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Configure bounded multi-channel recovery workflows, frequency caps, and stop conditions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/recovery/templates"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>TEMPLATES</span>
          </Link>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43] text-black hover:bg-[#D79A43]/90 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>CREATE CAMPAIGN</span>
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

      {/* Campaigns Table / Cards */}
      {isLoading ? (
        <div className="p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] space-y-4">
          <div className="h-12 bg-white/[0.03] rounded-xl animate-pulse" />
          <div className="h-12 bg-white/[0.03] rounded-xl animate-pulse" />
          <div className="h-12 bg-white/[0.03] rounded-xl animate-pulse" />
        </div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-20 rounded-2xl bg-[#11110F] border border-white/[0.08] space-y-4 font-mono text-xs text-[#918D84]">
          <Megaphone className="w-10 h-10 text-[#66625B] mx-auto mb-2" />
          <h3 className="font-sans font-bold text-base text-[#F5F0E8]">No recovery campaigns yet</h3>
          <p className="max-w-md mx-auto text-[11px] text-[#66625B]">
            Create your first automated campaign to sequence retries, send multi-channel recovery links, and track recovered revenue.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43] text-black hover:bg-[#D79A43]/90 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Campaign</span>
          </button>
        </div>
      ) : (
        <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] text-[11px] text-[#918D84] uppercase tracking-wider">
                <th className="pb-3">Campaign</th>
                <th className="pb-3">Type</th>
                <th className="pb-3">Status</th>
                <th className="pb-3">Enrolled</th>
                <th className="pb-3">Outreach Sent</th>
                <th className="pb-3">Recovered</th>
                <th className="pb-3">Recovery Rate</th>
                <th className="pb-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {campaigns.map((c) => {
                const isActive = c.status === "ACTIVE";
                const isPaused = c.status === "PAUSED";

                return (
                  <tr key={c.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-4">
                      <div className="font-sans font-bold text-sm text-[#F5F0E8]">{c.name}</div>
                      <div className="text-[11px] text-[#66625B] truncate max-w-xs">{c.description || "Automated recovery sequence"}</div>
                    </td>
                    <td className="py-4 text-[#D79A43]">{c.recovery_type}</td>
                    <td className="py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                          isActive
                            ? "bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30"
                            : isPaused
                            ? "bg-[#D79A43]/15 text-[#D79A43] border border-[#D79A43]/30"
                            : "bg-white/[0.05] text-[#918D84] border border-white/[0.08]"
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            isActive ? "bg-[#20B89A]" : isPaused ? "bg-[#D79A43]" : "bg-[#66625B]"
                          }`}
                        />
                        {c.status}
                      </span>
                    </td>
                    <td className="py-4 text-[#F5F0E8]">{c.enrolled_cases_count || 0}</td>
                    <td className="py-4 text-[#918D84]">{c.messages_sent_count || 0}</td>
                    <td className="py-4 font-bold text-[#20B89A]">
                      ₹{c.recovered_amount ? c.recovered_amount.toLocaleString() : "0"}
                    </td>
                    <td className="py-4 text-[#D79A43]">{c.recovery_rate || 0}%</td>
                    <td className="py-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        {isActive ? (
                          <button
                            onClick={() => handlePause(c.id, c.name)}
                            title="Pause Campaign"
                            className="p-1.5 rounded-lg bg-[#171614] text-[#D79A43] hover:bg-[#201F1D] border border-white/[0.08] cursor-pointer"
                          >
                            <Pause className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleResume(c.id, c.name)}
                            title="Resume Campaign"
                            className="p-1.5 rounded-lg bg-[#171614] text-[#20B89A] hover:bg-[#201F1D] border border-white/[0.08] cursor-pointer"
                          >
                            <Play className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => handleArchive(c.id, c.name)}
                          title="Archive Campaign"
                          className="p-1.5 rounded-lg bg-[#171614] text-[#918D84] hover:text-[#E56B6F] hover:bg-[#201F1D] border border-white/[0.08] cursor-pointer"
                        >
                          <Archive className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Campaign Drawer / Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-xl p-6 sm:p-8 rounded-2xl bg-[#11110F] border border-white/[0.1] shadow-2xl space-y-6 font-mono text-xs max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43]">
                    <Megaphone className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="font-sans font-bold text-base text-[#F5F0E8]">Create Recovery Campaign</h2>
                    <span className="text-[11px] text-[#918D84]">Configure bounded automated recovery rules</span>
                  </div>
                </div>

                <button
                  onClick={() => setShowCreateModal(false)}
                  className="p-1 rounded-lg text-[#918D84] hover:text-[#F5F0E8] hover:bg-white/[0.05]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {modalError && (
                <div className="p-3 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{modalError}</span>
                </div>
              )}

              <form onSubmit={handleCreateCampaign} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase">Campaign Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Standard Failed Payment Recovery"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase">Description</label>
                  <textarea
                    rows={2}
                    placeholder="Brief description of the recovery strategy"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Recovery Type</label>
                    <select
                      value={recoveryType}
                      onChange={(e) => setRecoveryType(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    >
                      <option value="FAILED_PAYMENT">Failed Payment</option>
                      <option value="SUBSCRIPTION">Subscription / Recurring</option>
                      <option value="CHECKOUT_ABANDONED">Checkout Abandonment</option>
                      <option value="OVERDUE_INVOICE">Overdue Invoice</option>
                      <option value="MANDATE_RETRY">Mandate Retry</option>
                      <option value="PAYMENT_METHOD_UPDATE">Payment Method Update</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Target Segment</label>
                    <select
                      value={targetSegment}
                      onChange={(e) => setTargetSegment(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    >
                      <option value="ALL_FAILURES">All Failures</option>
                      <option value="HIGH_VALUE">High Value Only</option>
                      <option value="CART_ABANDONED">Cart Abandoned</option>
                      <option value="RECURRING_SUB">Recurring Subscriptions</option>
                    </select>
                  </div>
                </div>

                {/* Amount Bounds */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Min Amount (₹)</label>
                    <input
                      type="number"
                      value={minAmount}
                      onChange={(e) => setMinAmount(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Max Amount (₹)</label>
                    <input
                      type="number"
                      value={maxAmount}
                      onChange={(e) => setMaxAmount(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    />
                  </div>
                </div>

                {/* Attempts & Delay */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Max Attempts (Cap)</label>
                    <input
                      type="number"
                      max={5}
                      min={1}
                      value={maxAttempts}
                      onChange={(e) => setMaxAttempts(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Retry Delay (Hours)</label>
                    <input
                      type="number"
                      min={1}
                      value={retryDelay}
                      onChange={(e) => setRetryDelay(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    />
                  </div>
                </div>

                {/* Channel Selectors */}
                <div className="space-y-2">
                  <label className="block text-[11px] text-[#918D84] uppercase">Enabled Channels</label>
                  <div className="flex items-center gap-3">
                    {["EMAIL", "WHATSAPP", "SMS", "IN_APP"].map((ch) => (
                      <button
                        key={ch}
                        type="button"
                        onClick={() => toggleChannel(ch)}
                        className={`px-3 py-1.5 rounded-lg border text-[11px] transition-all cursor-pointer ${
                          channels.includes(ch)
                            ? "bg-[#D79A43]/15 text-[#D79A43] border-[#D79A43]/40"
                            : "bg-[#141412] text-[#66625B] border-white/[0.08]"
                        }`}
                      >
                        {ch}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-4 flex items-center justify-end gap-3 border-t border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 rounded-xl text-[#918D84] hover:text-[#F5F0E8]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2.5 rounded-xl font-bold bg-[#D79A43] text-black hover:bg-[#D79A43]/90 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {isSubmitting ? "Creating..." : "Save & Activate"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
