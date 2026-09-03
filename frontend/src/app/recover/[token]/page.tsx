"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  CreditCard,
  Lock,
  ArrowRight,
  RefreshCw,
  Building2,
  ChevronRight,
  XCircle,
  HelpCircle,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";

export default function CustomerRecoveryPage() {
  const params = useParams();
  const token = params.token as string;

  const [data, setData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isOptedOut, setIsOptedOut] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState<any | null>(null);

  const loadTokenData = async () => {
    try {
      setIsLoading(true);
      setErrorStatus(null);
      const res = await api.getRecoveryTokenData(token);
      setData(res);
      if (res.status === "EXPIRED") setErrorStatus("EXPIRED");
      else if (res.status === "USED") setErrorStatus("USED");
      else if (res.status === "REVOKED") setErrorStatus("REVOKED");
    } catch (err: any) {
      console.error("Failed to load recovery link:", err);
      setErrorStatus("INVALID");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) loadTokenData();
  }, [token]);

  const handleContinuePayment = async () => {
    try {
      setIsProcessing(true);
      const res = await api.initiateCustomerPayment(token);

      if (res.flow === "REDIRECT" && res.redirect_url) {
        // Redirect to provider checkout
        window.location.href = res.redirect_url;
        return;
      }

      // Test/Sandbox Flow Execution
      const completeRes = await api.completeSandboxRecovery(token);
      setPaymentSuccess(completeRes);
    } catch (err: any) {
      console.error("Payment attempt error:", err);
      setErrorStatus("FAILED");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOptOut = async () => {
    try {
      setIsProcessing(true);
      await api.optOutFromRecoveryLink(token);
      setIsOptedOut(true);
    } catch (err) {
      console.error("Opt-out error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const currencySymbol =
    data?.currency === "USD" ? "$" : data?.currency === "EUR" ? "€" : data?.currency === "GBP" ? "£" : "₹";

  return (
    <div className="min-h-screen bg-[#070706] text-[#F5F0E8] flex flex-col justify-between p-4 sm:p-8 font-sans selection:bg-[#D79A43] selection:text-black">
      {/* Top Header / Branding */}
      <header className="max-w-md w-full mx-auto flex items-center justify-between py-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#D79A43] flex items-center justify-center text-black font-serif font-bold text-sm">
            R
          </div>
          <span className="font-serif text-sm font-bold tracking-tight text-[#F5F0E8]">
            RecoverAI Secure Pay
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#918D84]">
          <Lock className="w-3.5 h-3.5 text-[#20B89A]" />
          <span>256-bit SSL</span>
        </div>
      </header>

      {/* Main Card */}
      <main className="max-w-md w-full mx-auto my-auto">
        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-white/[0.08] text-center space-y-4 shadow-2xl"
            >
              <RefreshCw className="w-8 h-8 text-[#D79A43] animate-spin mx-auto" />
              <p className="text-xs font-mono text-[#918D84]">Verifying secure payment session...</p>
            </motion.div>
          ) : isOptedOut ? (
            /* Opt-Out State */
            <motion.div
              key="opted_out"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-white/[0.08] text-center space-y-4 shadow-2xl font-mono text-xs"
            >
              <div className="w-12 h-12 rounded-2xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-[#918D84] mx-auto">
                <Check className="w-6 h-6" />
              </div>
              <h2 className="font-sans font-bold text-xl text-[#F5F0E8]">Preferences Updated</h2>
              <p className="text-[#918D84] leading-relaxed">
                You have been unsubscribed from automated payment recovery communications for this transaction.
              </p>
            </motion.div>
          ) : paymentSuccess ? (
            /* Success State */
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-[#20B89A]/30 text-center space-y-6 shadow-[0_16px_48px_rgba(32,184,154,0.15)] font-mono text-xs"
            >
              <div className="w-14 h-14 rounded-2xl bg-[#20B89A]/15 border border-[#20B89A]/30 flex items-center justify-center text-[#20B89A] mx-auto">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="space-y-1">
                <span className="text-[10px] uppercase tracking-widest text-[#20B89A] font-bold">
                  PAYMENT RECOVERED
                </span>
                <h2 className="font-serif text-2xl font-bold text-[#F5F0E8]">
                  Payment Completed Successfully
                </h2>
                <p className="text-sm font-sans text-[#D79A43] pt-1 font-bold">
                  {currencySymbol}{paymentSuccess.amount?.toLocaleString()} to {paymentSuccess.merchant_name}
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-[#0D0D0B] border border-white/[0.06] text-left space-y-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-[#66625B]">Recipient:</span>
                  <span className="text-[#F5F0E8] font-bold">{paymentSuccess.merchant_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#66625B]">Status:</span>
                  <span className="text-[#20B89A] font-bold">Verified & Settled</span>
                </div>
              </div>

              <p className="text-[11px] text-[#66625B]">
                A receipt has been recorded. You may safely close this window.
              </p>
            </motion.div>
          ) : errorStatus === "EXPIRED" ? (
            /* Expired Link State */
            <motion.div
              key="expired"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-white/[0.08] text-center space-y-4 shadow-2xl font-mono text-xs"
            >
              <Clock className="w-12 h-12 text-[#D79A43] mx-auto mb-2" />
              <h2 className="font-sans font-bold text-xl text-[#F5F0E8]">Recovery Link Expired</h2>
              <p className="text-[#918D84] leading-relaxed">
                This secure recovery link has expired for your protection. Please contact{" "}
                <strong className="text-[#F5F0E8]">{data?.merchant_name || "the merchant"}</strong> for an updated link.
              </p>
            </motion.div>
          ) : errorStatus === "USED" ? (
            /* Used Link State */
            <motion.div
              key="used"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-white/[0.08] text-center space-y-4 shadow-2xl font-mono text-xs"
            >
              <CheckCircle2 className="w-12 h-12 text-[#20B89A] mx-auto mb-2" />
              <h2 className="font-sans font-bold text-xl text-[#F5F0E8]">Link Already Used</h2>
              <p className="text-[#918D84] leading-relaxed">
                This payment recovery link has already been completed. No further action is required.
              </p>
            </motion.div>
          ) : errorStatus === "INVALID" ? (
            /* Invalid Link State */
            <motion.div
              key="invalid"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-[#E56B6F]/30 text-center space-y-4 shadow-2xl font-mono text-xs"
            >
              <XCircle className="w-12 h-12 text-[#E56B6F] mx-auto mb-2" />
              <h2 className="font-sans font-bold text-xl text-[#F5F0E8]">Invalid Recovery Link</h2>
              <p className="text-[#918D84] leading-relaxed">
                We could not find a valid payment session for this link. Please verify the URL or contact the merchant.
              </p>
            </motion.div>
          ) : (
            /* Active Recovery State */
            <motion.div
              key="active"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-3xl bg-[#11110F] border border-white/[0.1] shadow-2xl space-y-6"
            >
              {/* Test / Sandbox Notice */}
              {data?.is_test_mode && (
                <div className="p-3 rounded-2xl bg-[#D79A43]/10 border border-[#D79A43]/30 text-[11px] font-mono text-[#D79A43] flex items-center justify-between">
                  <span className="font-bold">● TEST / SANDBOX MODE</span>
                  <span className="text-[10px] text-[#918D84]">Simulated settlement</span>
                </div>
              )}

              {/* Merchant Title & Prompt */}
              <div className="space-y-1 text-center sm:text-left">
                <div className="flex items-center gap-2 text-xs font-mono text-[#918D84]">
                  <Building2 className="w-3.5 h-3.5 text-[#D79A43]" />
                  <span>{data?.merchant_name}</span>
                </div>
                <h1 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F0E8]">
                  Your payment needs attention
                </h1>
                <p className="text-xs font-mono text-[#918D84] pt-1">
                  Hi {data?.customer_first_name || "there"}, we couldn&apos;t complete your recent transaction. Please finalize your payment below.
                </p>
              </div>

              {/* Amount Display */}
              <div className="p-6 rounded-2xl bg-[#0D0D0B] border border-white/[0.06] text-center space-y-1">
                <span className="text-[11px] font-mono uppercase text-[#66625B] tracking-wider">
                  Amount Due
                </span>
                <div className="font-serif text-4xl font-bold text-[#F5F0E8]">
                  {currencySymbol}{data?.amount ? data.amount.toLocaleString() : "0"}
                </div>
                <span className="text-[10px] font-mono text-[#20B89A]">
                  Encrypted & Secure • Single-use session
                </span>
              </div>

              {/* Action Button */}
              <div className="space-y-3">
                <button
                  onClick={handleContinuePayment}
                  disabled={isProcessing}
                  className="w-full py-4 rounded-2xl font-mono text-sm font-bold bg-[#D79A43] text-black hover:bg-[#F0B84B] transition-all shadow-[0_8px_24px_rgba(215,154,67,0.3)] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>PROCESSING SECURE PAYMENT...</span>
                    </>
                  ) : (
                    <>
                      <span>
                        {data?.action_type === "PAYMENT_METHOD_UPDATE"
                          ? "UPDATE PAYMENT METHOD"
                          : "CONTINUE PAYMENT"}
                      </span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <div className="flex items-center justify-center gap-2 text-[11px] font-mono text-[#66625B]">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#20B89A]" />
                  <span>Powered by RecoverAI Enterprise Gateway</span>
                </div>
              </div>

              {/* Opt-out suppression footer */}
              <div className="pt-4 border-t border-white/[0.04] text-center">
                <button
                  onClick={handleOptOut}
                  className="text-[11px] font-mono text-[#66625B] hover:text-[#918D84] hover:underline cursor-pointer"
                >
                  Stop recovery messages for this order
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Page Footer */}
      <footer className="max-w-md w-full mx-auto py-4 text-center text-[10px] font-mono text-[#66625B]">
        RecoverAI Autonomous Revenue Recovery Platform • Multi-Tenant Enterprise Security
      </footer>
    </div>
  );
}
