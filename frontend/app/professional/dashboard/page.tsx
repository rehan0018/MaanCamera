"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  TrendingUp,
  Inbox,
  Calendar,
  Camera,
  Star,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function ProfessionalDashboard() {
  const [activeSection, setActiveSection] = useState<"overview" | "leads" | "bookings" | "portfolio">("overview");

  const stats = [
    { label: "Active Client Leads", value: "8", change: "+3 this week" },
    { label: "Confirmed Shoots", value: "14", change: "â‚¹4.2L revenue" },
    { label: "Average Rating", value: "4.92", change: "48 verified reviews" },
    { label: "Portfolio Views", value: "1,240", change: "+18% vs last month" },
  ];

  const leads = [
    {
      id: "enq-902",
      client: "Pooja & Rohan",
      type: "Destination Wedding (2 Days)",
      date: "Jan 22, 2027",
      location: "Mahabaleshwar, MH",
      budget: "â‚¹70,000",
      status: "pending_quote",
    },
    {
      id: "enq-905",
      client: "Karan Singhania",
      type: "Brand Lookbook & Commercial Fashion",
      date: "Dec 05, 2026",
      location: "Bandra, Mumbai",
      budget: "â‚¹40,000",
      status: "pending_quote",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Studio Header */}
      <div className="p-8 rounded-3xl bg-gradient-to-r from-[#171822] via-[#1a1c28] to-[#171822] border border-white/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[#FF5E1E] flex items-center justify-center font-extrabold text-white text-xl shadow-xl shadow-[#FF5E1E]/20">
            AW
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-white">Aura Weddings & Films</h1>
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold flex items-center gap-1 border border-emerald-500/20">
                <ShieldCheck className="w-3.5 h-3.5" /> Verified Studio
              </span>
            </div>
            <p className="text-xs text-gray-400">Pune, Maharashtra â€¢ Pro SaaS Plan â€¢ 8 Years Experience</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => alert("AI Assistant: Drafted customer proposal and tailored quotation generated from your package templates.")}
            className="px-4 py-2.5 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Sparkles className="w-4 h-4" /> AI Quotation Assistant
          </button>
          <button
            onClick={() => alert("Upload media dialog: Select high-res photos or videos for automatic AI tagging.")}
            className="px-4 py-2.5 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-md flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Project to Portfolio
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="p-5 rounded-2xl bg-[#14151b] border border-white/10 space-y-1">
            <span className="text-xs text-gray-400">{s.label}</span>
            <div className="text-2xl font-extrabold text-white">{s.value}</div>
            <span className="text-[11px] text-emerald-400 font-medium">{s.change}</span>
          </div>
        ))}
      </div>

      {/* Leads / Quotation Builder */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Direct Client Enquiries</h2>
            <p className="text-xs text-gray-400">High-intent leads awaiting your customized quotation</p>
          </div>
          <span className="text-xs text-[#FF5E1E] font-semibold">{leads.length} Action Needed</span>
        </div>

        <div className="space-y-4">
          {leads.map((l) => (
            <div
              key={l.id}
              className="p-5 rounded-xl bg-[#1a1b24] border border-white/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-sm">{l.client}</span>
                  <span className="text-xs text-gray-400">â€¢ {l.type}</span>
                </div>
                <div className="text-xs text-gray-400">
                  Target Date: <strong className="text-gray-200">{l.date}</strong> | Location: <strong className="text-gray-200">{l.location}</strong> | Client Budget: <strong className="text-emerald-400">{l.budget}</strong>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => alert(`Quotation modal opened for ${l.client}. Form: Scope, Deliverables, Total (Paise), Advance Required.`)}
                  className="px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-md flex items-center gap-1.5 transition-colors"
                >
                  <Send className="w-3.5 h-3.5" /> Send Digital Quotation
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
