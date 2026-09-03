"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Building2,
  Globe2,
  Coins,
  CreditCard,
  FileSpreadsheet,
  PlusCircle,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ShieldCheck,
  Sliders,
  Lock,
  Radio,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

const INDUSTRIES = [
  "SaaS & Subscription",
  "E-commerce & Retail",
  "Fintech & Banking",
  "Marketplace & Platforms",
  "B2B Professional Services",
  "Gaming & Digital Goods",
  "Other",
];

const COMPANY_SIZES = [
  "1-10 employees",
  "11-50 employees",
  "51-200 employees",
  "201-1000 employees",
  "1000+ enterprise",
];

const CURRENCIES = [
  { code: "INR", symbol: "₹", name: "Indian Rupee (INR)" },
  { code: "USD", symbol: "$", name: "US Dollar (USD)" },
  { code: "EUR", symbol: "€", name: "Euro (EUR)" },
  { code: "GBP", symbol: "£", name: "British Pound (GBP)" },
];

export default function OnboardingPage() {
  const { organization, refreshUser } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // STEP 01: Workspace (Empty by default for new organization)
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("SaaS & Subscription");
  const [companySize, setCompanySize] = useState("11-50 employees");
  const [country, setCountry] = useState("India");
  const [currency, setCurrency] = useState("INR");

  // STEP 02: Recovery Guardrails
  const [maxRetries, setMaxRetries] = useState(3);
  const [highValueThreshold, setHighValueThreshold] = useState(25000);
  const [requireHumanApproval, setRequireHumanApproval] = useState(true);
  const [hardDeclineBehavior, setHardDeclineBehavior] = useState("SUPPRESS");
  const [autoEscalateRules, setAutoEscalateRules] = useState("AFTER_MAX_RETRIES");

  // STEP 03: Data Source Choice
  const [selectedDataSource, setSelectedDataSource] = useState<"CSV" | "MANUAL" | "PROVIDER">("CSV");

  // Restore already-persisted organization properties if user refreshes browser
  useEffect(() => {
    if (organization) {
      if (organization.name) setCompanyName(organization.name);
      if (organization.industry) setIndustry(organization.industry);
      if (organization.company_size) setCompanySize(organization.company_size);
      if (organization.country) setCountry(organization.country);
      if (organization.currency) setCurrency(organization.currency);
      if (organization.max_retries !== undefined) setMaxRetries(organization.max_retries);
      if (organization.high_value_threshold !== undefined) setHighValueThreshold(organization.high_value_threshold);
      if (organization.require_human_approval !== undefined) setRequireHumanApproval(organization.require_human_approval);
      if (organization.hard_decline_behavior) setHardDeclineBehavior(organization.hard_decline_behavior);
      if (organization.auto_escalate_rules) setAutoEscalateRules(organization.auto_escalate_rules);
    }
  }, [organization]);

  const handleStep1Next = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) {
      setError("Please specify your organization name.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Persist Step 1 directly to authenticated organization in DB
      await api.updateOrganization({
        name: companyName.trim(),
        industry,
        company_size: companySize,
        country,
        currency,
      });

      await refreshUser();
      setStep(2);
    } catch (err: any) {
      setError(err.message || "Failed to persist workspace settings.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleStep2Next = async (e: React.FormEvent) => {
    e.preventDefault();
    if (maxRetries < 1 || maxRetries > 10) {
      setError("Maximum automatic retries must be between 1 and 10.");
      return;
    }
    if (highValueThreshold < 0) {
      setError("High-value transaction threshold must be non-negative.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Persist Step 2 directly to authenticated organization in DB
      await api.updateOrganization({
        max_retries: Number(maxRetries),
        high_value_threshold: Number(highValueThreshold),
        require_human_approval: requireHumanApproval,
        hard_decline_behavior: hardDeclineBehavior,
        auto_escalate_rules: autoEscalateRules,
      });

      await refreshUser();
      setStep(3);
    } catch (err: any) {
      setError(err.message || "Failed to persist recovery guardrails.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFinishOnboarding = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Finalize Onboarding & Save
      await api.updateOrganization({
        name: companyName.trim(),
        industry,
        company_size: companySize,
        country,
        currency,
        max_retries: Number(maxRetries),
        high_value_threshold: Number(highValueThreshold),
        require_human_approval: requireHumanApproval,
        hard_decline_behavior: hardDeclineBehavior,
        auto_escalate_rules: autoEscalateRules,
        onboarding_completed: true,
      });

      await refreshUser();

      // Redirect to Dashboard (or specific ingestion route if chosen)
      if (selectedDataSource === "CSV") {
        window.location.href = "/dashboard/transactions/import";
      } else if (selectedDataSource === "MANUAL") {
        window.location.href = "/dashboard/transactions/new";
      } else {
        window.location.href = "/dashboard";
      }
    } catch (err: any) {
      setError(err.message || "Failed to complete onboarding setup.");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070706] text-[#F5F0E8] flex flex-col justify-between selection:bg-[#D79A43]/20 relative overflow-hidden font-sans">
      {/* Background Ambience */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#D79A43]/[0.025] blur-[160px] pointer-events-none" />
      <div className="absolute -bottom-24 left-1/3 w-[600px] h-[300px] bg-[#20B89A]/[0.02] blur-[150px] pointer-events-none" />

      {/* Header */}
      <header className="px-6 sm:px-12 py-8 flex items-center justify-between relative z-10 border-b border-white/[0.04]">
        <Link href="/" className="flex items-center gap-3 group cursor-pointer">
          <div className="w-8 h-8 rounded-xl bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43] group-hover:scale-105 transition-transform">
            <Zap className="w-4 h-4 fill-[#D79A43]" />
          </div>
          <span className="font-sans font-bold text-lg tracking-tight text-[#F5F0E8]">
            Recover<span className="text-[#D79A43]">AI</span>
          </span>
        </Link>

        {/* Step Progression Indicators */}
        <div className="flex items-center gap-3 text-xs font-mono">
          <div className={`px-3 py-1 rounded-full border flex items-center gap-2 ${step === 1 ? "bg-[#D79A43]/10 border-[#D79A43]/40 text-[#D79A43]" : step > 1 ? "bg-[#20B89A]/10 border-[#20B89A]/30 text-[#20B89A]" : "bg-[#11110F] border-white/5 text-[#66625B]"}`}>
            <span>01</span>
            <span className="hidden sm:inline">Workspace</span>
          </div>
          <div className="w-4 h-px bg-white/10" />
          <div className={`px-3 py-1 rounded-full border flex items-center gap-2 ${step === 2 ? "bg-[#D79A43]/10 border-[#D79A43]/40 text-[#D79A43]" : step > 2 ? "bg-[#20B89A]/10 border-[#20B89A]/30 text-[#20B89A]" : "bg-[#11110F] border-white/5 text-[#66625B]"}`}>
            <span>02</span>
            <span className="hidden sm:inline">Guardrails</span>
          </div>
          <div className="w-4 h-px bg-white/10" />
          <div className={`px-3 py-1 rounded-full border flex items-center gap-2 ${step === 3 ? "bg-[#D79A43]/10 border-[#D79A43]/40 text-[#D79A43]" : "bg-[#11110F] border-white/5 text-[#66625B]"}`}>
            <span>03</span>
            <span className="hidden sm:inline">Data Source</span>
          </div>
        </div>
      </header>

      {/* Center Container */}
      <main className="flex-1 flex items-center justify-center px-6 py-12 relative z-10">
        <motion.div
          key={`step-${step}`}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          className="w-full max-w-2xl"
        >
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] text-xs font-mono flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {step === 1 && (
            /* STEP 01: WORKSPACE PROFILE */
            <div className="space-y-6">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
                  <span>STEP 01 OF 03 • WORKSPACE PROFILE</span>
                </div>
                <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
                  Define your recovery workspace.
                </h1>
                <p className="text-xs font-mono text-[#918D84] mt-2">
                  Configure your organization profile and telemetry defaults for autonomous recovery operations.
                </p>
              </div>

              <form onSubmit={handleStep1Next} className="p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] backdrop-blur-xl space-y-5">
                <div className="space-y-1.5">
                  <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                    Company / Organization Name *
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      required
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="Acme Payments, Nova Technologies..."
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                      Industry Vertical
                    </label>
                    <select
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    >
                      {INDUSTRIES.map((ind) => (
                        <option key={ind} value={ind} className="bg-[#11110F] text-[#F5F0E8]">
                          {ind}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                      Company Size
                    </label>
                    <select
                      value={companySize}
                      onChange={(e) => setCompanySize(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    >
                      {COMPANY_SIZES.map((size) => (
                        <option key={size} value={size} className="bg-[#11110F] text-[#F5F0E8]">
                          {size}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                      Country
                    </label>
                    <div className="relative">
                      <Globe2 className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                      <input
                        type="text"
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                        placeholder="India, United States, UK..."
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                      Default Currency
                    </label>
                    <select
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    >
                      {CURRENCIES.map((curr) => (
                        <option key={curr.code} value={curr.code} className="bg-[#11110F] text-[#F5F0E8]">
                          {curr.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full mt-4 py-3.5 px-6 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isLoading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Continue to Recovery Guardrails</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>
          )}

          {step === 2 && (
            /* STEP 02: RECOVERY GUARDRAILS */
            <div className="space-y-6">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
                  <span>STEP 02 OF 03 • RECOVERY GUARDRAILS</span>
                </div>
                <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
                  Set deterministic policy boundaries.
                </h1>
                <p className="text-xs font-mono text-[#918D84] mt-2">
                  Configure automatic retry limits, high-value thresholds, and human approval rules.
                </p>
              </div>

              <form onSubmit={handleStep2Next} className="p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] backdrop-blur-xl space-y-5 font-mono text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-2">
                    <label className="text-[10px] text-[#66625B] uppercase block">
                      Maximum Automatic Retries
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={maxRetries}
                      onChange={(e) => setMaxRetries(Number(e.target.value))}
                      className="w-full px-3 py-2.5 rounded-lg bg-[#141412] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                    />
                    <span className="text-[10px] text-[#918D84] block">
                      Limits automated attempts before requiring human review.
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-2">
                    <label className="text-[10px] text-[#66625B] uppercase block">
                      High-Value Transaction Threshold ({currency})
                    </label>
                    <input
                      type="number"
                      step="1000"
                      value={highValueThreshold}
                      onChange={(e) => setHighValueThreshold(Number(e.target.value))}
                      className="w-full px-3 py-2.5 rounded-lg bg-[#141412] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                    />
                    <span className="text-[10px] text-[#918D84] block">
                      Transactions above this require manual confirmation.
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-2">
                    <label className="text-[10px] text-[#66625B] uppercase block">
                      Hard-Decline Behavior
                    </label>
                    <select
                      value={hardDeclineBehavior}
                      onChange={(e) => setHardDeclineBehavior(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-lg bg-[#141412] border border-white/[0.08] text-xs text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                    >
                      <option value="SUPPRESS">SUPPRESS (Block Retries on Stolen/Lost Cards)</option>
                      <option value="FLAG">FLAG FOR COMPLIANCE</option>
                      <option value="NOTIFY">NOTIFY OPERATOR ONLY</option>
                    </select>
                    <span className="text-[10px] text-[#918D84] block">
                      Invariant 01: Prevents retrying permanent hard declines.
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#080807] border border-white/[0.06] space-y-2">
                    <label className="text-[10px] text-[#66625B] uppercase block">
                      Automatic Escalation Rules
                    </label>
                    <select
                      value={autoEscalateRules}
                      onChange={(e) => setAutoEscalateRules(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-lg bg-[#141412] border border-white/[0.08] text-xs text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                    >
                      <option value="AFTER_MAX_RETRIES">Escalate after Max Retries Reached</option>
                      <option value="LOW_CONFIDENCE">Escalate on Low AI Confidence (&lt;60%)</option>
                      <option value="ALL_EXCEPTIONS">Escalate on All Failure Exceptions</option>
                    </select>
                    <span className="text-[10px] text-[#918D84] block">
                      Invariant 03: Automatic handover to human operators.
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 mt-6 pt-4 border-t border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="py-3 px-5 rounded-xl bg-[#141412] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] font-mono text-xs transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back</span>
                  </button>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="py-3.5 px-8 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <span>Continue to Data Source</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {step === 3 && (
            /* STEP 03: DATA SOURCE SELECTION */
            <div className="space-y-6">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#20B89A] mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B89A] animate-pulse" />
                  <span>STEP 03 OF 03 • DATA SOURCE SETUP</span>
                </div>
                <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
                  Select initial ingestion source.
                </h1>
                <p className="text-xs font-mono text-[#918D84] mt-2">
                  Choose how you want to bring payment transaction failure data into RecoverAI.
                </p>
              </div>

              {/* Data Source Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <button
                  type="button"
                  onClick={() => setSelectedDataSource("CSV")}
                  className={`p-5 rounded-2xl border text-left transition-all cursor-pointer ${
                    selectedDataSource === "CSV"
                      ? "bg-[#D79A43]/10 border-[#D79A43]/40 text-[#F5F0E8]"
                      : "bg-[#11110F] border-white/[0.06] text-[#918D84] hover:border-white/20"
                  }`}
                >
                  <FileSpreadsheet className={`w-6 h-6 mb-3 ${selectedDataSource === "CSV" ? "text-[#D79A43]" : "text-[#66625B]"}`} />
                  <div className="font-mono text-xs font-bold text-[#F5F0E8]">Import CSV</div>
                  <div className="text-[10px] font-mono text-[#66625B] mt-1">Upload failure history with duplicate checking</div>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedDataSource("MANUAL")}
                  className={`p-5 rounded-2xl border text-left transition-all cursor-pointer ${
                    selectedDataSource === "MANUAL"
                      ? "bg-[#D79A43]/10 border-[#D79A43]/40 text-[#F5F0E8]"
                      : "bg-[#11110F] border-white/[0.06] text-[#918D84] hover:border-white/20"
                  }`}
                >
                  <PlusCircle className={`w-6 h-6 mb-3 ${selectedDataSource === "MANUAL" ? "text-[#D79A43]" : "text-[#66625B]"}`} />
                  <div className="font-mono text-xs font-bold text-[#F5F0E8]">Manual Entry</div>
                  <div className="text-[10px] font-mono text-[#66625B] mt-1">Add individual transactions on demand</div>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedDataSource("PROVIDER")}
                  className={`p-5 rounded-2xl border text-left transition-all cursor-pointer ${
                    selectedDataSource === "PROVIDER"
                      ? "bg-[#D79A43]/10 border-[#D79A43]/40 text-[#F5F0E8]"
                      : "bg-[#11110F] border-white/[0.06] text-[#918D84] hover:border-white/20"
                  }`}
                >
                  <CreditCard className={`w-6 h-6 mb-3 ${selectedDataSource === "PROVIDER" ? "text-[#D79A43]" : "text-[#66625B]"}`} />
                  <div className="font-mono text-xs font-bold text-[#F5F0E8]">Connect Provider</div>
                  <div className="text-[10px] font-mono text-[#66625B] mt-1">Webhook listener & API credentials</div>
                </button>
              </div>

              {/* Detail Box */}
              <div className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] font-mono text-xs space-y-3">
                {selectedDataSource === "CSV" && (
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-[#F5F0E8] flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4 text-[#D79A43]" />
                      <span>Ready to import CSV transaction files</span>
                    </div>
                    <p className="text-[11px] text-[#918D84]">
                      You will be directed to <code className="text-[#D79A43]">/dashboard/transactions/import</code> to upload your historical data with live header validation and duplicate detection.
                    </p>
                  </div>
                )}

                {selectedDataSource === "MANUAL" && (
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-[#F5F0E8] flex items-center gap-2">
                      <PlusCircle className="w-4 h-4 text-[#D79A43]" />
                      <span>Clean workspace ready for manual entry</span>
                    </div>
                    <p className="text-[11px] text-[#918D84]">
                      You will be directed to <code className="text-[#D79A43]">/dashboard/transactions/new</code> to register your first failed transaction and trigger autonomous recovery.
                    </p>
                  </div>
                )}

                {selectedDataSource === "PROVIDER" && (
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-[#F5F0E8] flex items-center gap-2">
                      <CreditCard className="w-4 h-4 text-[#D79A43]" />
                      <span>Payment Provider Telemetry Listener</span>
                    </div>
                    <p className="text-[11px] text-[#918D84]">
                      RecoverAI provides webhook URLs and API endpoints. Configure webhook listeners in Settings whenever you are ready.
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between gap-4 pt-4 border-t border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="py-3 px-5 rounded-xl bg-[#141412] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] font-mono text-xs transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleFinishOnboarding}
                    disabled={isLoading}
                    className="py-3.5 px-8 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-[#070706] border-t-transparent rounded-full animate-spin" />
                        <span>Initializing Workspace...</span>
                      </>
                    ) : (
                      <>
                        <span>Finish Onboarding & Launch</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 text-center text-[10px] font-mono text-[#66625B] flex items-center justify-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-[#20B89A]" />
            <span>Dedicated tenant isolation • Cryptographic SHA-256 audit ledger</span>
          </div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-6 text-center text-[11px] font-mono text-[#66625B] border-t border-white/[0.04]">
        © 2026 RecoverAI Platform Inc. • Autonomous Financial Recovery
      </footer>
    </div>
  );
}
