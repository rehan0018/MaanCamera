"use client";

import { useState } from "react";
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
  Film,
  Video,
  Eye,
  Award,
} from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCity, setSelectedCity] = useState("Pune");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      router.push(`/search?city=${encodeURIComponent(selectedCity)}`);
    } else {
      router.push(`/search?ai=true&query=${encodeURIComponent(searchQuery)}`);
    }
  };

  const categories = [
    { name: "Wedding Photography", slug: "wedding-photography", icon: Camera, count: "450+ Verified" },
    { name: "Cinematic Films", slug: "cinematic-films", icon: Film, count: "280+ Creators" },
    { name: "Portrait & Fashion", slug: "portrait-fashion", icon: Eye, count: "310+ Artists" },
    { name: "Drone & Aerial", slug: "drone-aerial", icon: Video, count: "120+ Pilots" },
  ];

  const featuredPros = [
    {
      id: "b1000000-0000-0000-0000-000000000001",
      name: "Aura Weddings & Films",
      slug: "aura-weddings-pune",
      city: "Pune, Maharashtra",
      rating: 4.9,
      reviews: 48,
      price: "â‚¹45,000",
      experience: "8 yrs exp",
      specialty: "Candid & Cinematic",
      image: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=600&q=80",
    },
    {
      id: "b1000000-0000-0000-0000-000000000002",
      name: "Drishti Visuals",
      slug: "drishti-visuals-mumbai",
      city: "Mumbai, Maharashtra",
      rating: 4.85,
      reviews: 36,
      price: "â‚¹60,000",
      experience: "6 yrs exp",
      specialty: "Luxury Weddings",
      image: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=600&q=80",
    },
    {
      id: "b1000000-0000-0000-0000-000000000003",
      name: "Varanasi Heritage Lens",
      slug: "varanasi-heritage-lens",
      city: "Delhi NCR",
      rating: 4.95,
      reviews: 52,
      price: "â‚¹75,000",
      experience: "10 yrs exp",
      specialty: "Traditional & Royal",
      image: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&w=600&q=80",
    },
  ];

  return (
    <div className="space-y-20 pb-20">
      {/* Hero Section */}
      <section className="relative pt-16 pb-24 overflow-hidden border-b border-white/5 bg-gradient-to-b from-[#131418] via-[#0e0f13] to-[#0d0e12]">
        <div className="absolute inset-0 bg-[radial-gradient(#FF5E1E_1px,transparent_1px)] [background-size:24px_24px] opacity-10" />

        <div className="max-w-5xl mx-auto px-4 text-center relative z-10 space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-[#FF5E1E]">
            <Sparkles className="w-3.5 h-3.5" />
            <span>India's AI-Powered Creative Marketplace</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Discover. Compare. <br className="hidden sm:inline" />
            Connect. <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF5E1E] to-[#FFA07A]">Capture.</span>
          </h1>

          <p className="max-w-2xl mx-auto text-base sm:text-lg text-gray-400">
            Find the perfect photography and videography team for your wedding, brand, or event. Verified portfolios, transparent quotations, and AI matching.
          </p>

          {/* Search Bar Form */}
          <form onSubmit={handleSearch} className="max-w-3xl mx-auto mt-8 p-2 rounded-2xl bg-[#1a1b22] border border-white/15 shadow-2xl flex flex-col sm:flex-row gap-2">
            <div className="flex-1 flex items-center px-4 py-2 gap-2 text-sm text-gray-300">
              <Sparkles className="w-4 h-4 text-[#FF5E1E] shrink-0" />
              <input
                type="text"
                placeholder="Ask AI: 'Candid wedding photographer in Pune under 50,000 for 2 days'..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent placeholder-gray-500 focus:outline-none text-white text-sm"
              />
            </div>

            <div className="flex items-center gap-2 px-3 py-2 border-t sm:border-t-0 sm:border-l border-white/10 text-sm">
              <MapPin className="w-4 h-4 text-gray-400 shrink-0" />
              <select
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="bg-transparent text-gray-300 focus:outline-none text-xs sm:text-sm font-medium"
              >
                <option value="Pune" className="bg-[#1a1b22]">Pune</option>
                <option value="Mumbai" className="bg-[#1a1b22]">Mumbai</option>
                <option value="Delhi" className="bg-[#1a1b22]">Delhi NCR</option>
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

          {/* Suggestions */}
          <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-gray-400 pt-2">
            <span className="text-gray-500">Popular:</span>
            <button
              type="button"
              onClick={() => {
                setSearchQuery("Candid wedding photographer in Pune under 50k");
              }}
              className="px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
            >
              Wedding in Pune under 50k
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchQuery("Cinematic drone videographer Mumbai");
              }}
              className="px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
            >
              Cinematic Drone Mumbai
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchQuery("Traditional pre-wedding shoot Delhi");
              }}
              className="px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
            >
              Pre-wedding Delhi
            </button>
          </div>
        </div>
      </section>

      {/* Categories Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Explore by Category</h2>
            <p className="text-xs text-gray-400 mt-1">Specialized visual professionals across every genre</p>
          </div>
          <Link href="/search" className="text-xs font-semibold text-[#FF5E1E] hover:underline flex items-center gap-1">
            View All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {categories.map((cat) => {
            const Icon = cat.icon;
            return (
              <Link
                key={cat.slug}
                href={`/search?category=${cat.slug}`}
                className="group p-5 rounded-xl bg-[#14151b] border border-white/5 hover:border-[#FF5E1E]/40 hover:bg-[#1a1c24] transition-all flex flex-col justify-between"
              >
                <div className="w-10 h-10 rounded-lg bg-white/5 group-hover:bg-[#FF5E1E]/10 flex items-center justify-center text-gray-300 group-hover:text-[#FF5E1E] transition-colors mb-4">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-white text-sm group-hover:text-[#FF5E1E] transition-colors">
                    {cat.name}
                  </h3>
                  <span className="text-xs text-gray-500 font-medium">{cat.count}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Featured Professionals */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Featured Verified Professionals</h2>
            <p className="text-xs text-gray-400 mt-1">Identity, portfolio, and booking-verified studios</p>
          </div>
          <Link href="/search?verified_only=true" className="text-xs font-semibold text-[#FF5E1E] hover:underline flex items-center gap-1">
            See All Verified <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {featuredPros.map((pro) => (
            <div
              key={pro.id}
              className="rounded-2xl bg-[#14151b] border border-white/10 overflow-hidden hover:border-white/20 transition-all flex flex-col group"
            >
              <div className="relative h-48 w-full overflow-hidden bg-gray-900">
                <img
                  src={pro.image}
                  alt={pro.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
                <div className="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-black/60 backdrop-blur-md text-[11px] font-semibold text-emerald-400 flex items-center gap-1 border border-emerald-500/20">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Verified Studio
                </div>
                <div className="absolute top-3 right-3 px-2 py-1 rounded-md bg-black/60 backdrop-blur-md text-[11px] font-semibold text-white flex items-center gap-1">
                  <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                  {pro.rating} ({pro.reviews})
                </div>
              </div>

              <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-white text-base group-hover:text-[#FF5E1E] transition-colors">
                      {pro.name}
                    </h3>
                    <span className="text-xs text-gray-400">{pro.experience}</span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
                    <MapPin className="w-3.5 h-3.5 text-gray-500" />
                    <span>{pro.city}</span>
                  </div>
                  <div className="inline-block mt-2 px-2 py-0.5 rounded bg-white/5 text-[11px] text-gray-300">
                    {pro.specialty}
                  </div>
                </div>

                <div className="pt-3 border-t border-white/5 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-gray-500 block">Starting from</span>
                    <span className="font-bold text-white text-sm">{pro.price}</span>
                  </div>
                  <div className="flex gap-2">
                    <Link
                      href={`/search?compare=${pro.id}`}
                      className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-colors"
                      title="Add to comparison"
                    >
                      <SlidersHorizontal className="w-4 h-4" />
                    </Link>
                    <Link
                      href={`/search`}
                      className="px-3.5 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-md transition-all"
                    >
                      View Profile
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
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
              Real client photo projects and videos, not bought followers or fabricated descriptions. High-definition galleries inspectable down to lighting and equipment.
            </p>
          </div>

          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-white text-lg">Verified Trust & Reviews</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Strict triple verification: government ID, business registration, and verified booking reviews. Only clients with completed bookings can leave feedback.
            </p>
          </div>

          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-white text-lg">AI-Assisted Matching</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Open-source 7-factor weighted algorithm analyzes your dates, city, budget, and visual style to recommend eligible candidates with clear match explanations.
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
              MaanCamera for Business
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">
              Grow Your Photography & Studio Business
            </h2>
            <p className="text-sm text-gray-400 leading-relaxed">
              Publish structured portfolios, receive high-intent client enquiries, generate digital quotations, confirm advance bookings, and get discovered by clients across India.
            </p>
            <div className="flex items-center gap-6 text-xs text-gray-300 pt-2">
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Free to Register</span>
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Zero Upfront Lock-in</span>
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
              Explore Studio Portal
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
