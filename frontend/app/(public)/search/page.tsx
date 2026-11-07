"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Search,
  SlidersHorizontal,
  MapPin,
  ShieldCheck,
  Star,
  Check,
  ArrowRight,
  Sparkles,
  Camera,
  Filter,
} from "lucide-react";

export default function SearchPage() {
  const [city, setCity] = useState("All");
  const [category, setCategory] = useState("all");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [aiMode, setAiMode] = useState(false);
  const [aiQuery, setAiQuery] = useState("");
  const [shortlist, setShortlist] = useState<string[]>([]);

  const mockProfiles = [
    {
      id: "b1000000-0000-0000-0000-000000000001",
      name: "Aura Weddings & Films",
      slug: "aura-weddings-pune",
      headline: "Premier Candid Wedding Photography & 4K Cinematic Films",
      city: "Pune",
      rating: 4.9,
      reviews: 48,
      starting_price: 45000,
      verified: true,
      experience: 8,
      styles: ["Candid", "Cinematic", "Pre-wedding"],
      image: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=600&q=80",
    },
    {
      id: "b1000000-0000-0000-0000-000000000002",
      name: "Drishti Visuals",
      slug: "drishti-visuals-mumbai",
      headline: "Luxury Destination Weddings & Commercial Fashion Productions",
      city: "Mumbai",
      rating: 4.85,
      reviews: 36,
      starting_price: 60000,
      verified: true,
      experience: 6,
      styles: ["Traditional", "Drone", "Fashion"],
      image: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=600&q=80",
    },
    {
      id: "b1000000-0000-0000-0000-000000000003",
      name: "Varanasi Heritage Lens",
      slug: "varanasi-heritage-lens",
      headline: "Timeless Royal Weddings & Fine-Art Portraiture",
      city: "Delhi",
      rating: 4.95,
      reviews: 52,
      starting_price: 75000,
      verified: true,
      experience: 10,
      styles: ["Royal", "Candid", "Fine-Art"],
      image: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&w=600&q=80",
    },
    {
      id: "b1000000-0000-0000-0000-000000000004",
      name: "Namma Studio Bengaluru",
      slug: "namma-studio-bengaluru",
      headline: "Contemporary Architecture, Drone & Corporate Media",
      city: "Bengaluru",
      rating: 4.78,
      reviews: 29,
      starting_price: 35000,
      verified: true,
      experience: 5,
      styles: ["Architecture", "Drone", "Corporate"],
      image: "https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=600&q=80",
    },
  ];

  const toggleShortlist = (id: string) => {
    if (shortlist.includes(id)) {
      setShortlist(shortlist.filter((x) => x !== id));
    } else {
      if (shortlist.length >= 4) {
        alert("You can compare up to 4 professionals at a time.");
        return;
      }
      setShortlist([...shortlist, id]);
    }
  };

  const filtered = mockProfiles.filter((p) => {
    if (city !== "All" && p.city.toLowerCase() !== city.toLowerCase()) return false;
    if (verifiedOnly && !p.verified) return false;
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Top Header & AI Toggle */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Find Creative Professionals</h1>
          <p className="text-xs text-gray-400 mt-1">
            Compare portfolios, verify credentials, and connect directly with verified teams.
          </p>
        </div>

        <button
          onClick={() => setAiMode(!aiMode)}
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

      {/* AI Search Box if Active */}
      {aiMode && (
        <div className="p-6 rounded-2xl bg-gradient-to-r from-[#1b1c24] to-[#14151c] border border-[#FF5E1E]/30 space-y-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#FF5E1E]">
            <Sparkles className="w-4 h-4" />
            <span>AI Natural Language Parser (Ollama / Local LLM)</span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. 'I need a candid wedding photographer in Pune for two days, budget around Rs 50,000, with cinematic video'"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[#FF5E1E]"
            />
            <button
              onClick={() => alert("AI analyzed: Extracted Category=[Wedding, Cinematic], City=Pune, Budget Max=50,000 INR, Match Score=94%")}
              className="px-5 py-2.5 rounded-xl bg-[#FF5E1E] text-white text-xs font-semibold hover:bg-[#E04E15] transition-colors"
            >
              Analyze & Rank
            </button>
          </div>
        </div>
      )}

      {/* Filter Toolbar & Results Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Filters Sidebar */}
        <div className="space-y-6 bg-[#131418] p-5 rounded-2xl border border-white/10 h-fit">
          <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider pb-3 border-b border-white/10">
            <Filter className="w-4 h-4 text-[#FF5E1E]" />
            <span>Search Filters</span>
          </div>

          {/* City Filter */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-300">City / Location</label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="All">All Cities</option>
              <option value="Pune">Pune</option>
              <option value="Mumbai">Mumbai</option>
              <option value="Delhi">Delhi NCR</option>
              <option value="Bengaluru">Bengaluru</option>
              <option value="Jaipur">Jaipur</option>
            </select>
          </div>

          {/* Category Filter */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-300">Service Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="all">All Categories</option>
              <option value="wedding">Wedding Photography</option>
              <option value="cinematic">Cinematic Films</option>
              <option value="fashion">Portrait & Fashion</option>
              <option value="commercial">Corporate & Commercial</option>
              <option value="drone">Drone & Aerial</option>
            </select>
          </div>

          {/* Verified Only Checkbox */}
          <div className="pt-2">
            <label className="flex items-center gap-2.5 text-xs text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={verifiedOnly}
                onChange={(e) => setVerifiedOnly(e.target.checked)}
                className="rounded border-white/20 text-[#FF5E1E] focus:ring-0"
              />
              <span className="font-medium">Verified Professionals Only</span>
            </label>
          </div>
        </div>

        {/* Results List */}
        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>Showing <strong className="text-white">{filtered.length}</strong> available visual professionals</span>
            <span>Sorted by: <strong>Relevance & Verified Rating</strong></span>
          </div>

          <div className="space-y-4">
            {filtered.map((pro) => {
              const isShortlisted = shortlist.includes(pro.id);
              return (
                <div
                  key={pro.id}
                  className="p-5 rounded-2xl bg-[#14151b] border border-white/10 hover:border-white/20 transition-all flex flex-col md:flex-row gap-5"
                >
                  <div className="w-full md:w-56 h-44 rounded-xl overflow-hidden shrink-0 bg-gray-900 relative">
                    <img src={pro.image} alt={pro.name} className="w-full h-full object-cover" />
                    {pro.verified && (
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-[10px] font-semibold text-emerald-400 flex items-center gap-1 border border-emerald-500/20">
                        <ShieldCheck className="w-3 h-3" /> Verified
                      </div>
                    )}
                  </div>

                  <div className="flex-1 flex flex-col justify-between space-y-3">
                    <div>
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-lg font-bold text-white hover:text-[#FF5E1E] transition-colors">
                            {pro.name}
                          </h3>
                          <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{pro.headline}</p>
                        </div>
                        <div className="flex items-center gap-1 text-xs font-semibold text-white bg-white/5 px-2.5 py-1 rounded-lg">
                          <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                          <span>{pro.rating}</span>
                          <span className="text-gray-500">({pro.reviews})</span>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400 mt-2">
                        <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5 text-gray-500" /> {pro.city}</span>
                        <span>â€¢</span>
                        <span>{pro.experience} Years Experience</span>
                        <span>â€¢</span>
                        <span>Starting â‚¹{pro.starting_price.toLocaleString("en-IN")}</span>
                      </div>

                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {pro.styles.map((s) => (
                          <span key={s} className="px-2 py-0.5 rounded bg-white/5 text-[10px] text-gray-300 font-medium">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-white/5 flex items-center justify-between">
                      <button
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
                          href={`/customer/dashboard?enquire=${pro.id}`}
                          className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
                        >
                          Send Enquiry
                        </Link>
                        <Link
                          href={`/search`}
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
        </div>
      </div>

      {/* Floating Comparison Bar if profiles shortlisted */}
      {shortlist.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-[#171822] border border-white/20 shadow-2xl rounded-2xl px-6 py-4 flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs font-semibold text-white">
            <SlidersHorizontal className="w-4 h-4 text-[#FF5E1E]" />
            <span>{shortlist.length} of 4 Selected for Comparison</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShortlist([])}
              className="text-xs text-gray-400 hover:text-white underline"
            >
              Clear
            </button>
            <Link
              href={`/compare?ids=${shortlist.join(",")}`}
              className="px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold shadow-lg transition-colors flex items-center gap-1.5"
            >
              <span>Compare Profiles</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
