"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  CreditCard,
  Mail,
  User,
  AlertTriangle,
  Zap,
  ShieldCheck,
  Building2,
  Calendar,
  DollarSign,
  Tag,
  CheckCircle2,
  FileText,
  Repeat,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const FAILURE_PRESETS = [
  {
    code: "BAD_REQUEST_PAYMENT_TIMED_OUT",
    reason: "Bank authorization server did not respond within timeout window",
    category: "Temporary Failure",
  },
  {
    code: "INSUFFICIENT_FUNDS",
    reason: "Customer account balance insufficient for authorization",
    category: "Insufficient Funds",
  },
  {
    code: "CHECKOUT_ABANDONED",
    reason: "Customer navigated away before completing 3D Secure / UPI approval",
    category: "Customer Drop-off",
  },
  {
    code: "AUTHENTICATION_FAILED",
    reason: "OTP / biometric validation failed at issuer gateway",
    category: "Authentication Failure",
  },
  {
    code: "GATEWAY_ERROR",
    reason: "Payment network switch returned internal processing failure",
    category: "Temporary Failure",
  },
  {
    code: "CARD_EXPIRED",
    reason: "Payment card has passed expiration date",
    category: "Hard Decline",
  },
];

export default function NewTransactionPage() {
  const { organization } = useAuth();
  const router = useRouter();

  const [transactionId, setTransactionId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState(organization?.currency || "INR");
  const [status, setStatus] = useState("FAILED");
  const [paymentMethod, setPaymentMethod] = useState("CARD");
  const [failureCode, setFailureCode] = useState(FAILURE_PRESETS[0].code);
  const [failureReason, setFailureReason] = useState(FAILURE_PRESETS[0].reason);
  const [invoiceId, setInvoiceId] = useState("");
  const [subscriptionId, setSubscriptionId] = useState("");
  const [timestamp, setTimestamp] = useState(new Date().toISOString().slice(0, 16));

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handlePresetSelect = (code: string) => {
    setFailureCode(code);
    const matched = FAILURE_PRESETS.find((p) => p.code === code);
    if (matched) {
      setFailureReason(matched.reason);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount) {
      setError("Please specify the transaction amount.");
      return;
    }

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError("Transaction amount must be greater than zero.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      await api.createTransaction({
        transaction_id: transactionId.trim() || undefined,
        customer_id: customerId.trim() || undefined,
        customer_email: customerEmail.trim() || undefined,
        customer_name: customerName.trim() || undefined,
        amount: numAmount,
        currency,
        status,
        payment_method: paymentMethod,
        failure_code: status === "FAILED" || status === "ABANDONED" ? failureCode : undefined,
        failure_reason: status === "FAILED" || status === "ABANDONED" ? failureReason : undefined,
        invoice_id: invoiceId.trim() || undefined,
        subscription_id: subscriptionId.trim() || undefined,
        timestamp: timestamp ? new Date(timestamp).toISOString() : new Date().toISOString(),
      });

      setSavedSuccess(true);
      setTimeout(() => {
        router.push("/dashboard/transactions?created=true");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to save transaction.");
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8 pb-16 font-sans">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Back Link */}
        <Link
          href="/dashboard/transactions"
          className="inline-flex items-center gap-2 text-xs font-mono text-[#918D84] hover:text-[#F5F0E8] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Transactions</span>
        </Link>

        {/* Page Header */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#D79A43] mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D79A43] animate-pulse" />
            <span>MANUAL TRANSACTION INGESTION</span>
          </div>
          <h1 className="font-serif text-3xl font-bold tracking-tight text-[#F5F0E8]">
            Manual Transaction Entry
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Register a transaction directly to {organization?.name || "workspace"}. Failed payments evaluate revenue at risk and trigger autonomous recovery.
          </p>
        </div>

        {/* Success Alert */}
        {savedSuccess && (
          <div className="p-4 rounded-xl bg-[#20B89A]/10 border border-[#20B89A]/30 text-[#20B89A] text-xs font-mono flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-[#20B89A] shrink-0" />
            <span>Transaction saved successfully! Scoped to {organization?.name || "workspace"}. Redirecting...</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F] text-xs font-mono flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Form Container */}
        <form onSubmit={handleSubmit} className="p-8 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] backdrop-blur-xl space-y-5 font-mono text-xs">
          {/* Identifiers (Transaction ID & Customer ID) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Transaction ID (Optional / Auto-generated)
              </label>
              <div className="relative">
                <Tag className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={transactionId}
                  onChange={(e) => setTransactionId(e.target.value)}
                  placeholder="txn_custom_1001"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Customer ID (Optional)
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  placeholder="cust_user_890"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>
          </div>

          {/* Customer Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Customer Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  placeholder="customer@enterprise.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Customer Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="Vikram Malhotra"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>
          </div>

          {/* Amount, Currency & Status */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Amount *
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="14999.00"
                className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Currency
              </label>
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

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Status *
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
              >
                <option value="FAILED">FAILED</option>
                <option value="CAPTURED">CAPTURED / SUCCESS</option>
                <option value="ABANDONED">ABANDONED</option>
                <option value="AUTHORIZED">AUTHORIZED / PENDING</option>
                <option value="REFUNDED">REFUNDED</option>
              </select>
            </div>
          </div>

          {/* Payment Method & Timestamp */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Payment Method
              </label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
              >
                <option value="CARD">Credit / Debit Card</option>
                <option value="UPI">UPI Instant Rails</option>
                <option value="NETBANKING">Netbanking Direct</option>
                <option value="WALLET">Digital Wallet</option>
                <option value="SUBSCRIPTION">Recurring Mandate</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Transaction Timestamp
              </label>
              <div className="relative">
                <Calendar className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="datetime-local"
                  value={timestamp}
                  onChange={(e) => setTimestamp(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>
          </div>

          {/* Invoice ID & Subscription ID */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Invoice ID (Optional)
              </label>
              <div className="relative">
                <FileText className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={invoiceId}
                  onChange={(e) => setInvoiceId(e.target.value)}
                  placeholder="inv_rec_4021"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#918D84] uppercase tracking-wider">
                Subscription ID (Optional)
              </label>
              <div className="relative">
                <Repeat className="w-4 h-4 text-[#66625B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={subscriptionId}
                  onChange={(e) => setSubscriptionId(e.target.value)}
                  placeholder="sub_tier_pro_12"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>
          </div>

          {/* Failure Telemetry Fields (Shown when Status is FAILED or ABANDONED) */}
          {(status === "FAILED" || status === "ABANDONED") && (
            <div className="p-4 rounded-xl bg-[#141412] border border-white/[0.06] space-y-4">
              <div className="text-[11px] font-bold text-[#D79A43] uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#D79A43]" />
                <span>Failure Telemetry & Diagnostic Signal</span>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[11px] text-[#918D84]">
                  Failure Code / Diagnostic Preset
                </label>
                <select
                  value={failureCode}
                  onChange={(e) => handlePresetSelect(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] focus:outline-none focus:border-[#D79A43]"
                >
                  {FAILURE_PRESETS.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.code} — {p.category}
                    </option>
                  ))}
                  <option value="CUSTOM_FAILURE">CUSTOM_FAILURE (Enter reason below)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[11px] text-[#918D84]">
                  Failure Reason / Gateway Error Description
                </label>
                <textarea
                  rows={2}
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  placeholder="Enter human-readable gateway failure error message..."
                  className="w-full px-4 py-2.5 rounded-xl bg-[#080807] border border-white/[0.08] text-sm text-[#F5F0E8] placeholder:text-[#4A4742] focus:outline-none focus:border-[#D79A43]"
                />
              </div>
            </div>
          )}

          {/* Submit CTA */}
          <div className="pt-4 flex items-center justify-between border-t border-white/[0.06]">
            <Link
              href="/dashboard/transactions"
              className="py-3 px-5 rounded-xl bg-[#141412] text-[#918D84] hover:text-[#F5F0E8] border border-white/[0.08] transition-colors"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isLoading || savedSuccess}
              className="py-3.5 px-8 rounded-xl bg-[#D79A43] text-[#070706] hover:bg-[#F0B84B] font-bold transition-all shadow-gold flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#070706] border-t-transparent rounded-full animate-spin" />
                  <span>Saving Transaction...</span>
                </>
              ) : (
                <>
                  <span>Save & Ingest Transaction</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
