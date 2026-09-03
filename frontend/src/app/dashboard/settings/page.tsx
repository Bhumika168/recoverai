"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  User,
  Building2,
  Lock,
  Key,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Zap,
  Sliders,
  Save,
  Globe2,
  Coins,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const { user, organization, refreshUser } = useAuth();
  const [copiedKey, setCopiedKey] = useState(false);

  // Organization & Policy Form State
  const [orgName, setOrgName] = useState(organization?.name || "");
  const [industry, setIndustry] = useState(organization?.industry || "SaaS & Subscription");
  const [companySize, setCompanySize] = useState(organization?.company_size || "11-50 employees");
  const [country, setCountry] = useState(organization?.country || "India");
  const [currency, setCurrency] = useState(organization?.currency || "INR");

  const [maxRetries, setMaxRetries] = useState(organization?.max_retries || 3);
  const [highValueThreshold, setHighValueThreshold] = useState(organization?.high_value_threshold || 25000);
  const [autoRetryEnabled, setAutoRetryEnabled] = useState(
    organization?.auto_retry_enabled !== undefined ? organization.auto_retry_enabled : true
  );

  const [isSavingOrg, setIsSavingOrg] = useState(false);
  const [orgSuccess, setOrgSuccess] = useState(false);
  const [orgError, setOrgError] = useState<string | null>(null);

  // Password State
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    if (organization) {
      setOrgName(organization.name || "");
      setIndustry(organization.industry || "SaaS & Subscription");
      setCompanySize(organization.company_size || "11-50 employees");
      setCountry(organization.country || "India");
      setCurrency(organization.currency || "INR");
      if (organization.max_retries) setMaxRetries(organization.max_retries);
      if (organization.high_value_threshold) setHighValueThreshold(organization.high_value_threshold);
      if (organization.auto_retry_enabled !== undefined) setAutoRetryEnabled(organization.auto_retry_enabled);
    }
  }, [organization]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleSaveOrganization = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName.trim()) {
      setOrgError("Organization name cannot be empty.");
      return;
    }
    try {
      setIsSavingOrg(true);
      setOrgError(null);
      await api.updateOrganization({
        name: orgName.trim(),
        industry,
        company_size: companySize,
        country,
        currency,
        max_retries: Number(maxRetries),
        high_value_threshold: Number(highValueThreshold),
        auto_retry_enabled: autoRetryEnabled,
      });
      await refreshUser();
      setOrgSuccess(true);
      setTimeout(() => setOrgSuccess(false), 3000);
    } catch (err: any) {
      setOrgError(err.message || "Failed to update workspace settings.");
    } finally {
      setIsSavingOrg(false);
    }
  };

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("Please complete all password fields.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    setPasswordError(null);
    setPasswordSuccess(true);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setTimeout(() => setPasswordSuccess(false), 4000);
  };

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Header */}
      <div className="pb-6 border-b border-white/[0.07]">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[#D79A43] block mb-1">
          ORGANIZATION & POLICY CONFIGURATION
        </span>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
          Workspace Settings
        </h1>
        <p className="text-xs font-mono text-[#918D84] mt-1">
          Configure recovery thresholds, deterministic policy guardrails, company telemetry, and team access.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column (8 cols): Main Settings Panels */}
        <div className="lg:col-span-8 space-y-6">
          {/* 1. Organization & Policy Configuration */}
          <form onSubmit={handleSaveOrganization} className="p-6 sm:p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.5)] space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43]">
                  <Building2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-serif text-lg font-bold text-[#F5F0E8]">
                    Workspace Profile & Telemetry
                  </h3>
                  <span className="text-[11px] font-mono text-[#66625B]">
                    Tenant boundary: <code className="text-[#D79A43]">{organization?.slug || "isolated"}</code>
                  </span>
                </div>
              </div>
              <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30">
                {organization?.role || "OWNER"}
              </span>
            </div>

            {orgSuccess && (
              <div className="p-3.5 rounded-xl bg-[#20B89A]/10 border border-[#20B89A]/30 text-[#20B89A] text-xs font-mono flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Workspace settings and policy rules updated successfully.</span>
              </div>
            )}

            {orgError && (
              <div className="p-3.5 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] text-xs font-mono flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                <span>{orgError}</span>
              </div>
            )}

            <div className="space-y-4 font-mono text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#66625B] uppercase block">Organization Name</label>
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#66625B] uppercase block">Industry</label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#66625B] uppercase block">Company Size</label>
                  <input
                    type="text"
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#66625B] uppercase block">Country</label>
                  <input
                    type="text"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#66625B] uppercase block">Currency</label>
                  <select
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
              </div>

              {/* Recovery Policy Invariants Section */}
              <div className="pt-4 border-t border-white/[0.06] space-y-4">
                <div className="flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-[#D79A43]" />
                  <span className="text-xs font-bold text-[#F5F0E8] uppercase tracking-wider">
                    Autonomous Recovery Policy Guardrails
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-2">
                    <label className="text-[10px] text-[#66625B] uppercase block">
                      Max Retry Limit (Invar 02)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={maxRetries}
                      onChange={(e) => setMaxRetries(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg bg-[#141412] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                    />
                    <span className="text-[10px] text-[#918D84] block">
                      Hard limit on automated retry attempts before mandatory escalation.
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-2">
                    <label className="text-[10px] text-[#66625B] uppercase block">
                      High-Value Approval Threshold (Invar 04)
                    </label>
                    <input
                      type="number"
                      step="1000"
                      value={highValueThreshold}
                      onChange={(e) => setHighValueThreshold(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg bg-[#141412] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                    />
                    <span className="text-[10px] text-[#918D84] block">
                      Transactions exceeding this amount require human operator approval.
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSavingOrg}
                  className="py-2.5 px-6 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSavingOrg ? "Saving Settings..." : "Save Workspace & Policies"}</span>
                </button>
              </div>
            </div>
          </form>

          {/* 2. Personal Profile */}
          <div className="p-6 sm:p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.5)] space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-white/[0.06]">
              <div className="w-8 h-8 rounded-xl bg-[#20B89A]/15 border border-[#20B89A]/30 flex items-center justify-center text-[#20B89A]">
                <User className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-serif text-lg font-bold text-[#F5F0E8]">
                  Personal Credentials
                </h3>
                <span className="text-[11px] font-mono text-[#66625B]">
                  Authenticated user profile
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
              <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-1">
                <span className="text-[10px] text-[#66625B] uppercase block">Full Name</span>
                <span className="text-sm font-bold text-[#F5F0E8] block">
                  {user?.full_name || "Alex Vance"}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-1">
                <span className="text-[10px] text-[#66625B] uppercase block">Work Email</span>
                <span className="text-xs text-[#F5F0E8] block truncate">
                  {user?.email || "alex@recoverai.com"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Security & Webhook */}
        <div className="lg:col-span-4 space-y-6">
          {/* API Keys Panel */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.5)] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-[#D79A43]" />
                <span className="text-xs font-mono font-bold text-[#F5F0E8]">
                  WEBHOOK INGESTION
                </span>
              </div>
            </div>

            <p className="text-[11px] font-mono text-[#918D84] leading-relaxed">
              Configure your payment gateway to dispatch failure events to this endpoint.
            </p>

            <div className="p-3 rounded-xl bg-[#080807] border border-white/[0.06] flex items-center justify-between font-mono text-xs">
              <span className="text-[#D79A43] truncate text-[11px] mr-2">
                https://api.recoverai.io/webhooks/v1/payment-events
              </span>
              <button
                onClick={() => handleCopy("https://api.recoverai.io/webhooks/v1/payment-events")}
                className="p-1.5 rounded bg-[#171614] text-[#918D84] hover:text-[#F5F0E8] transition-colors cursor-pointer"
                title="Copy webhook URL"
              >
                {copiedKey ? <Check className="w-3.5 h-3.5 text-[#20B89A]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Security Invariants */}
          <div className="p-6 rounded-2xl bg-[#11110F] border border-[#20B89A]/30 shadow-[0_8px_32px_rgba(0,0,0,0.5)] font-mono space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-bold text-[#F5F0E8] tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#20B89A]" />
                TENANT BOUNDARY
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#20B89A]/15 text-[#20B89A] border border-[#20B89A]/30 font-bold">
                ISOLATED
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#66625B]">Tenant Slug:</span>
                <span className="text-[#F5F0E8] font-bold">{organization?.slug || "active"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#66625B]">Ledger Immutability:</span>
                <span className="text-[#20B89A] font-bold">SHA-256 Chained</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#66625B]">Session Security:</span>
                <span className="text-[#20B89A] font-bold">HttpOnly + SameSite</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
