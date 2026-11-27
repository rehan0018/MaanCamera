"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  Sparkles,
  MapPin,
  ShieldCheck,
  Star,
  CheckCircle2,
  SlidersHorizontal,
  ArrowRight,
  Camera,
  Award,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";

interface CategoryItem {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
}

interface SearchProItem {
  id: string;
  display_name: string;
  slug: string;
  headline?: string | null;
  profile_image?: string | null;
  cover_image?: string | null;
  base_city: string;
  state: string;
  years_experience: number;
  avg_rating: number;
  total_reviews: number;
  starting_price_minor?: number | null;
  verification_status: string;
}

export default function HomePage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCity, setSelectedCity] = useState("Pune");
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [featuredPros, setFeaturedPros] = useState<SearchProItem[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadHomepageData = async () => {
    setLoadingData(true);
    setLoadError(null);
    try {
      const [catRes, proRes] = await Promise.all([
        api.getCategories(),
        api.searchProfessionals({ verified_only: true, limit: 6 }),
      ]);
      setCategories(Array.isArray(catRes.data) ? catRes.data : []);
      const results = Array.isArray(proRes.data?.results) ? proRes.data.results : [];
      if (results.length > 0) {
        setFeaturedPros(results);
      } else {
        const allRes = await api.searchProfessionals({ limit: 6 });
        setFeaturedPros(Array.isArray(allRes.data?.results) ? allRes.data.results : []);
      }
    } catch (err: any) {
      setLoadError(err?.message || "Unable to reach marketplace backend right now.");
      setCategories([]);
      setFeaturedPros([]);
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    loadHomepageData();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      router.push(`/search?city=${encodeURIComponent(selectedCity)}`);
    } else {
      router.push(`/search?ai=true&query=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div className="space-y-20 pb-20">
      {/* Hero Section */}
      <section className="relative pt-16 pb-24 overflow-hidden border-b border-white/5 bg-gradient-to-b from-[#131418] via-[#0e0f13] to-[#0d0e12]">
        <div className="absolute inset-0 bg-[radial-gradient(#FF5E1E_1px,transparent_1px)] [background-size:24px_24px] opacity-10" />

        <div className="max-w-5xl mx-auto px-4 text-center relative z-10 space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-[#FF5E1E]">
            <Sparkles className="w-3.5 h-3.5" />
            <span>India&apos;s AI-Powered Creative Marketplace</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Discover. Compare. <br className="hidden sm:inline" />
            Connect.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF5E1E] to-[#FFA07A]">
              Capture.
            </span>
          </h1>

          <p className="max-w-2xl mx-auto text-base sm:text-lg text-gray-400">
            Find photography and videography studios across India with transparent quotations,
            verified portfolios, and structured bookings.
          </p>

          <form
            onSubmit={handleSearch}
            className="max-w-3xl mx-auto mt-8 p-2 rounded-2xl bg-[#1a1b22] border border-white/15 shadow-2xl flex flex-col sm:flex-row gap-2"
          >
            <div className="flex-1 flex items-center px-4 py-2 gap-2 text-sm text-gray-300">
              <Sparkles className="w-4 h-4 text-[#FF5E1E] shrink-0" />
              <input
                type="text"
                aria-label="Describe your shoot requirements"
                placeholder="Ask AI or leave blank to browse city: e.g. 'Candid wedding photographer in Pune'..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent placeholder-gray-500 focus:outline-none text-white text-sm"
              />
            </div>

            <div className="flex items-center gap-2 px-3 py-2 border-t sm:border-t-0 sm:border-l border-white/10 text-sm">
              <MapPin className="w-4 h-4 text-gray-400 shrink-0" />
              <select
                aria-label="Select city"
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="bg-transparent text-gray-300 focus:outline-none text-xs sm:text-sm font-medium"
              >
                <option value="Pune" className="bg-[#1a1b22]">Pune</option>
                <option value="Mumbai" className="bg-[#1a1b22]">Mumbai</option>
                <option value="Delhi" className="bg-[#1a1b22]">Delhi</option>
                <option value="Bengaluru" className="bg-[#1a1b22]">Bengaluru</option>
                <option value="Jaipur" className="bg-[#1a1b22]">Jaipur</option>
              </select>
            </div>

            <button
              type="submit"
              className="px-6 py-3 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-[#FF5E1E]/25 transition-all"
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </button>
          </form>

          <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-gray-400 pt-2">
            <span className="text-gray-500">Quick prompts:</span>
            {[
              "Candid wedding photographer in Pune under 50k",
              "Cinematic drone videographer Mumbai",
              "Pre-wedding shoot in Delhi",
            ].map((sample) => (
              <button
                key={sample}
                type="button"
                onClick={() => setSearchQuery(sample)}
                className="px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
              >
                {sample}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Categories Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Explore by Category</h2>
            <p className="text-xs text-gray-400 mt-1">Live marketplace specialties seeded in PostgreSQL</p>
          </div>
          <Link href="/search" className="text-xs font-semibold text-[#FF5E1E] hover:underline flex items-center gap-1">
            Browse Directory <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loadingData ? (
          <div className="flex items-center gap-2 text-xs text-gray-400 py-8">
            <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading categories...
          </div>
        ) : loadError ? (
          <div className="p-5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-center justify-between gap-4">
            <span className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {loadError}
            </span>
            <button
              type="button"
              onClick={loadHomepageData}
              className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-semibold flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        ) : categories.length === 0 ? (
          <div className="p-6 rounded-xl bg-[#14151b] border border-white/10 text-xs text-gray-400">
            No active service categories configured yet.
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {categories.map((cat) => (
              <Link
                key={cat.id}
                href={`/search?category=${encodeURIComponent(cat.slug)}`}
                className="group p-5 rounded-xl bg-[#14151b] border border-white/5 hover:border-[#FF5E1E]/40 hover:bg-[#1a1c24] transition-all flex flex-col justify-between"
              >
                <div className="w-10 h-10 rounded-lg bg-white/5 group-hover:bg-[#FF5E1E]/10 flex items-center justify-center text-gray-300 group-hover:text-[#FF5E1E] transition-colors mb-4">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-white text-sm group-hover:text-[#FF5E1E] transition-colors">
                    {cat.name}
                  </h3>
                  <span className="text-xs text-gray-500 line-clamp-1">
                    {cat.description || cat.slug}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Live Featured Professionals */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Verified Professionals</h2>
            <p className="text-xs text-gray-400 mt-1">
              Onboarded public studios active on MaanCamera
            </p>
          </div>
          <Link href="/search?verified_only=true" className="text-xs font-semibold text-[#FF5E1E] hover:underline flex items-center gap-1">
            See All Verified <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loadingData ? (
          <div className="flex items-center gap-2 text-xs text-gray-400 py-8">
            <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading verified studios...
          </div>
        ) : featuredPros.length === 0 ? (
          <div className="p-8 rounded-2xl bg-[#14151b] border border-white/10 text-center space-y-2">
            <p className="text-sm font-semibold text-white">No public professionals listed yet</p>
            <p className="text-xs text-gray-400">
              Professionals appear here once they finish onboarding with at least one active service.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {featuredPros.map((pro) => {
              const imgUrl = pro.cover_image || pro.profile_image;
              const startPrice = Math.round((pro.starting_price_minor || 0) / 100);
              return (
                <div
                  key={pro.id}
                  className="rounded-2xl bg-[#14151b] border border-white/10 overflow-hidden hover:border-white/20 transition-all flex flex-col group"
                >
                  <div className="relative h-48 w-full overflow-hidden bg-gradient-to-br from-[#1b1c26] to-[#111218] flex items-center justify-center">
                    {imgUrl ? (
                      <img
                        src={imgUrl}
                        alt={pro.display_name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    ) : (
                      <Camera className="w-10 h-10 text-white/20" />
                    )}
                    {pro.verification_status === "verified" && (
                      <div className="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-md text-[11px] font-semibold text-emerald-400 flex items-center gap-1 border border-emerald-500/20">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Verified Studio
                      </div>
                    )}
                    <div className="absolute top-3 right-3 px-2 py-1 rounded-md bg-black/70 backdrop-blur-md text-[11px] font-semibold text-white flex items-center gap-1">
                      <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                      {pro.avg_rating.toFixed(1)} ({pro.total_reviews})
                    </div>
                  </div>

                  <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="font-bold text-white text-base group-hover:text-[#FF5E1E] transition-colors truncate">
                          {pro.display_name}
                        </h3>
                        <span className="text-xs text-gray-400 shrink-0">{pro.years_experience} yrs</span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
                        <MapPin className="w-3.5 h-3.5 text-gray-500" />
                        <span>{pro.base_city}, {pro.state}</span>
                      </div>
                      {pro.headline && (
                        <p className="mt-2 text-xs text-gray-300 line-clamp-2">{pro.headline}</p>
                      )}
                    </div>

                    <div className="pt-3 border-t border-white/5 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] uppercase tracking-wider text-gray-500 block">
                          Starting from
                        </span>
                        <span className="font-bold text-white text-sm">
                          {startPrice > 0 ? `₹${startPrice.toLocaleString("en-IN")}` : "Custom Quote"}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <Link
                          href={`/compare?ids=${encodeURIComponent(pro.id)}`}
                          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-colors"
                          title="Compare studio"
                        >
                          <SlidersHorizontal className="w-4 h-4" />
                        </Link>
                        <Link
                          href={`/professionals/${encodeURIComponent(pro.slug)}`}
                          className="px-3.5 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-md transition-all"
                        >
                          View Profile
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Value Pillars */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 border-y border-white/5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-[#FF5E1E]/10 border border-[#FF5E1E]/20 flex items-center justify-center text-[#FF5E1E]">
              <Camera className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-white text-lg">Portfolio-First Discovery</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Sanitized client galleries backed by PostgreSQL visibility controls and private/public bucket isolation.
            </p>
          </div>

          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-white text-lg">Verified Trust & Reviews</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Only clients with completed bookings can review, and every review passes moderation before affecting studio ratings.
            </p>
          </div>

          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-white text-lg">AI-Assisted Matching</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              7-factor weighted ranking grounds city, category, experience, budget, and ratings directly in database records.
            </p>
          </div>
        </div>
      </section>

      {/* For Professionals SaaS Banner */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl bg-gradient-to-r from-[#171821] via-[#1a1c26] to-[#171821] border border-white/10 p-8 sm:p-12 flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="space-y-4 max-w-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FF5E1E]/10 text-xs font-semibold text-[#FF5E1E]">
              <Award className="w-3.5 h-3.5" />
              MaanCamera for Studios
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">
              Grow Your Photography & Studio Business
            </h2>
            <p className="text-sm text-gray-400 leading-relaxed">
              Onboard your services, publish draft-reviewed galleries, respond to client enquiries with digital quotations, and track booking escrow.
            </p>
            <div className="flex flex-wrap items-center gap-6 text-xs text-gray-300 pt-2">
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Free to Register</span>
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Private Client Proofs</span>
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Direct Quotations</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href="/register"
              className="px-6 py-3.5 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-sm shadow-xl shadow-[#FF5E1E]/20 text-center transition-all"
            >
              Register as Professional
            </Link>
            <Link
              href="/professional/dashboard"
              className="px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold text-sm text-center border border-white/10 transition-colors"
            >
              Open Studio Portal
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
