"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Camera,
  MapPin,
  ShieldCheck,
  Star,
  Send,
  Loader2,
  AlertCircle,
  Flag,
  Sparkles,
  Wrench,
} from "lucide-react";
import { ApiClientError, api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";

function ProfileDetailContent() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const { notify } = useToast();
  const profSlugOrId = params?.id || "";

  const [profile, setProfile] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [aiSummary, setAiSummary] = useState<{ summary: string; highlights: string[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showEnquiryModal, setShowEnquiryModal] = useState(searchParams.get("enquire") === "1");
  const [enqTitle, setEnqTitle] = useState("");
  const [enqCategoryId, setEnqCategoryId] = useState("");
  const [enqDescription, setEnqDescription] = useState("");
  const [enqDate, setEnqDate] = useState("");
  const [enqCity, setEnqCity] = useState("");
  const [enqLocation, setEnqLocation] = useState("");
  const [enqBudgetInr, setEnqBudgetInr] = useState("50000");
  const [submittingEnquiry, setSubmittingEnquiry] = useState(false);

  const loadAll = useCallback(async () => {
    if (!profSlugOrId) return;
    setLoading(true);
    setError(null);
    try {
      const [profRes, catRes] = await Promise.all([
        api.getProfessional(profSlugOrId),
        api.getCategories(),
      ]);
      const p = profRes.data;
      setProfile(p);
      setEnqCity(p.base_city || "Pune");
      const cats = Array.isArray(catRes.data) ? catRes.data : [];
      setCategories(cats);
      if (p.services?.[0]?.category_id) {
        setEnqCategoryId(p.services[0].category_id);
      } else if (cats[0]?.id) {
        setEnqCategoryId(cats[0].id);
      }

      const [portRes, revRes] = await Promise.all([
        api.getProfessionalPortfolios(p.id),
        api.getProfessionalReviews(p.id),
      ]);
      const ports = Array.isArray(portRes.data) ? portRes.data : [];
      setReviews(Array.isArray(revRes.data) ? revRes.data : []);

      const projectBatches = await Promise.all(
        ports.map((pt: any) => api.getPortfolioProjects(pt.id).catch(() => ({ data: [] })))
      );
      const flatProjects = projectBatches.flatMap((batch) =>
        Array.isArray(batch.data) ? batch.data : []
      );
      setProjects(flatProjects);
    } catch (err: any) {
      setError(err?.message || "Unable to load studio profile.");
    } finally {
      setLoading(false);
    }
  }, [profSlugOrId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSubmitEnquiry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      notify("Sign in first to send a direct enquiry.", "info");
      router.push(`/login?next=${encodeURIComponent(`/professionals/${profSlugOrId}?enquire=1`)}`);
      return;
    }
    if (!profile || !enqCategoryId) return;
    setSubmittingEnquiry(true);
    try {
      const budgetMinor = Math.max(0, Number(enqBudgetInr || "0") * 100);
      await api.createEnquiry({
        category_id: enqCategoryId,
        title: enqTitle.trim(),
        description: enqDescription.trim(),
        shoot_date: enqDate || undefined,
        duration_days: 1,
        location: enqLocation.trim() || enqCity.trim(),
        city: enqCity.trim(),
        budget_max_minor: budgetMinor > 0 ? budgetMinor : undefined,
        currency_code: "INR",
        professional_ids: [profile.id],
      });
      notify("Enquiry sent directly to " + profile.display_name, "success");
      setShowEnquiryModal(false);
      router.push("/customer/dashboard");
    } catch (err: any) {
      notify(err?.message || "Failed to send enquiry.", "error");
    } finally {
      setSubmittingEnquiry(false);
    }
  };

  const handleSummarizeReviews = async () => {
    if (!profile) return;
    try {
      const res = await api.summarizeReviews(profile.id);
      setAiSummary(res.data);
    } catch (err: any) {
      if (err instanceof ApiClientError && err.status === 401) {
        notify("Sign in to view AI review synthesis.", "info");
      } else {
        notify(err?.message || "Failed to synthesize reviews.", "error");
      }
    }
  };

  const handleReportReview = async (reviewId: string) => {
    if (!user) {
      notify("Please sign in to report a review.", "info");
      return;
    }
    try {
      await api.reportReview(reviewId, {
        reason: "inappropriate",
        details: "Flagged from studio profile for moderator review",
      });
      notify("Review flagged for admin moderation.", "success");
    } catch (err: any) {
      notify(err?.message || "Could not submit content report.", "error");
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading studio portfolio...
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 space-y-4">
        <Link href="/search" className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white">
          <ArrowLeft className="w-4 h-4" /> Back to Search
        </Link>
        <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error || "Studio profile not found."}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      <Link href="/search" className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white">
        <ArrowLeft className="w-4 h-4" /> Back to Professionals Directory
      </Link>

      {/* Studio Header */}
      <div className="p-8 rounded-3xl bg-[#14151b] border border-white/10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="space-y-3 max-w-2xl">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-extrabold text-white">{profile.display_name}</h1>
            {profile.verification_status === "verified" && (
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 text-xs font-semibold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" /> Verified Studio
              </span>
            )}
          </div>
          {profile.headline && <p className="text-sm text-gray-300">{profile.headline}</p>}
          {profile.biography && <p className="text-xs text-gray-400 leading-relaxed">{profile.biography}</p>}
          <div className="flex flex-wrap items-center gap-4 text-xs text-gray-300 pt-1">
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-[#FF5E1E]" />
              {profile.base_city}, {profile.state}
            </span>
            <span>•</span>
            <span>{profile.years_experience} Years Experience</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
              {Number(profile.avg_rating || 0).toFixed(1)} ({profile.total_reviews} approved reviews)
            </span>
            <span>•</span>
            <span>{profile.completed_bookings_count} Completed Bookings</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link
            href={`/compare?ids=${encodeURIComponent(profile.id)}`}
            className="px-4 py-2.5 rounded-xl border border-white/15 hover:border-white/30 text-xs font-semibold text-gray-200"
          >
            Compare Studio
          </Link>
          <button
            type="button"
            onClick={() => setShowEnquiryModal(true)}
            className="px-5 py-2.5 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-[#FF5E1E]/20"
          >
            <Send className="w-3.5 h-3.5" /> Request Quotation
          </button>
        </div>
      </div>

      {/* Services & Equipment */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
          <h2 className="text-base font-bold text-white">Services & Packages</h2>
          {Array.isArray(profile.services) && profile.services.length > 0 ? (
            <div className="space-y-3">
              {profile.services.map((svc: any) => (
                <div key={svc.id} className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 space-y-2">
                  <div className="flex items-center justify-between gap-4">
                    <div className="font-bold text-white text-sm">{svc.name}</div>
                    <span className="text-xs font-bold text-[#FF5E1E]">
                      Starting ₹{Math.round((svc.starting_price_minor || 0) / 100).toLocaleString("en-IN")}
                    </span>
                  </div>
                  {svc.description && <p className="text-xs text-gray-400">{svc.description}</p>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-500">No active services published yet.</p>
          )}
        </div>

        <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Wrench className="w-4 h-4 text-[#FF5E1E]" /> Gear & Capabilities
          </h2>
          {Array.isArray(profile.equipment_list) && profile.equipment_list.length > 0 ? (
            <ul className="space-y-2 text-xs text-gray-300">
              {profile.equipment_list.map((eq: any) => (
                <li key={eq.id} className="flex items-center justify-between p-2.5 rounded-lg bg-[#1a1b24]">
                  <span>{eq.brand} {eq.model}</span>
                  <span className="text-[10px] uppercase text-gray-500">{eq.equipment_type}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-500">Camera gear details pending verification.</p>
          )}
        </div>
      </div>

      {/* Published Portfolio Projects */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white">Published Portfolios ({projects.length})</h2>
        {projects.length === 0 ? (
          <div className="p-8 rounded-2xl bg-[#14151b] border border-white/10 text-xs text-gray-400">
            No published portfolio projects yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {projects.map((proj) => (
              <div key={proj.id} className="p-5 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
                <div>
                  <h3 className="font-bold text-white text-base">{proj.title}</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {proj.style || "Featured Shoot"} {proj.location ? `• ${proj.location}` : ""}
                  </p>
                  {proj.description && <p className="text-xs text-gray-300 mt-2">{proj.description}</p>}
                </div>
                {Array.isArray(proj.media_assets) && proj.media_assets.length > 0 ? (
                  <div className="grid grid-cols-2 gap-2">
                    {proj.media_assets.map((asset: any) => (
                      <div key={asset.id} className="h-36 rounded-xl overflow-hidden bg-black/40 border border-white/5 flex items-center justify-center">
                        {asset.public_url ? (
                          <img src={asset.public_url} alt={proj.title} className="w-full h-full object-cover" />
                        ) : (
                          <div className="text-[11px] text-gray-500 text-center px-2">
                            <Camera className="w-5 h-5 mx-auto mb-1 text-gray-600" />
                            <span>Asset processing</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500">No public gallery images in this project yet.</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Verified Reviews */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-white">Verified Booking Reviews ({reviews.length})</h2>
          {reviews.length > 0 && (
            <button
              type="button"
              onClick={handleSummarizeReviews}
              className="px-3.5 py-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 text-purple-200 text-xs font-semibold flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" /> Synthesize Highlights
            </button>
          )}
        </div>

        {aiSummary && (
          <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/25 text-xs space-y-2">
            <p className="text-gray-200">{aiSummary.summary}</p>
            {aiSummary.highlights?.length > 0 && (
              <ul className="list-disc pl-5 text-purple-200 space-y-1">
                {aiSummary.highlights.map((h) => (
                  <li key={h}>{h}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {reviews.length === 0 ? (
          <p className="text-xs text-gray-400">No moderator-approved reviews published yet.</p>
        ) : (
          <div className="space-y-3">
            {reviews.map((rev) => (
              <div key={rev.id} className="p-4 rounded-xl bg-[#1a1b24] border border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 text-xs font-semibold text-amber-400">
                    <Star className="w-3.5 h-3.5 fill-current" />
                    <span>{Number(rev.overall_rating).toFixed(1)} / 5.0</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleReportReview(rev.id)}
                    className="text-[11px] text-gray-400 hover:text-red-300 flex items-center gap-1"
                  >
                    <Flag className="w-3 h-3" /> Report
                  </button>
                </div>
                <p className="text-xs text-gray-200 leading-relaxed">{rev.review_text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Direct Enquiry Modal */}
      {showEnquiryModal && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleSubmitEnquiry}
            className="w-full max-w-lg p-6 rounded-2xl bg-[#14151b] border border-white/15 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Send Enquiry to {profile.display_name}</h2>
              <button type="button" onClick={() => setShowEnquiryModal(false)} className="text-xs text-gray-400 hover:text-white">
                Close
              </button>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300">Category</label>
              <select
                required
                value={enqCategoryId}
                onChange={(e) => setEnqCategoryId(e.target.value)}
                className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300">Enquiry Title</label>
              <input
                type="text"
                required
                value={enqTitle}
                onChange={(e) => setEnqTitle(e.target.value)}
                placeholder="e.g. 2-Day Wedding Candid & Highlight Film"
                className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">City</label>
                <input
                  type="text"
                  required
                  value={enqCity}
                  onChange={(e) => setEnqCity(e.target.value)}
                  className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Max Budget (INR)</label>
                <input
                  type="number"
                  min={0}
                  value={enqBudgetInr}
                  onChange={(e) => setEnqBudgetInr(e.target.value)}
                  className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Venue / Area</label>
                <input
                  type="text"
                  required
                  value={enqLocation}
                  onChange={(e) => setEnqLocation(e.target.value)}
                  placeholder="e.g. Koregaon Park"
                  className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Target Shoot Date</label>
                <input
                  type="date"
                  value={enqDate}
                  onChange={(e) => setEnqDate(e.target.value)}
                  className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300">Requirements & Deliverables</label>
              <textarea
                required
                rows={3}
                value={enqDescription}
                onChange={(e) => setEnqDescription(e.target.value)}
                placeholder="Share shoot timings, deliverables needed, and style preferences..."
                className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
              />
            </div>

            <button
              type="submit"
              disabled={submittingEnquiry}
              className="w-full py-2.5 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] disabled:opacity-50 text-white font-semibold text-xs"
            >
              {submittingEnquiry ? "Sending Enquiry..." : "Submit Enquiry"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default function ProfessionalProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading studio...
        </div>
      }
    >
      <ProfileDetailContent />
    </Suspense>
  );
}
