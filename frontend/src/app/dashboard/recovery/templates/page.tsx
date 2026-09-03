"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Plus,
  RefreshCw,
  Eye,
  CheckCircle2,
  AlertTriangle,
  X,
  ArrowLeft,
  Copy,
  Languages,
  Mail,
  Smartphone,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeLanguage, setActiveLanguage] = useState<string>("ALL");
  const [notice, setNotice] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Preview Modal
  const [previewTemplate, setPreviewTemplate] = useState<any | null>(null);
  const [renderedPreview, setRenderedPreview] = useState<{ subject?: string; body: string } | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  // Create Template Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState("");
  const [channel, setChannel] = useState("EMAIL");
  const [language, setLanguage] = useState("EN");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadTemplates = async () => {
    try {
      setIsLoading(true);
      const data = await api.getTemplates(undefined, activeLanguage === "ALL" ? undefined : activeLanguage);
      setTemplates(data);
    } catch (err: any) {
      console.error("Failed to load templates:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, [activeLanguage]);

  const handleOpenPreview = async (t: any) => {
    setPreviewTemplate(t);
    setIsPreviewLoading(true);
    try {
      const res = await api.previewTemplate({ body: t.body, subject: t.subject });
      setRenderedPreview({
        subject: res.rendered_subject,
        body: res.rendered_body,
      });
    } catch (err) {
      setRenderedPreview({
        subject: t.subject,
        body: t.body,
      });
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setModalError(null);

      await api.createTemplate({
        name,
        channel,
        language,
        subject: channel === "EMAIL" ? subject : undefined,
        body,
      });

      setNotice({ text: `Template '${name}' created!`, type: "success" });
      setShowCreateModal(false);
      setName("");
      setSubject("");
      setBody("");
      await loadTemplates();
    } catch (err: any) {
      setModalError(err.message || "Failed to create template.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const insertVariable = (varName: string) => {
    setBody((prev) => `${prev} {{${varName}}}`);
  };

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Back Link */}
      <Link
        href="/dashboard/recovery/campaigns"
        className="inline-flex items-center gap-2 text-xs font-mono text-[#918D84] hover:text-[#F5F0E8] transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Campaigns</span>
      </Link>

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#121210] border border-white/[0.08] text-[11px] font-mono text-[#20B89A] mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#20B89A] animate-pulse" />
            <span>COMMUNICATION TEMPLATE ENGINE</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
            Message Templates
          </h1>
          <p className="text-xs font-mono text-[#918D84] mt-1">
            Multi-language, sanitized communication templates supporting English, Hindi, and Hinglish.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Language filter */}
          <div className="flex items-center p-1 rounded-xl bg-[#11110F] border border-white/[0.08] text-xs font-mono">
            {["ALL", "EN", "HINGLISH", "HI"].map((lang) => (
              <button
                key={lang}
                onClick={() => setActiveLanguage(lang)}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  activeLanguage === lang
                    ? "bg-[#D79A43] text-black font-bold"
                    : "text-[#918D84] hover:text-[#F5F0E8]"
                }`}
              >
                {lang}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#D79A43] text-black hover:bg-[#D79A43]/90 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>NEW TEMPLATE</span>
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

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {templates.map((t) => (
          <div
            key={t.id}
            className="p-6 rounded-2xl bg-[#11110F] border border-white/[0.08] shadow-xl flex flex-col justify-between space-y-4"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[#171614] border border-white/[0.08] flex items-center justify-center text-[#D79A43]">
                    {t.channel === "EMAIL" ? <Mail className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
                  </div>
                  <div>
                    <h3 className="font-sans font-bold text-sm text-[#F5F0E8]">{t.name}</h3>
                    <span className="text-[11px] font-mono text-[#918D84]">{t.channel}</span>
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded bg-[#171614] border border-white/[0.08] text-[10px] font-mono font-bold text-[#D79A43]">
                  {t.language}
                </span>
              </div>

              {t.subject && (
                <div className="text-xs font-mono text-[#918D84] truncate">
                  <span className="text-[#66625B]">Subject: </span>
                  {t.subject}
                </div>
              )}

              <div className="p-3 rounded-xl bg-[#0D0D0B] border border-white/[0.04] text-xs font-mono text-[#A8A49C] line-clamp-3 whitespace-pre-wrap">
                {t.body}
              </div>
            </div>

            <div className="pt-3 border-t border-white/[0.04] flex items-center justify-between">
              <span className="text-[10px] font-mono text-[#66625B]">ID: {t.id}</span>
              <button
                onClick={() => handleOpenPreview(t)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-[#D79A43] hover:bg-[#D79A43]/10 border border-[#D79A43]/30 transition-all cursor-pointer"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Live Preview</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Live Preview Modal */}
      <AnimatePresence>
        {previewTemplate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg p-6 sm:p-8 rounded-2xl bg-[#11110F] border border-white/[0.1] shadow-2xl space-y-6 font-mono text-xs"
            >
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <div className="flex items-center gap-2.5">
                  <Eye className="w-4 h-4 text-[#20B89A]" />
                  <h3 className="font-sans font-bold text-base text-[#F5F0E8]">Rendered Template Preview</h3>
                </div>
                <button onClick={() => setPreviewTemplate(null)} className="p-1 text-[#918D84] hover:text-[#F5F0E8]">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-[11px] text-[#918D84]">
                  <span>Channel: <strong className="text-[#F5F0E8]">{previewTemplate.channel}</strong></span>
                  <span>Language: <strong className="text-[#D79A43]">{previewTemplate.language}</strong></span>
                </div>

                {renderedPreview?.subject && (
                  <div className="p-3 rounded-xl bg-[#0D0D0B] border border-white/[0.06] text-xs">
                    <span className="text-[#66625B]">Subject: </span>
                    <span className="text-[#F5F0E8] font-bold">{renderedPreview.subject}</span>
                  </div>
                )}

                <div className="p-4 rounded-xl bg-[#0D0D0B] border border-white/[0.06] text-xs text-[#EAE6DF] whitespace-pre-wrap leading-relaxed">
                  {renderedPreview?.body}
                </div>
              </div>

              <div className="pt-3 border-t border-white/[0.06] text-right">
                <button
                  onClick={() => setPreviewTemplate(null)}
                  className="px-4 py-2 rounded-xl bg-[#171614] text-[#F5F0E8] hover:bg-[#201F1D] border border-white/[0.08] cursor-pointer"
                >
                  Close Preview
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Create Template Modal */}
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
                <h2 className="font-sans font-bold text-base text-[#F5F0E8]">Create Message Template</h2>
                <button onClick={() => setShowCreateModal(false)} className="p-1 text-[#918D84] hover:text-[#F5F0E8]">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {modalError && (
                <div className="p-3 rounded-xl bg-[#E56B6F]/10 border border-[#E56B6F]/30 text-[#E56B6F]">
                  {modalError}
                </div>
              )}

              <form onSubmit={handleCreateTemplate} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase">Template Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. VIP Urgent Payment Recovery"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Channel</label>
                    <select
                      value={channel}
                      onChange={(e) => setChannel(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    >
                      <option value="EMAIL">Email</option>
                      <option value="WHATSAPP">WhatsApp</option>
                      <option value="SMS">SMS</option>
                      <option value="IN_APP">In-App Notification</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Language</label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    >
                      <option value="EN">English</option>
                      <option value="HINGLISH">Hinglish (Hindi in Latin script)</option>
                      <option value="HI">Hindi (Devanagari)</option>
                    </select>
                  </div>
                </div>

                {channel === "EMAIL" && (
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-[#918D84] uppercase">Email Subject</label>
                    <input
                      type="text"
                      placeholder="Payment issue for {{company_name}}"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                    />
                  </div>
                )}

                {/* Variable helper tokens */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-[#918D84]">
                    <span>Insert Variables:</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {["customer_name", "amount", "currency", "payment_method", "payment_link", "company_name"].map(
                      (v) => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => insertVariable(v)}
                          className="px-2 py-1 rounded bg-[#171614] border border-white/[0.08] text-[10px] text-[#D79A43] hover:bg-[#201F1D] cursor-pointer"
                        >
                          +{v}
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] text-[#918D84] uppercase">Message Body *</label>
                  <textarea
                    rows={5}
                    required
                    placeholder="Hi {{customer_name}}, your payment of {{currency}} {{amount}} could not be completed..."
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#141412] text-[#F5F0E8] border border-white/[0.08] focus:border-[#D79A43] focus:outline-none"
                  />
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
                    {isSubmitting ? "Saving..." : "Save Template"}
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
