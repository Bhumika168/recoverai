"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Zap, ArrowRight, Lock, Mail, User, Building2, AlertTriangle, ShieldCheck, Check } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function SignUpPage() {
  const { signup } = useAuth();
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Password strength checks
  const hasMinLength = password.length >= 8;
  const hasLetterAndNumber = /[a-zA-Z]/.test(password) && /[0-9]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !email || !password || !confirmPassword) {
      setError("Please complete all required fields.");
      return;
    }

    if (!hasMinLength) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (!passwordsMatch) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      await signup({
        full_name: fullName,
        email,
        password,
        company_name: companyName || undefined,
      });
      window.location.href = "/onboarding";
    } catch (err: any) {
      setError(err.message || "Failed to create account. Please check your details.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070706] text-[#F5F0E8] flex flex-col justify-between selection:bg-[#D79A43]/20 relative overflow-hidden font-sans">
      {/* Ambient background lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[#D79A43]/[0.03] blur-[150px] pointer-events-none" />
      <div className="absolute -bottom-24 right-1/4 w-[500px] h-[250px] bg-[#20B89A]/[0.02] blur-[140px] pointer-events-none" />

      {/* Top Header */}
      <header className="px-6 sm:px-12 py-8 flex items-center justify-between relative z-10">
        <Link href="/" className="flex items-center gap-3 group cursor-pointer">
          <div className="w-8 h-8 rounded-xl bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43] group-hover:scale-105 transition-transform">
            <Zap className="w-4 h-4 fill-[#D79A43]" />
          </div>
          <span className="font-sans font-bold text-lg tracking-tight text-[#F5F0E8]">
            Recover<span className="text-[#D79A43]">AI</span>
          </span>
        </Link>

        <div className="flex items-center gap-4 text-xs font-mono">
          <span className="text-[#66625B] hidden sm:inline">Already have an organization?</span>
          <Link
            href="/login"
            className="px-4 py-2 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] hover:border-[#D79A43]/40 hover:text-[#D79A43] transition-all cursor-pointer"
          >
            Sign In
          </Link>
        </div>
      </header>

      {/* Center Auth Card */}
      <main className="flex-1 flex items-center justify-center px-6 py-12 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          className="w-full max-w-lg"
        >
          {/* Headline */}
          <div className="mb-8 text-center sm:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#20B89A] mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-[#20B89A] animate-pulse" />
              <span>ENTERPRISE ONBOARDING</span>
            </div>

            <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8] leading-tight">
              Start recovering revenue. <br />
              <span className="italic font-normal text-[#D79A43]">In minutes.</span>
            </h1>
            <p className="text-xs font-mono text-[#918D84] mt-2">
              Create your organization and configure autonomous payment recovery pipelines.
            </p>
          </div>

          {/* Form Card */}
          <div className="p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] backdrop-blur-xl space-y-6">
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="p-3.5 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] text-xs font-mono flex items-start gap-2.5"
              >
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name & Company Name */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                    Full Name *
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      required
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Alex Vance"
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                    Company Name
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="Acme Payments, Nova..."
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Work Email */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                  Work Email *
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="alex@company.com"
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                  />
                </div>
              </div>

              {/* Passwords */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                    Password *
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                    Confirm Password *
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Password Requirements Checklist */}
              <div className="p-3 rounded-xl bg-[#080807] border border-white/[0.05] space-y-1.5 text-[11px] font-mono">
                <div className="flex items-center gap-2">
                  <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center ${hasMinLength ? "bg-[#20B89A] text-[#070706]" : "bg-white/10 text-[#66625B]"}`}>
                    <Check className="w-2.5 h-2.5" />
                  </div>
                  <span className={hasMinLength ? "text-[#20B89A]" : "text-[#66625B]"}>Minimum 8 characters</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center ${passwordsMatch ? "bg-[#20B89A] text-[#070706]" : "bg-white/10 text-[#66625B]"}`}>
                    <Check className="w-2.5 h-2.5" />
                  </div>
                  <span className={passwordsMatch ? "text-[#20B89A]" : "text-[#66625B]"}>Passwords match</span>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3.5 px-6 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-[#070706] border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Create Organization & Launch</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="mt-6 text-center text-[10px] font-mono text-[#66625B] flex items-center justify-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-[#20B89A]" />
            <span>Dedicated tenant boundary • Zero cross-merchant data leakage</span>
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
