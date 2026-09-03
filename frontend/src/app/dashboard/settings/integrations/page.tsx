"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  CreditCard,
  Zap,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Lock,
  ExternalLink,
  SlidersHorizontal,
  X,
  Server,
  Activity,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [syncLoading, setSyncLoading] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Connect Modal State
  const [selectedProvider, setSelectedProvider] = useState<any | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [environment, setEnvironment] = useState("TEST");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadIntegrations = async () => {
    try {
      setIsLoading(true);
      const data = await api.getIntegrations();
      setIntegrations(data);
    } catch (err: any) {
      console.error("Failed to load integrations:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const handleOpenConnect = (provider: any) => {
    setSelectedProvider(provider);
    setApiKey("");
    setSecretKey("");
    setWebhookSecret("");
    setEnvironment(provider.environment || "TEST");
    setModalError(null);
  };

  const handleTestConnection = async (providerId: string) => {
    try {
      setTestLoading(providerId);
      setNotice(null);
      const res = await api.testIntegration({
        provider: providerId,
        api_key: apiKey || "sk_test_placeholder",
        secret_key: secretKey,
      });
      setNotice({ text: `${providerId}: ${res.message}`, type: "success" });
    } catch (err: any) {
      setNotice({ text: `${providerId}: ${err.message || "Connection test failed."}`, type: "error" });
    } finally {
      setTestLoading(null);
    }
  };

  const handleSaveConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProvider) return;

    try {
      setIsSubmitting(true);
      setModalError(null);

      await api.connectIntegration({
        provider: selectedProvider.provider,
        api_key: apiKey,
        secret_key: secretKey,
        webhook_secret: webhookSecret,
        environment,
      });

      setNotice({ text: `${selectedProvider.name} connected successfully!`, type: "success" });
      setSelectedProvider(null);
      await loadIntegrations();
    } catch (err: any) {
      setModalError(err.message || "Failed to save connection.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSync = async (providerId: string) => {
    try {
      setSyncLoading(providerId);
      setNotice(null);
      const res = await api.syncIntegration(providerId);
      setNotice({ text: res.message || "Transactions synced successfully.", type: "success" });
      await loadIntegrations();
    } catch (err: any) {
      setNotice({ text: err.message || "Sync failed.", type: "error" });
    } finally {
      setSyncLoading(null);
    }
  };

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
            <span>PAYMENT GATEWAY INTEGRATIONS</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
            Payment Providers
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Connect your payment provider to stream real transaction events and automatically triage revenue at risk.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/settings/integrations/events"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>WEBHOOK EVENT LOG</span>
          </Link>

          <button
            onClick={loadIntegrations}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#11110F] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#D79A43]" : ""}`} />
            <span>SYNC</span>
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

      {/* Providers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {integrations.map((p) => {
          const isConnected = p.status === "CONNECTED";
          const isError = p.status === "ERROR";

          return (
            <div
              key={p.provider}
              className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-xl flex flex-col justify-between space-y-6"
            >
              <div>
                {/* Header Strip */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#171614] border border-white/[0.08] flex items-center justify-center text-[#D79A43]">
                      <CreditCard className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-sans font-bold text-base text-[#F5F0E8]">{p.name}</h3>
                      <span className="text-[11px] font-mono text-[#918D84]">{p.description}</span>
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-bold tracking-wider ${
                      isConnected
                        ? "bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30"
                        : isError
                        ? "bg-[#E56B6F]/15 text-[#E56B6F] border border-[#E56B6F]/30"
                        : "bg-white/[0.05] text-[#918D84] border border-white/[0.08]"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isConnected ? "bg-[#20B89A]" : isError ? "bg-[#E56B6F]" : "bg-[#66625B]"
                      }`}
                    />
                    {isConnected ? "CONNECTED" : isError ? "ERROR" : "NOT CONNECTED"}
                  </span>
                </div>

                {/* Telemetry / Configuration Details */}
                <div className="mt-6 p-4 rounded-xl bg-[#0D0D0B] border border-white/[0.04] space-y-2.5 font-mono text-xs">
                  <div className="flex items-center justify-between text-[#918D84]">
                    <span>Environment:</span>
                    <span className="text-[#F5F0E8] font-bold">{p.environment}</span>
                  </div>

                  <div className="flex items-center justify-between text-[#918D84]">
                    <span>API Key:</span>
                    <span className="text-[#F5F0E8]">{p.api_key_masked || "••••••••••••••••"}</span>
                  </div>

                  <div className="flex items-center justify-between text-[#918D84]">
                    <span>Webhooks Received:</span>
                    <span className="text-[#20B89A] font-bold">{p.events_received || 0} events</span>
                  </div>

                  {p.last_webhook_at && (
                    <div className="flex items-center justify-between text-[#918D84]">
                      <span>Last Webhook:</span>
                      <span className="text-[#F5F0E8]">{new Date(p.last_webhook_at).toLocaleTimeString()}</span>
                    </div>
                  )}

                  <div className="pt-2 border-t border-white/[0.04] text-[11px] text-[#66625B] truncate">
                    <span className="text-[#918D84]">Webhook URL: </span>
                    <span className="text-[#D79A43]">{p.webhook_url}</span>
                  </div>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="flex items-center gap-3 pt-2 border-t border-white/[0.04]">
                <button
                  onClick={() => handleOpenConnect(p)}
                  className="flex-1 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#171614] text-[#F5F0E8] hover:bg-[#201F1D] border border-white/[0.08] hover:border-[#D79A43]/40 transition-all cursor-pointer"
                >
                  {isConnected ? "Configure Keys" : "Connect Provider"}
                </button>

                {isConnected && (
                  <button
                    onClick={() => handleSync(p.provider)}
                    disabled={syncLoading === p.provider}
                    className="px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43]/15 text-[#D79A43] hover:bg-[#D79A43]/25 border border-[#D79A43]/30 transition-all cursor-pointer disabled:opacity-50 flex items-center gap-2"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncLoading === p.provider ? "animate-spin" : ""}`} />
                    <span>{syncLoading === p.provider ? "Syncing..." : "Sync Txns"}</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Connect / Configure Modal */}
      <AnimatePresence>
        {selectedProvider && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg p-6 sm:p-8 rounded-2xl bg-[#11110F] border border-white/[0.1] shadow-2xl space-y-6 font-mono text-xs"
            >
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43]">
                    <CreditCard className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="font-sans font-bold text-base text-[#F5F0E8]">Connect {selectedProvider.name}</h2>
                    <span className="text-[11px] text-[#918D84]">Scoped strictly to your organization workspace</span>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedProvider(null)}
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

              <form onSubmit={handleSaveConnection} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">Environment</label>
                  <select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  >
                    <option value="TEST">TEST / SANDBOX MODE</option>
                    <option value="LIVE">LIVE PRODUCTION MODE</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                    API Key / Client ID *
                  </label>
                  <input
                    type="password"
                    placeholder="e.g. key_test_... or sk_live_..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                    Secret Key / Client Secret
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••••••••••"
                    value={secretKey}
                    onChange={(e) => setSecretKey(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                    Webhook Secret (Signature Verification)
                  </label>
                  <input
                    type="password"
                    placeholder="whsec_... or webhook secret"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
                </div>

                <div className="pt-4 flex items-center justify-between gap-3 border-t border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => handleTestConnection(selectedProvider.provider)}
                    disabled={testLoading === selectedProvider.provider}
                    className="px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#141412] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] cursor-pointer"
                  >
                    {testLoading === selectedProvider.provider ? "Testing..." : "Test Connection"}
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedProvider(null)}
                      className="px-4 py-2.5 rounded-xl text-xs font-mono text-[#918D84] hover:text-[#F5F0E8]"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43] text-black hover:bg-[#D79A43]/90 transition-all cursor-pointer disabled:opacity-50"
                    >
                      {isSubmitting ? "Saving..." : "Save Connection"}
                    </button>
                  </div>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
