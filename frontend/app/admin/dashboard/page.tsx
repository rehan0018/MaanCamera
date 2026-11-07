"use client";

import { useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  Users,
  Check,
  X,
  FileCheck,
  Activity,
  Layers,
} from "lucide-react";

export default function AdminDashboard() {
  const [verifications, setVerifications] = useState([
    {
      id: "v-01",
      name: "PixelCraft Studios",
      type: "Studio Agency",
      city: "Bengaluru",
      gstin: "29AABCU9603R1ZM",
      submitted: "2 hours ago",
      documents: "Business PAN & Incorporation Cert",
    },
    {
      id: "v-02",
      name: "Kabir Malhotra",
      type: "Individual Cinematographer",
      city: "Delhi NCR",
      gstin: "Govt Aadhaar + Passport",
      submitted: "5 hours ago",
      documents: "Identity & Drone DGCA License",
    },
  ]);

  const [reports, setReports] = useState([
    {
      id: "rep-1",
      target: "Review on Booking #bk-512",
      reporter: "Studio Owner",
      reason: "Suspected non-client competitor review",
      status: "pending",
    },
  ]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      <div className="flex items-center justify-between pb-6 border-b border-white/10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Platform Moderation & Trust</h1>
          <p className="text-xs text-gray-400 mt-1">Review professional verifications, dispute cases, and system health.</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
          <Activity className="w-3.5 h-3.5" /> All Services Operational
        </div>
      </div>

      {/* Verification Queue */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <div className="flex items-center gap-2 text-white font-bold text-base">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <span>Professional Verification Requests ({verifications.length})</span>
        </div>

        <div className="space-y-3">
          {verifications.map((v) => (
            <div
              key={v.id}
              className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs"
            >
              <div>
                <div className="font-bold text-white text-sm">{v.name}</div>
                <div className="text-gray-400 mt-0.5">{v.type} â€¢ {v.city} â€¢ Submitted {v.submitted}</div>
                <div className="text-gray-300 mt-1">Documents: <strong className="text-emerald-400">{v.documents}</strong></div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => {
                    alert(`Approved verification for ${v.name}`);
                    setVerifications(verifications.filter((x) => x.id !== v.id));
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-semibold flex items-center gap-1 transition-colors"
                >
                  <Check className="w-3.5 h-3.5" /> Approve Badge
                </button>
                <button
                  onClick={() => {
                    alert(`Requested additional proof for ${v.name}`);
                    setVerifications(verifications.filter((x) => x.id !== v.id));
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-gray-300 transition-colors"
                >
                  Request More Info
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Flagged Content & Disputes */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <div className="flex items-center gap-2 text-white font-bold text-base">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <span>Flagged Content & Reports</span>
        </div>

        <div className="space-y-3">
          {reports.map((r) => (
            <div
              key={r.id}
              className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 flex items-center justify-between text-xs"
            >
              <div>
                <div className="font-bold text-white">{r.target}</div>
                <div className="text-gray-400">Reporter: {r.reporter} â€¢ Reason: <span className="text-amber-400">{r.reason}</span></div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    alert("Report resolved and review maintained");
                    setReports([]);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white transition-colors"
                >
                  Dismiss Report
                </button>
                <button
                  onClick={() => {
                    alert("Review removed and recorded in audit log");
                    setReports([]);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
                >
                  Remove Content
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
