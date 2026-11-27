"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Check, Star, ShieldCheck, SlidersHorizontal, Loader2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";

interface ComparedPro {
  id: string;
  display_name: string;
  slug: string;
  headline?: string | null;
  base_city: string;
  years_experience: number;
  avg_rating: number;
  total_reviews: number;
  verification_status: string;
  travel_available: boolean;
  services: string[];
}

function CompareContent() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";

  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>(
    idsParam
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 4)
  );
  const [compared, setCompared] = useState<ComparedPro[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .searchProfessionals({ limit: 12 })
      .then((res) => {
        const list = Array.isArray(res.data?.results) ? res.data.results : [];
        setCandidates(list);
        if (selectedIds.length === 0 && list.length >= 2) {
          setSelectedIds(list.slice(0, 3).map((p: any) => p.id));
        }
      })
      .catch((err) => setError(err?.message || "Unable to fetch professionals for comparison."));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    async function loadMatrix() {
      if (selectedIds.length < 2) {
        setCompared([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const res = await api.compareProfessionals(selectedIds);
        setCompared(Array.isArray(res.data?.professionals) ? res.data.professionals : []);
      } catch (err: any) {
        setError(err?.message || "Failed to compare selected professionals.");
        setCompared([]);
      } finally {
        setLoading(false);
      }
    }
    loadMatrix();
  }, [selectedIds]);

  const toggleCandidate = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link href="/search" className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Search
        </Link>
        <span className="text-xs text-[#FF5E1E] font-semibold flex items-center gap-1">
          <SlidersHorizontal className="w-3.5 h-3.5" /> Comparing {compared.length} of 4 Studios
        </span>
      </div>

      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Side-by-Side Comparison</h1>
        <p className="text-xs text-gray-400 mt-1">
          Select 2 to 4 onboarded studios to compare ratings, verified credentials, experience, and services from PostgreSQL.
        </p>
      </div>

      {candidates.length > 0 && (
        <div className="p-4 rounded-2xl bg-[#14151b] border border-white/10 space-y-3">
          <p className="text-xs font-semibold text-gray-300">Select Studios ({selectedIds.length}/4)</p>
          <div className="flex flex-wrap gap-2">
            {candidates.map((cand) => {
              const active = selectedIds.includes(cand.id);
              return (
                <button
                  key={cand.id}
                  type="button"
                  onClick={() => toggleCandidate(cand.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    active
                      ? "bg-[#FF5E1E]/20 border-[#FF5E1E] text-white"
                      : "bg-white/5 border-white/10 text-gray-400 hover:text-white"
                  }`}
                >
                  {cand.display_name} ({cand.base_city})
                </button>
              );
            })}
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-xs text-gray-400 py-10">
          <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading live comparison matrix...
        </div>
      ) : compared.length < 2 ? (
        <div className="p-8 rounded-2xl bg-[#14151b] border border-white/10 text-center space-y-2">
          <p className="text-sm font-bold text-white">Select at least 2 professionals to compare</p>
          <p className="text-xs text-gray-400">
            Shortlist studios in the directory or toggle two studios above.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse bg-[#14151b] border border-white/10 rounded-2xl overflow-hidden text-xs">
            <thead>
              <tr className="border-b border-white/10 bg-[#171822]">
                <th className="p-4 w-48 text-gray-400 font-semibold uppercase tracking-wider text-[11px]">
                  Feature / Profile
                </th>
                {compared.map((p) => (
                  <th key={p.id} className="p-4 min-w-[220px]">
                    <div className="font-bold text-white text-sm">{p.display_name}</div>
                    <div className="text-gray-400 text-xs mt-0.5">{p.base_city}</div>
                    {p.verification_status === "verified" ? (
                      <div className="flex items-center gap-1 mt-1 text-emerald-400 font-medium">
                        <ShieldCheck className="w-3.5 h-3.5" /> Verified Studio
                      </div>
                    ) : (
                      <div className="text-gray-500 text-[11px] mt-1 capitalize">{p.verification_status}</div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-gray-300">
              <tr>
                <td className="p-4 font-semibold text-gray-400">Headline</td>
                {compared.map((p) => (
                  <td key={p.id} className="p-4 text-gray-300">{p.headline || "Creative Professional"}</td>
                ))}
              </tr>
              <tr>
                <td className="p-4 font-semibold text-gray-400">Rating & Reviews</td>
                {compared.map((p) => (
                  <td key={p.id} className="p-4">
                    <div className="flex items-center gap-1 text-white font-medium">
                      <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                      <span>{Number(p.avg_rating || 0).toFixed(1)}</span>
                      <span className="text-gray-400 font-normal">({p.total_reviews} approved)</span>
                    </div>
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-4 font-semibold text-gray-400">Experience</td>
                {compared.map((p) => (
                  <td key={p.id} className="p-4">{p.years_experience} Years</td>
                ))}
              </tr>
              <tr>
                <td className="p-4 font-semibold text-gray-400">Active Services</td>
                {compared.map((p) => (
                  <td key={p.id} className="p-4 space-y-1">
                    {p.services.length > 0 ? (
                      p.services.map((s) => (
                        <div key={s} className="flex items-center gap-1 text-gray-300">
                          <Check className="w-3 h-3 text-emerald-400 shrink-0" />
                          <span>{s}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-gray-500">None listed</span>
                    )}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-4 font-semibold text-gray-400">Travel Availability</td>
                {compared.map((p) => (
                  <td key={p.id} className="p-4 font-medium">
                    {p.travel_available ? (
                      <span className="text-emerald-400">Available to Travel</span>
                    ) : (
                      <span className="text-gray-400">Base City Only</span>
                    )}
                  </td>
                ))}
              </tr>
              <tr className="bg-[#171822]">
                <td className="p-4 font-semibold text-gray-400">Actions</td>
                {compared.map((p) => (
                  <td key={p.id} className="p-4">
                    <Link
                      href={`/professionals/${encodeURIComponent(p.slug)}?enquire=1`}
                      className="block text-center px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-xs transition-colors shadow-md shadow-[#FF5E1E]/20"
                    >
                      View & Request Quote
                    </Link>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading comparison...
        </div>
      }
    >
      <CompareContent />
    </Suspense>
  );
}
