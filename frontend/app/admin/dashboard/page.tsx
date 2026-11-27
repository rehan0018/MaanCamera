"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  AlertTriangle,
  Check,
  X,
  Activity,
  Loader2,
  Star,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";

export default function AdminDashboard() {
  const { user, loading: authLoading } = useAuth();
  const { notify } = useToast();

  const [loading, setLoading] = useState(true);
  const [verifications, setVerifications] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [reviewFilter, setReviewFilter] = useState("pending");
  const [reconciling, setReconciling] = useState(false);

  const loadQueues = useCallback(async () => {
    if (!user || user.role !== "admin") return;
    setLoading(true);
    try {
      const [verRes, revRes, repRes] = await Promise.all([
        api.listAdminVerifications("pending"),
        api.listModerationReviews({ moderation_status: reviewFilter }),
        api.listAdminReports("pending"),
      ]);
      setVerifications(Array.isArray(verRes.data) ? verRes.data : []);
      setReviews(Array.isArray(revRes.data) ? revRes.data : []);
      setReports(Array.isArray(repRes.data) ? repRes.data : []);
    } catch (err: any) {
      notify(err?.message || "Failed to load admin queues.", "error");
    } finally {
      setLoading(false);
    }
  }, [user, reviewFilter, notify]);

  useEffect(() => {
    if (!authLoading && user?.role === "admin") {
      loadQueues();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, user, loadQueues]);

  const handleVerificationDecision = async (id: string, decision: "verified" | "rejected") => {
    try {
      await api.decideVerification(id, {
        decision,
        notes: decision === "verified" ? "Verified by admin" : "Additional proof requested",
      });
      notify(`Verification marked '${decision}'.`, "success");
      await loadQueues();
    } catch (err: any) {
      notify(err?.message || "Failed to decide verification.", "error");
    }
  };

  const handleReviewDecision = async (
    id: string,
    decision: "approved" | "rejected" | "under_review" | "hidden"
  ) => {
    try {
      await api.moderateReview(id, { decision, notes: `Admin moderation: ${decision}` });
      notify(`Review status updated to '${decision}'.`, "success");
      await loadQueues();
    } catch (err: any) {
      notify(err?.message || "Failed to moderate review.", "error");
    }
  };

  const handleReportResolution = async (id: string, action: "dismiss" | "hide_content") => {
    try {
      await api.resolveReport(id, { action, notes: `Moderator action: ${action}` });
      notify(`Report resolved (${action}).`, "success");
      await loadQueues();
    } catch (err: any) {
      notify(err?.message || "Failed to resolve content report.", "error");
    }
  };

  const handleReconcile = async () => {
    setReconciling(true);
    try {
      const res = await api.reconcilePayments(15);
      notify(
        `Reconciled ${res.data.checked} pending orders (${res.data.reconciled_captured} captured).`,
        "success"
      );
    } catch (err: any) {
      notify(err?.message || "Payment reconciliation failed.", "error");
    } finally {
      setReconciling(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading moderation queues...
      </div>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center space-y-4">
        <h1 className="text-2xl font-extrabold text-white">Administrator Access Required</h1>
        <p className="text-xs text-gray-400">
          Only platform admins can inspect private KYC submissions, moderate reviews, and resolve disputes.
        </p>
        <Link href="/login?next=/admin/dashboard" className="inline-block px-5 py-2.5 rounded-xl bg-[#FF5E1E] text-white text-xs font-semibold">
          Sign In as Admin
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Platform Moderation & Trust</h1>
          <p className="text-xs text-gray-400 mt-1">
            Live verification requests, pending booking reviews, content reports, and gateway reconciliation.
          </p>
        </div>
        <button
          type="button"
          disabled={reconciling}
          onClick={handleReconcile}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-white text-xs font-semibold"
        >
          {reconciling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 text-[#FF5E1E]" />}
          <span>Run Razorpay Reconciliation</span>
        </button>
      </div>

      {/* Verification Queue */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <div className="flex items-center gap-2 text-white font-bold text-base">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <span>Pending Professional Verifications ({verifications.length})</span>
        </div>
        {verifications.length === 0 ? (
          <p className="text-xs text-gray-400">No pending verification submissions.</p>
        ) : (
          <div className="space-y-3">
            {verifications.map((v) => (
              <div
                key={v.id}
                className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs"
              >
                <div>
                  <div className="font-bold text-white text-sm">{v.professional_name}</div>
                  <div className="text-gray-400 mt-0.5">
                    {v.professional_type} • {v.base_city} • Document: <strong className="text-emerald-400">{v.document_type}</strong>
                  </div>
                  {v.notes && <div className="text-gray-300 mt-1">Notes: {v.notes}</div>}
                  {v.document_access_url && (
                    <a
                      href={v.document_access_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 mt-1.5 text-[#FF5E1E] hover:underline"
                    >
                      Inspect Signed Document <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleVerificationDecision(v.id, "verified")}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" /> Approve Badge
                  </button>
                  <button
                    type="button"
                    onClick={() => handleVerificationDecision(v.id, "rejected")}
                    className="px-3.5 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30 flex items-center gap-1"
                  >
                    <X className="w-3.5 h-3.5" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Review Moderation Queue */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-white font-bold text-base">
            <Star className="w-5 h-5 text-amber-400" />
            <span>Booking Review Moderation ({reviews.length})</span>
          </div>
          <select
            value={reviewFilter}
            onChange={(e) => setReviewFilter(e.target.value)}
            className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white"
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="hidden">Hidden</option>
          </select>
        </div>

        {reviews.length === 0 ? (
          <p className="text-xs text-gray-400">No reviews in &apos;{reviewFilter}&apos; status.</p>
        ) : (
          <div className="space-y-3">
            {reviews.map((rev) => (
              <div
                key={rev.id}
                className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
              >
                <div className="space-y-1">
                  <div className="font-bold text-white">
                    Rating: {Number(rev.overall_rating).toFixed(1)}/5 • Booking {rev.booking_id.slice(0, 8)}
                  </div>
                  <p className="text-gray-300">{rev.review_text}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleReviewDecision(rev.id, "approved")}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReviewDecision(rev.id, "rejected")}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-gray-200"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReviewDecision(rev.id, "hidden")}
                    className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-300 border border-red-500/30"
                  >
                    Hide
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Flagged Content & Reports */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <div className="flex items-center gap-2 text-white font-bold text-base">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <span>Flagged Content Reports ({reports.length})</span>
        </div>
        {reports.length === 0 ? (
          <p className="text-xs text-gray-400">No pending content reports.</p>
        ) : (
          <div className="space-y-3">
            {reports.map((r) => (
              <div
                key={r.id}
                className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs"
              >
                <div>
                  <div className="font-bold text-white capitalize">
                    {r.content_type} ({r.content_id.slice(0, 8)}) — {r.reason}
                  </div>
                  <div className="text-gray-400">
                    Reporter: {r.reporter_name || "User"} {r.details ? `• ${r.details}` : ""}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleReportResolution(r.id, "dismiss")}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white"
                  >
                    Dismiss Report
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReportResolution(r.id, "hide_content")}
                    className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30"
                  >
                    Hide Target Content
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 text-[11px] text-emerald-400">
        <Activity className="w-3.5 h-3.5" /> Connected directly to PostgreSQL admin queues and audit logging.
      </div>
    </div>
  );
}
