"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  SlidersHorizontal,
  MapPin,
  ShieldCheck,
  Star,
  Check,
  ArrowRight,
  Sparkles,
  Camera,
  Filter,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { ApiClientError, api } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

interface CategoryOption {
  id: string;
  name: string;
  slug: string;
}

interface ProCard {
  id: string;
  name: string;
  slug: string;
  headline: string;
  city: string;
  state: string;
  rating: number;
  reviews: number;
  starting_price: number;
  verified: boolean;
  experience: number;
  styles: string[];
  image: string | null;
  match_score?: number;
  match_explanation?: string;
}

function SearchContent() {
  const searchParams = useSearchParams();
  const { notify } = useToast();

  const [city, setCity] = useState(searchParams.get("city") || "All");
  const [category, setCategory] = useState(searchParams.get("category") || "all");
  const [verifiedOnly, setVerifiedOnly] = useState(searchParams.get("verified_only") === "true");
  const [aiMode, setAiMode] = useState(searchParams.get("ai") === "true");
  const [aiQuery, setAiQuery] = useState(searchParams.get("query") || "");
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [shortlist, setShortlist] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiAuthRequired, setAiAuthRequired] = useState(false);
  const [professionals, setProfessionals] = useState<ProCard[]>([]);
  const [totalResults, setTotalResults] = useState(0);

  useEffect(() => {
    api
      .getCategories()
      .then((res) => setCategories(Array.isArray(res.data) ? res.data : []))
      .catch(() => setCategories([]));
  }, []);

  const fetchProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    setAiAuthRequired(false);
    try {
      const params: {
        category_slug?: string;
        city?: string;
        verified_only?: boolean;
        limit?: number;
      } = { limit: 20 };
      if (city !== "All") params.city = city;
      if (category !== "all") params.category_slug = category;
      if (verifiedOnly) params.verified_only = true;

      const res = await api.searchProfessionals(params);
      const rows = Array.isArray(res.data?.results) ? res.data.results : [];
      setTotalResults(Number(res.data?.total_results ?? rows.length));
      setProfessionals(
        rows.map((p: any) => ({
          id: p.id,
          name: p.display_name,
          slug: p.slug,
          headline: p.headline || "Photography & Videography Studio",
          city: p.base_city,
          state: p.state || "",
          rating: Number(p.avg_rating || 0),
          reviews: Number(p.total_reviews || 0),
          starting_price: Math.round((p.starting_price_minor || 0) / 100),
          verified: p.verification_status === "verified",
          experience: Number(p.years_experience || 0),
          styles: [p.verification_status === "verified" ? "Verified" : "Onboarded"],
          image: p.cover_image || p.profile_image || null,
          match_score: p.match_score,
          match_explanation: p.match_explanation,
        }))
      );
    } catch (err: any) {
      setProfessionals([]);
      setTotalResults(0);
      setError(err?.message || "Failed to load professionals from API.");
    } finally {
      setLoading(false);
    }
  }, [city, category, verifiedOnly]);

  const runAiSearch = useCallback(async (queryText: string) => {
    if (!queryText.trim()) {
      setProfessionals([]);
      setTotalResults(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setAiAuthRequired(false);
    try {
      const res = await api.aiSearch(queryText.trim());
      const recs = Array.isArray(res.data?.recommendations) ? res.data.recommendations : [];
      setTotalResults(recs.length);
      setProfessionals(
        recs.map((r: any) => ({
          id: r.professional_id,
          name: r.display_name,
          slug: r.slug,
          headline: r.headline || "AI Matched Studio",
          city: r.base_city,
          state: r.state || "",
          rating: Number(r.avg_rating || 0),
          reviews: Number(r.total_reviews || 0),
          starting_price: Math.round((r.starting_price_minor || 0) / 100),
          verified: r.verification_status === "verified",
          experience: Number(r.years_experience || 0),
          styles: r.relevant_projects || ["AI Matched"],
          image: r.profile_image || null,
          match_score: r.relevance_score ? Math.round(Number(r.relevance_score) * 100) : undefined,
          match_explanation: r.match_explanation,
        }))
      );
    } catch (err: any) {
      setProfessionals([]);
      setTotalResults(0);
      if (err instanceof ApiClientError && err.status === 401) {
        setAiAuthRequired(true);
      } else {
        setError(err?.message || "AI Search request failed.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!aiMode) {
      fetchProfiles();
    } else if (aiQuery.trim()) {
      runAiSearch(aiQuery);
    } else {
      setLoading(false);
    }
  }, [aiMode, fetchProfiles]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleShortlist = (id: string) => {
    if (shortlist.includes(id)) {
      setShortlist(shortlist.filter((x) => x !== id));
    } else {
      if (shortlist.length >= 4) {
        notify("You can compare up to 4 professionals at a time.", "info");
        return;
      }
      setShortlist([...shortlist, id]);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Top Header & AI Toggle */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Find Creative Professionals</h1>
          <p className="text-xs text-gray-400 mt-1">
            Live database directory with real portfolios, verified bookings, and direct quotations.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setAiMode((prev) => !prev)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
            aiMode
              ? "bg-[#FF5E1E] border-[#FF5E1E] text-white shadow-lg shadow-[#FF5E1E]/25"
              : "bg-white/5 border-white/15 text-gray-300 hover:text-white"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>{aiMode ? "AI Match Mode Active" : "Enable AI Requirement Match"}</span>
        </button>
      </div>

      {/* AI Search Box */}
      {aiMode && (
        <div className="p-6 rounded-2xl bg-gradient-to-r from-[#1b1c24] to-[#14151c] border border-[#FF5E1E]/30 space-y-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#FF5E1E]">
            <Sparkles className="w-4 h-4" />
            <span>AI Natural Language Parser (Ollama / Evidence-Grounded Ranking)</span>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              placeholder="e.g. 'Candid wedding photographer in Pune under Rs 60,000'"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[#FF5E1E]"
            />
            <button
              type="button"
              onClick={() => runAiSearch(aiQuery)}
              disabled={loading || !aiQuery.trim()}
              className="px-5 py-2.5 rounded-xl bg-[#FF5E1E] disabled:opacity-50 text-white text-xs font-semibold hover:bg-[#E04E15] transition-colors flex items-center justify-center gap-1.5"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              <span>{loading ? "Analyzing..." : "Analyze & Rank"}</span>
            </button>
          </div>
          {aiAuthRequired && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <span>Sign in to run personalized AI recommendations, or switch off AI mode to filter the public directory.</span>
              <div className="flex gap-2">
                <Link
                  href="/login?next=/search?ai=true"
                  className="px-3.5 py-1.5 rounded-lg bg-[#FF5E1E] text-white font-semibold"
                >
                  Sign In
                </Link>
                <button
                  type="button"
                  onClick={() => setAiMode(false)}
                  className="px-3.5 py-1.5 rounded-lg bg-white/10 text-white"
                >
                  Use Filter Search
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filter Toolbar & Results */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="space-y-6 bg-[#131418] p-5 rounded-2xl border border-white/10 h-fit">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-3 border-b border-white/10">
            <Filter className="w-4 h-4 text-[#FF5E1E]" />
            <span>Search Filters</span>
          </div>

          <div className="space-y-2">
            <label htmlFor="search-city" className="text-xs font-semibold text-gray-300">City / Location</label>
            <select
              id="search-city"
              value={city}
              onChange={(e) => {
                setAiMode(false);
                setCity(e.target.value);
              }}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="All">All Cities</option>
              <option value="Pune">Pune</option>
              <option value="Mumbai">Mumbai</option>
              <option value="Delhi">Delhi</option>
              <option value="Bengaluru">Bengaluru</option>
              <option value="Jaipur">Jaipur</option>
            </select>
          </div>

          <div className="space-y-2">
            <label htmlFor="search-category" className="text-xs font-semibold text-gray-300">Service Category</label>
            <select
              id="search-category"
              value={category}
              onChange={(e) => {
                setAiMode(false);
                setCategory(e.target.value);
              }}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="all">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.slug}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-2.5 text-xs text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={verifiedOnly}
                onChange={(e) => {
                  setAiMode(false);
                  setVerifiedOnly(e.target.checked);
                }}
                className="rounded border-white/20 text-[#FF5E1E] focus:ring-0"
              />
              <span className="font-medium">Verified Professionals Only</span>
            </label>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>
              {loading ? "Searching..." : (
                <>
                  Showing <strong className="text-white">{professionals.length}</strong> of{" "}
                  <strong className="text-white">{totalResults}</strong> matching professionals
                </>
              )}
            </span>
            <span>Sorted by: <strong>Relevance & Verified Rating</strong></span>
          </div>

          {error && (
            <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-center justify-between gap-4">
              <span className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </span>
              <button
                type="button"
                onClick={() => (aiMode ? runAiSearch(aiQuery) : fetchProfiles())}
                className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-semibold flex items-center gap-1"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry
              </button>
            </div>
          )}

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((idx) => (
                <div key={idx} className="h-44 rounded-2xl bg-[#14151b] border border-white/10 animate-pulse" />
              ))}
            </div>
          ) : professionals.length === 0 ? (
            <div className="p-10 rounded-2xl bg-[#14151b] border border-white/10 text-center space-y-3">
              <Camera className="w-8 h-8 text-gray-500 mx-auto" />
              <h2 className="text-base font-bold text-white">No matching professionals found</h2>
              <p className="text-xs text-gray-400 max-w-md mx-auto">
                Try clearing city or category filters to explore all onboarded studios across MaanCamera.
              </p>
              <button
                type="button"
                onClick={() => {
                  setCity("All");
                  setCategory("all");
                  setVerifiedOnly(false);
                  setAiMode(false);
                }}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-xs font-semibold text-white"
              >
                Reset All Filters
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {professionals.map((pro) => {
                const isShortlisted = shortlist.includes(pro.id);
                return (
                  <div
                    key={pro.id}
                    className="p-5 rounded-2xl bg-[#14151b] border border-white/10 hover:border-white/20 transition-all flex flex-col md:flex-row gap-5"
                  >
                    <div className="w-full md:w-56 h-44 rounded-xl overflow-hidden shrink-0 bg-gradient-to-br from-[#1b1c26] to-[#111218] relative flex items-center justify-center">
                      {pro.image ? (
                        <img src={pro.image} alt={pro.name} className="w-full h-full object-cover" />
                      ) : (
                        <Camera className="w-10 h-10 text-white/20" />
                      )}
                      {pro.verified && (
                        <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/70 backdrop-blur-md text-[10px] font-semibold text-emerald-400 flex items-center gap-1 border border-emerald-500/20">
                          <ShieldCheck className="w-3 h-3" /> Verified
                        </div>
                      )}
                    </div>

                    <div className="flex-1 flex flex-col justify-between space-y-3">
                      <div>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <Link
                              href={`/professionals/${encodeURIComponent(pro.slug)}`}
                              className="text-lg font-bold text-white hover:text-[#FF5E1E] transition-colors"
                            >
                              {pro.name}
                            </Link>
                            <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{pro.headline}</p>
                          </div>
                          <div className="flex items-center gap-1 text-xs font-semibold text-white bg-white/5 px-2.5 py-1 rounded-lg shrink-0">
                            <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                            <span>{pro.rating.toFixed(1)}</span>
                            <span className="text-gray-500">({pro.reviews})</span>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400 mt-2">
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5 text-gray-500" />
                            {pro.city}{pro.state ? `, ${pro.state}` : ""}
                          </span>
                          <span>•</span>
                          <span>{pro.experience} Years Experience</span>
                          <span>•</span>
                          <span>
                            {pro.starting_price > 0
                              ? `Starting ₹${pro.starting_price.toLocaleString("en-IN")}`
                              : "Custom Quote"}
                          </span>
                        </div>

                        {pro.match_explanation && (
                          <p className="mt-2 text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-2.5 py-1.5">
                            {pro.match_score !== undefined ? `${pro.match_score}% Match — ` : ""}
                            {pro.match_explanation}
                          </p>
                        )}
                      </div>

                      <div className="pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-3">
                        <button
                          type="button"
                          onClick={() => toggleShortlist(pro.id)}
                          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors ${
                            isShortlisted
                              ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                              : "bg-white/5 border-white/10 text-gray-300 hover:text-white"
                          }`}
                        >
                          {isShortlisted ? <Check className="w-3.5 h-3.5" /> : <SlidersHorizontal className="w-3.5 h-3.5" />}
                          <span>{isShortlisted ? "Shortlisted for Compare" : "Add to Compare"}</span>
                        </button>

                        <div className="flex gap-2">
                          <Link
                            href={`/professionals/${encodeURIComponent(pro.slug)}?enquire=1`}
                            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
                          >
                            Send Enquiry
                          </Link>
                          <Link
                            href={`/professionals/${encodeURIComponent(pro.slug)}`}
                            className="px-4 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-md transition-colors"
                          >
                            View Portfolio
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Floating Comparison Bar */}
      {shortlist.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-[#171822] border border-white/20 shadow-2xl rounded-2xl px-6 py-4 flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs font-semibold text-white">
            <SlidersHorizontal className="w-4 h-4 text-[#FF5E1E]" />
            <span>{shortlist.length} of 4 Selected</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShortlist([])}
              className="text-xs text-gray-400 hover:text-white underline"
            >
              Clear
            </button>
            {shortlist.length >= 2 ? (
              <Link
                href={`/compare?ids=${encodeURIComponent(shortlist.join(","))}`}
                className="px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-lg transition-colors flex items-center gap-1.5"
              >
                <span>Compare Profiles</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ) : (
              <span className="text-[11px] text-amber-300">Select at least 2 to compare</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading directory...
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
