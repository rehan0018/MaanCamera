"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Inbox,
  Calendar,
  FileText,
  CreditCard,
  Star,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

export default function CustomerDashboard() {
  const [activeTab, setActiveTab] = useState<"enquiries" | "bookings" | "reviews">("bookings");

  const bookings = [
    {
      id: "bk-98214",
      professional: "Aura Weddings & Films",
      city: "Pune",
      service: "2-Day Candid & Cinematic Wedding Shoot",
      date: "Dec 18 - 19, 2026",
      amount: "â‚¹50,000",
      advancePaid: "â‚¹15,000",
      balanceDue: "â‚¹35,000",
      status: "confirmed",
      completion: "pending",
    },
    {
      id: "bk-76120",
      professional: "Drishti Visuals",
      city: "Mumbai",
      service: "Pre-Wedding Cinematic Video Teaser",
      date: "Nov 02, 2026",
      amount: "â‚¹25,000",
      advancePaid: "â‚¹25,000",
      balanceDue: "â‚¹0",
      status: "completed",
      completion: "accepted",
      reviewed: false,
    },
  ];

  const enquiries = [
    {
      id: "enq-101",
      title: "Royal Destination Wedding at Jaipur Fort",
      category: "Wedding Photography & Video",
      date: "Feb 14, 2027",
      budget: "â‚¹1,50,000",
      proposalsReceived: 3,
      status: "open",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Top Welcome */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Customer Dashboard</h1>
          <p className="text-xs text-gray-400 mt-1">Track requirements, received quotations, and confirmed shoots.</p>
        </div>
        <Link
          href="/search"
          className="px-4 py-2.5 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-xs shadow-md transition-colors flex items-center gap-1.5"
        >
          <span>Find New Professional</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-white/10 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("bookings")}
          className={`pb-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "bookings"
              ? "border-[#FF5E1E] text-white"
              : "border-transparent text-gray-400 hover:text-white"
          }`}
        >
          <Calendar className="w-4 h-4" /> My Bookings (2)
        </button>
        <button
          onClick={() => setActiveTab("enquiries")}
          className={`pb-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "enquiries"
              ? "border-[#FF5E1E] text-white"
              : "border-transparent text-gray-400 hover:text-white"
          }`}
        >
          <Inbox className="w-4 h-4" /> Active Enquiries (1)
        </button>
      </div>

      {/* Bookings View */}
      {activeTab === "bookings" && (
        <div className="space-y-4">
          {bookings.map((b) => (
            <div
              key={b.id}
              className="p-6 rounded-2xl bg-[#14151b] border border-white/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-base">{b.professional}</span>
                  <span className="text-xs text-gray-400">({b.city})</span>
                  {b.status === "confirmed" ? (
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[11px] font-semibold border border-emerald-500/20">
                      Confirmed Shoot
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[11px] font-semibold">
                      Completed & Delivered
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-300 font-medium">{b.service}</p>
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5 text-gray-500" /> {b.date}</span>
                  <span>â€¢</span>
                  <span>Total: <strong className="text-white">{b.amount}</strong></span>
                  <span>â€¢</span>
                  <span>Advance: {b.advancePaid}</span>
                  {b.balanceDue !== "â‚¹0" && (
                    <span className="text-amber-400 font-medium">Balance Due: {b.balanceDue}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3">
                {b.status === "completed" && !b.reviewed && (
                  <button
                    onClick={() => alert("Verified review dialog opened: Rate work quality, communication, punctuality, and value.")}
                    className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Star className="w-3.5 h-3.5 fill-current" />
                    <span>Submit Verified Review</span>
                  </button>
                )}
                {b.balanceDue !== "â‚¹0" && (
                  <button
                    onClick={() => alert("Payment Order initiated for balance payment.")}
                    className="px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-md transition-colors"
                  >
                    Pay Balance
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Enquiries View */}
      {activeTab === "enquiries" && (
        <div className="space-y-4">
          {enquiries.map((e) => (
            <div key={e.id} className="p-6 rounded-2xl bg-[#14151b] border border-white/10 flex items-center justify-between">
              <div className="space-y-1">
                <h3 className="font-bold text-white text-sm">{e.title}</h3>
                <p className="text-xs text-gray-400">{e.category} â€¢ Date: {e.date} â€¢ Budget: {e.budget}</p>
                <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[11px] font-medium">
                  {e.proposalsReceived} Quotations Received
                </span>
              </div>
              <button
                onClick={() => alert("Reviewing quotations received from professionals")}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
              >
                Review Quotations
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
