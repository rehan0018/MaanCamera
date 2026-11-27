"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Calendar,
  Camera,
  Plus,
  Send,
  ShieldCheck,
  Loader2,
  AlertCircle,
  Upload,
  Eye,
  Trash2,
  FileCheck,
  CheckCircle2,
} from "lucide-react";
import { api, computeFileSha256, uploadFileToPresignedUrl } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";

export default function ProfessionalDashboard() {
  const { user, loading: authLoading } = useAuth();
  const { notify } = useToast();

  const [activeTab, setActiveTab] = useState<"leads" | "bookings" | "portfolio" | "verification">("leads");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [profile, setProfile] = useState<any>(null);
  const [categories, setCategories] = useState<any[]>([]);
  const [enquiries, setEnquiries] = useState<any[]>([]);
  const [quotations, setQuotations] = useState<any[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [verifications, setVerifications] = useState<any[]>([]);

  // Profile onboarding forms
  const [studioName, setStudioName] = useState("");
  const [headline, setHeadline] = useState("");
  const [biography, setBiography] = useState("");
  const [baseCity, setBaseCity] = useState("Pune");
  const [baseState, setBaseState] = useState("Maharashtra");
  const [svcCategoryId, setSvcCategoryId] = useState("");
  const [svcName, setSvcName] = useState("Wedding Photography Package");
  const [svcPriceInr, setSvcPriceInr] = useState("45000");

  // Quotation builder modal
  const [quoteTarget, setQuoteTarget] = useState<any | null>(null);
  const [quoteTotalInr, setQuoteTotalInr] = useState("50000");
  const [quoteAdvanceInr, setQuoteAdvanceInr] = useState("15000");
  const [quoteScope, setQuoteScope] = useState("");

  // New Draft Project & Media form
  const [newProjTitle, setNewProjTitle] = useState("");
  const [newProjStyle, setNewProjStyle] = useState("Candid");
  const [newProjLocation, setNewProjLocation] = useState("Pune");
  const [uploadProjectId, setUploadProjectId] = useState("");
  const [uploadIsPublic, setUploadIsPublic] = useState(true);
  const [uploadBusy, setUploadBusy] = useState(false);

  // Verification submission
  const [verDocType, setVerDocType] = useState<"government_id" | "business_license" | "gst_certificate" | "equipment_invoice">("government_id");
  const [verNotes, setVerNotes] = useState("");

  const loadAll = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [catRes, profRes] = await Promise.all([api.getCategories(), api.getMyProfile()]);
      const cats = Array.isArray(catRes.data) ? catRes.data : [];
      setCategories(cats);
      if (cats[0]?.id && !svcCategoryId) setSvcCategoryId(cats[0].id);

      const p = profRes.data;
      setProfile(p);
      if (!p) {
        setLoading(false);
        return;
      }

      const [enqRes, quotRes, bkRes, portRes, verRes] = await Promise.all([
        api.getMyEnquiries(),
        api.getMyQuotations(),
        api.getMyBookings(),
        api.getMyPortfolios(),
        api.listMyVerifications(),
      ]);
      setEnquiries(Array.isArray(enqRes.data) ? enqRes.data : []);
      setQuotations(Array.isArray(quotRes.data) ? quotRes.data : []);
      setBookings(Array.isArray(bkRes.data) ? bkRes.data : []);
      const pts = Array.isArray(portRes.data) ? portRes.data : [];
      setPortfolios(pts);
      setVerifications(Array.isArray(verRes.data) ? verRes.data : []);

      const projBatches = await Promise.all(
        pts.map((pt: any) => api.getPortfolioProjects(pt.id).catch(() => ({ data: [] })))
      );
      const flatProjs = projBatches.flatMap((b) => (Array.isArray(b.data) ? b.data : []));
      setProjects(flatProjs);
      if (flatProjs[0]?.id && !uploadProjectId) {
        setUploadProjectId(flatProjs[0].id);
      }
    } catch (err: any) {
      setError(err?.message || "Unable to load studio workspace.");
    } finally {
      setLoading(false);
    }
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!authLoading && user && (user.role === "professional" || user.role === "admin")) {
      loadAll();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, user, loadAll]);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createProfessionalProfile({
        display_name: studioName.trim(),
        headline: headline.trim() || undefined,
        biography: biography.trim() || undefined,
        professional_type: "studio",
        years_experience: 3,
        base_city: baseCity.trim(),
        state: baseState.trim(),
      });
      notify("Studio profile created cleanly as private draft. Add your first service to publish.", "success");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Profile creation failed.", "error");
    }
  };

  const handleAddService = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createMyService({
        category_id: svcCategoryId,
        name: svcName.trim(),
        starting_price_minor: Math.max(0, Number(svcPriceInr || "0") * 100),
      });
      notify("Service saved! Onboarding completed and studio is now discoverable.", "success");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Failed to add service.", "error");
    }
  };

  const handleSendQuotation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quoteTarget) return;
    try {
      await api.createQuotation({
        enquiry_id: quoteTarget.id,
        total_amount_minor: Math.max(100, Number(quoteTotalInr || "0") * 100),
        advance_amount_minor: Math.max(0, Number(quoteAdvanceInr || "0") * 100),
        scope_of_work: quoteScope.trim(),
      });
      notify("Digital quotation sent to customer.", "success");
      setQuoteTarget(null);
      setQuoteScope("");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Failed to send quotation.", "error");
    }
  };

  const handleBookingStart = async (bookingId: string) => {
    try {
      await api.updateBookingStatus(bookingId, { booking_status: "in_progress" });
      notify("Booking transitioned to In Progress.", "success");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Unable to update booking status.", "error");
    }
  };

  const handleCreateDraftProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!portfolios[0] || !categories[0]) return;
    try {
      const res = await api.createProject({
        portfolio_id: portfolios[0].id,
        category_id: categories[0].id,
        title: newProjTitle.trim(),
        style: newProjStyle.trim() || undefined,
        location: newProjLocation.trim() || undefined,
        publication_status: "draft",
      });
      notify("Draft project created! Upload a public photo before publishing.", "success");
      setNewProjTitle("");
      setUploadProjectId(res.data.id);
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Failed to create project.", "error");
    }
  };

  const handleMediaFileUpload = async (file: File | null, targetProjectId: string) => {
    if (!file || !targetProjectId) return;
    setUploadBusy(true);
    try {
      const upRes = await api.getUploadUrl({
        filename: file.name,
        mime_type: file.type || "image/jpeg",
        file_size_bytes: file.size,
        is_public: uploadIsPublic,
      });
      await uploadFileToPresignedUrl(upRes.data.upload_url, file);
      const checksum = await computeFileSha256(file);
      await api.completeMediaUpload({
        project_id: targetProjectId,
        storage_key: upRes.data.storage_key,
        visibility: uploadIsPublic ? "public" : "private",
        mime_type: file.type || "image/jpeg",
        file_size_bytes: file.size,
        checksum,
      });
      notify(
        uploadIsPublic
          ? "Public asset uploaded & queued for sanitization."
          : "Private proof asset stored securely in private bucket.",
        "success"
      );
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Media upload failed.", "error");
    } finally {
      setUploadBusy(false);
    }
  };

  const handlePublishToggle = async (project: any) => {
    const nextStatus = project.publication_status === "published" ? "draft" : "published";
    try {
      await api.updateProject(project.id, { publication_status: nextStatus });
      notify(`Project status set to '${nextStatus}'.`, "success");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Cannot update project status.", "error");
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    try {
      await api.deleteMediaAsset(assetId);
      notify("Media asset deleted.", "info");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Failed to delete asset.", "error");
    }
  };

  const handlePreviewPrivateAsset = async (assetId: string) => {
    try {
      const res = await api.getMediaAccessUrl(assetId);
      if (res.data?.url) {
        window.open(res.data.url, "_blank", "noopener,noreferrer");
      }
    } catch (err: any) {
      notify(err?.message || "Could not fetch signed asset URL.", "error");
    }
  };

  const handleVerificationUpload = async (file: File | null) => {
    if (!file) return;
    setUploadBusy(true);
    try {
      const upRes = await api.getUploadUrl({
        filename: file.name,
        mime_type: file.type || "image/jpeg",
        file_size_bytes: file.size,
        is_public: false,
      });
      await uploadFileToPresignedUrl(upRes.data.upload_url, file);
      await api.submitVerification({
        document_type: verDocType,
        document_storage_key: upRes.data.storage_key,
        notes: verNotes.trim() || undefined,
      });
      notify("Verification document submitted securely to admin queue.", "success");
      setVerNotes("");
      await loadAll();
    } catch (err: any) {
      notify(err?.message || "Verification submission failed.", "error");
    } finally {
      setUploadBusy(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading studio workspace...
      </div>
    );
  }

  if (!user || (user.role !== "professional" && user.role !== "admin")) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center space-y-4">
        <h1 className="text-2xl font-extrabold text-white">Professional Studio Workspace</h1>
        <p className="text-xs text-gray-400">
          Sign in with a professional account to manage onboarding, portfolios, quotations, and bookings.
        </p>
        <Link href="/login?next=/professional/dashboard" className="inline-block px-5 py-2.5 rounded-xl bg-[#FF5E1E] text-white text-xs font-semibold">
          Sign In as Professional
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!profile ? (
        <form onSubmit={handleCreateProfile} className="max-w-xl mx-auto p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4 text-xs">
          <h1 className="text-xl font-extrabold text-white">Create Your Studio Profile</h1>
          <p className="text-gray-400">
            Profiles begin in <code className="text-amber-300">private</code> onboarding mode until you add at least one active service.
          </p>
          <input
            type="text"
            required
            placeholder="Studio / Brand Name"
            value={studioName}
            onChange={(e) => setStudioName(e.target.value)}
            className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
          />
          <input
            type="text"
            placeholder="Short Headline (e.g. Candid Wedding & Film Studio)"
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
          />
          <textarea
            rows={3}
            placeholder="Studio biography..."
            value={biography}
            onChange={(e) => setBiography(e.target.value)}
            className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              required
              placeholder="Base City"
              value={baseCity}
              onChange={(e) => setBaseCity(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
            />
            <input
              type="text"
              required
              placeholder="State"
              value={baseState}
              onChange={(e) => setBaseState(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
            />
          </div>
          <button type="submit" className="w-full py-2.5 rounded-xl bg-[#FF5E1E] text-white font-semibold">
            Create Studio Profile
          </button>
        </form>
      ) : (
        <>
          {/* Live Studio Header */}
          <div className="p-8 rounded-3xl bg-gradient-to-r from-[#171822] via-[#1a1c28] to-[#171822] border border-white/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-extrabold text-white">{profile.display_name}</h1>
                <span className="px-2.5 py-0.5 rounded-full bg-white/10 text-gray-200 text-[11px] font-semibold capitalize">
                  Visibility: {profile.profile_visibility}
                </span>
                {profile.verification_status === "verified" && (
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold flex items-center gap-1 border border-emerald-500/20">
                    <ShieldCheck className="w-3.5 h-3.5" /> Verified Studio
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400">
                {profile.base_city}, {profile.state} • {profile.years_experience} Years Experience • Slug:{" "}
                <Link href={`/professionals/${encodeURIComponent(profile.slug)}`} className="text-[#FF5E1E] hover:underline">
                  /professionals/{profile.slug}
                </Link>
              </p>
            </div>
          </div>

          {/* Onboarding Service Gate */}
          {!profile.onboarding_completed && (
            <form onSubmit={handleAddService} className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-4 text-xs">
              <div className="font-bold text-amber-200 text-sm">
                Complete Onboarding: Add Your First Active Service to Unlock Public Discovery
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <select
                  value={svcCategoryId}
                  onChange={(e) => setSvcCategoryId(e.target.value)}
                  className="bg-[#1b1c23] border border-white/15 rounded-lg px-3 py-2 text-white"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <input
                  type="text"
                  required
                  value={svcName}
                  onChange={(e) => setSvcName(e.target.value)}
                  placeholder="Service Package Name"
                  className="bg-[#1b1c23] border border-white/15 rounded-lg px-3 py-2 text-white"
                />
                <input
                  type="number"
                  required
                  min={0}
                  value={svcPriceInr}
                  onChange={(e) => setSvcPriceInr(e.target.value)}
                  placeholder="Starting Price (INR)"
                  className="bg-[#1b1c23] border border-white/15 rounded-lg px-3 py-2 text-white"
                />
                <button type="submit" className="px-4 py-2 rounded-lg bg-[#FF5E1E] text-white font-semibold">
                  Publish First Service
                </button>
              </div>
            </form>
          )}

          {/* Computed Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-[#14151b] border border-white/10">
              <span className="text-xs text-gray-400">Client Enquiries</span>
              <div className="text-2xl font-extrabold text-white mt-1">{enquiries.length}</div>
            </div>
            <div className="p-5 rounded-2xl bg-[#14151b] border border-white/10">
              <span className="text-xs text-gray-400">Sent Quotations</span>
              <div className="text-2xl font-extrabold text-white mt-1">{quotations.length}</div>
            </div>
            <div className="p-5 rounded-2xl bg-[#14151b] border border-white/10">
              <span className="text-xs text-gray-400">Active / Total Bookings</span>
              <div className="text-2xl font-extrabold text-white mt-1">{bookings.length}</div>
            </div>
            <div className="p-5 rounded-2xl bg-[#14151b] border border-white/10">
              <span className="text-xs text-gray-400">Verified Rating</span>
              <div className="text-2xl font-extrabold text-white mt-1">
                {Number(profile.avg_rating || 0).toFixed(1)}{" "}
                <span className="text-xs text-gray-400 font-normal">({profile.total_reviews})</span>
              </div>
            </div>
          </div>

          {/* Workspace Tabs */}
          <div className="flex flex-wrap gap-4 border-b border-white/10 text-xs font-semibold">
            {(["leads", "bookings", "portfolio", "verification"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`pb-3 px-2 border-b-2 capitalize transition-colors ${
                  activeTab === tab
                    ? "border-[#FF5E1E] text-white"
                    : "border-transparent text-gray-400 hover:text-white"
                }`}
              >
                {tab === "leads"
                  ? `Leads & Quotations (${enquiries.length})`
                  : tab === "bookings"
                    ? `Bookings (${bookings.length})`
                    : tab === "portfolio"
                      ? `Portfolio & Drafts (${projects.length})`
                      : `KYC Verification (${verifications.length})`}
              </button>
            ))}
          </div>

          {/* Tab: Leads & Quotations */}
          {activeTab === "leads" && (
            <div className="space-y-4">
              {enquiries.length === 0 ? (
                <div className="p-8 rounded-2xl bg-[#14151b] border border-white/10 text-xs text-gray-400">
                  No incoming client enquiries assigned yet.
                </div>
              ) : (
                enquiries.map((enq) => (
                  <div
                    key={enq.id}
                    className="p-5 rounded-2xl bg-[#14151b] border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-bold text-white text-sm">
                        {enq.title} — {enq.customer_name || "Client"}
                      </div>
                      <p className="text-gray-400">
                        {enq.category_name || "Photography"} • {enq.city} ({enq.location}) •{" "}
                        {enq.shoot_date || "Flexible"}
                      </p>
                      <p className="text-gray-300">{enq.description}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setQuoteTarget(enq);
                        setQuoteScope(`Coverage for ${enq.title}`);
                      }}
                      className="px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold flex items-center gap-1.5 shrink-0"
                    >
                      <Send className="w-3.5 h-3.5" /> Send Quotation
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab: Bookings */}
          {activeTab === "bookings" && (
            <div className="space-y-4">
              {bookings.length === 0 ? (
                <div className="p-8 rounded-2xl bg-[#14151b] border border-white/10 text-xs text-gray-400">
                  No bookings confirmed yet.
                </div>
              ) : (
                bookings.map((bk) => (
                  <div
                    key={bk.id}
                    className="p-5 rounded-2xl bg-[#14151b] border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-bold text-white text-sm">
                        Client: {bk.customer_name || bk.customer_id.slice(0, 8)} •{" "}
                        <span className="text-[#FF5E1E] uppercase text-[11px]">{bk.booking_status}</span>
                      </div>
                      <p className="text-gray-400">
                        {bk.shoot_date} • {bk.location} • Agreed ₹{Math.round(bk.agreed_amount_minor / 100).toLocaleString("en-IN")} • Paid ₹{Math.round(bk.paid_amount_minor / 100).toLocaleString("en-IN")}
                      </p>
                    </div>
                    {bk.booking_status === "confirmed" && (
                      <button
                        type="button"
                        onClick={() => handleBookingStart(bk.id)}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Start Shoot (In Progress)
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab: Portfolio & Draft/Publish Manager */}
          {activeTab === "portfolio" && (
            <div className="space-y-6 text-xs">
              <form onSubmit={handleCreateDraftProject} className="p-5 rounded-2xl bg-[#14151b] border border-white/10 grid grid-cols-1 md:grid-cols-4 gap-3">
                <input
                  type="text"
                  required
                  placeholder="New Project Title (starts as draft)"
                  value={newProjTitle}
                  onChange={(e) => setNewProjTitle(e.target.value)}
                  className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                />
                <input
                  type="text"
                  placeholder="Style (e.g. Candid)"
                  value={newProjStyle}
                  onChange={(e) => setNewProjStyle(e.target.value)}
                  className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                />
                <input
                  type="text"
                  placeholder="Location"
                  value={newProjLocation}
                  onChange={(e) => setNewProjLocation(e.target.value)}
                  className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                />
                <button type="submit" className="px-4 py-2 rounded-lg bg-[#FF5E1E] text-white font-semibold flex items-center justify-center gap-1.5">
                  <Plus className="w-3.5 h-3.5" /> Create Draft Project
                </button>
              </form>

              <div className="p-5 rounded-2xl bg-[#14151b] border border-white/10 flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-3">
                  <select
                    value={uploadProjectId}
                    onChange={(e) => setUploadProjectId(e.target.value)}
                    className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="">Select Target Project</option>
                    {projects.map((pr) => (
                      <option key={pr.id} value={pr.id}>
                        {pr.title} ({pr.publication_status})
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-2 text-gray-300">
                    <input
                      type="checkbox"
                      checked={uploadIsPublic}
                      onChange={(e) => setUploadIsPublic(e.target.checked)}
                    />
                    Public Portfolio Asset (uncheck for private client proof)
                  </label>
                </div>
                <label className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white font-semibold cursor-pointer flex items-center gap-1.5">
                  <Upload className="w-3.5 h-3.5 text-[#FF5E1E]" />
                  <span>{uploadBusy ? "Uploading..." : "Upload Image"}</span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    disabled={uploadBusy || !uploadProjectId}
                    onChange={(e) => handleMediaFileUpload(e.target.files?.[0] || null, uploadProjectId)}
                  />
                </label>
              </div>

              <div className="space-y-4">
                {projects.map((pr) => (
                  <div key={pr.id} className="p-5 rounded-2xl bg-[#14151b] border border-white/10 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-bold text-white text-sm">{pr.title}</div>
                        <span className="text-[11px] text-gray-400">
                          Status: <strong className="text-[#FF5E1E]">{pr.publication_status}</strong> •{" "}
                          {pr.media_assets?.length || 0} assets
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handlePublishToggle(pr)}
                        className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-semibold"
                      >
                        {pr.publication_status === "published" ? "Unpublish to Draft" : "Publish Project"}
                      </button>
                    </div>
                    {pr.media_assets?.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {pr.media_assets.map((asset: any) => (
                          <div key={asset.id} className="p-3 rounded-xl bg-[#1a1b24] border border-white/5 flex items-center justify-between gap-2">
                            <span className="truncate text-gray-300">
                              [{asset.visibility}] {asset.mime_type}
                            </span>
                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                type="button"
                                onClick={() => handlePreviewPrivateAsset(asset.id)}
                                title="Open authorized preview URL"
                                className="text-gray-300 hover:text-white"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteAsset(asset.id)}
                                title="Delete asset"
                                className="text-red-400 hover:text-red-300"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab: KYC Verification */}
          {activeTab === "verification" && (
            <div className="space-y-4 text-xs">
              <div className="p-5 rounded-2xl bg-[#14151b] border border-white/10 space-y-3">
                <h2 className="font-bold text-white text-sm flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-400" /> Submit Verification Document (Private S3)
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <select
                    value={verDocType}
                    onChange={(e) => setVerDocType(e.target.value as any)}
                    className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="government_id">Government ID (Aadhaar / PAN)</option>
                    <option value="business_license">Business License</option>
                    <option value="gst_certificate">GST Certificate</option>
                    <option value="equipment_invoice">Equipment Invoice</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Verification notes / GSTIN"
                    value={verNotes}
                    onChange={(e) => setVerNotes(e.target.value)}
                    className="bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                  />
                  <label className="px-4 py-2 rounded-lg bg-[#FF5E1E] text-white font-semibold text-center cursor-pointer">
                    {uploadBusy ? "Uploading..." : "Upload Document & Submit"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      disabled={uploadBusy}
                      onChange={(e) => handleVerificationUpload(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
              </div>

              {verifications.map((v) => (
                <div key={v.id} className="p-4 rounded-xl bg-[#14151b] border border-white/10 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white capitalize">{v.document_type.replaceAll("_", " ")}</div>
                    <span className="text-gray-400">Submitted: {new Date(v.created_at).toLocaleString()}</span>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-white/10 text-white uppercase text-[10px]">{v.status}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Quotation Builder Modal */}
      {quoteTarget && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleSendQuotation} className="w-full max-w-md p-6 rounded-2xl bg-[#14151b] border border-white/15 space-y-4 text-xs">
            <h2 className="text-lg font-bold text-white">Send Digital Quotation</h2>
            <p className="text-gray-400">Enquiry: {quoteTarget.title}</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-gray-300 block mb-1">Total Amount (INR)</label>
                <input
                  type="number"
                  required
                  min={1}
                  value={quoteTotalInr}
                  onChange={(e) => setQuoteTotalInr(e.target.value)}
                  className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="font-semibold text-gray-300 block mb-1">Advance Deposit (INR)</label>
                <input
                  type="number"
                  required
                  min={0}
                  value={quoteAdvanceInr}
                  onChange={(e) => setQuoteAdvanceInr(e.target.value)}
                  className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
                />
              </div>
            </div>
            <div>
              <label className="font-semibold text-gray-300 block mb-1">Scope of Work & Deliverables</label>
              <textarea
                required
                rows={4}
                value={quoteScope}
                onChange={(e) => setQuoteScope(e.target.value)}
                className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setQuoteTarget(null)} className="px-3 py-1.5 rounded-lg bg-white/10 text-white">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 rounded-lg bg-[#FF5E1E] text-white font-semibold">
                Send Quotation
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
