"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Zap, ArrowLeft, Mail, AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError("Please enter your email address.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      await api.forgotPassword(email);
      setIsSubmitted(true);
    } catch (err: any) {
      // Keep UX generic for security
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070706] text-[#F5F0E8] flex flex-col justify-between selection:bg-[#D79A43]/20 relative overflow-hidden font-sans">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-[#D79A43]/[0.03] blur-[150px] pointer-events-none" />

      {/* Header */}
      <header className="px-6 sm:px-12 py-8 flex items-center justify-between relative z-10">
        <Link href="/" className="flex items-center gap-3 group cursor-pointer">
          <div className="w-8 h-8 rounded-xl bg-[#D79A43]/15 border border-[#D79A43]/30 flex items-center justify-center text-[#D79A43] group-hover:scale-105 transition-transform">
            <Zap className="w-4 h-4 fill-[#D79A43]" />
          </div>
          <span className="font-sans font-bold text-lg tracking-tight text-[#F5F0E8]">
            Recover<span className="text-[#D79A43]">AI</span>
          </span>
        </Link>

        <Link
          href="/login"
          className="flex items-center gap-2 text-xs font-mono text-[#918D84] hover:text-[#F5F0E8] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Sign In</span>
        </Link>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-6 py-12 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          className="w-full max-w-md"
        >
          <div className="mb-8 text-center sm:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
              <span>CREDENTIAL RECOVERY</span>
            </div>

            <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8] leading-tight">
              Reset your password.
            </h1>
            <p className="text-xs font-mono text-[#918D84] mt-2">
              Enter your work email address to receive password reset instructions.
            </p>
          </div>

          <div className="p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] backdrop-blur-xl">
            {isSubmitted ? (
              <div className="space-y-4 text-center py-4">
                <div className="w-12 h-12 rounded-full bg-[#20B89A]/15 border border-[#20B89A]/30 text-[#20B89A] flex items-center justify-center mx-auto">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="text-base font-serif font-bold text-[#F5F0E8]">
                  Instructions Dispatched
                </h3>
                <p className="text-xs font-mono text-[#918D84] leading-relaxed">
                  If an account exists with that email, password reset instructions have been dispatched.
                </p>
                <div className="pt-4">
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#171614] border border-white/[0.08] text-xs font-mono text-[#F5F0E8] hover:text-[#D79A43] hover:border-[#D79A43]/40 transition-all cursor-pointer"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Return to Sign In</span>
                  </Link>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                {error && (
                  <div className="p-3 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] text-xs font-mono flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="block text-[11px] font-mono text-[#918D84] uppercase tracking-wider">
                    Work Email
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="alex@apexfintech.com"
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43] transition-colors font-mono"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3.5 px-6 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-mono text-xs font-bold transition-all shadow-gold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isLoading ? (
                    <div className="w-4 h-4 border-2 border-[#070706] border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <span>Send Reset Instructions</span>
                  )}
                </button>
              </form>
            )}
          </div>

          <div className="mt-6 text-center text-[10px] font-mono text-[#66625B] flex items-center justify-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-[#20B89A]" />
            <span>Cryptographic reset token validity • Generic response policy</span>
          </div>
        </motion.div>
      </main>

      <footer className="px-6 py-6 text-center text-[11px] font-mono text-[#66625B] border-t border-white/[0.04]">
        © 2026 RecoverAI Platform Inc. • Autonomous Financial Recovery
      </footer>
    </div>
  );
}
