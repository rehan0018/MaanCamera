"use client";

import Link from "next/link";
import { ArrowLeft, Check, X, Star, ShieldCheck, Camera, SlidersHorizontal } from "lucide-react";

export default function ComparePage() {
  const pros = [
    {
      id: "b1000000-0000-0000-0000-000000000001",
      name: "Aura Weddings & Films",
      city: "Pune",
      rating: 4.9,
      reviews: 48,
      experience: "8 Years",
      startingPrice: "â‚¹45,000",
      services: ["Candid Photography", "4K Cinematic Teaser", "Traditional Video", "Drone Aerial"],
      deliverables: "300+ Retouched Photos, 3-5 Min Film, Raw Hard Drive",
      turnaround: "21 Days",
      equipment: ["Sony A7 IV (2x)", "Sony FX3 Cinema", "DJI Mini 4 Pro Drone", "Godox Lighting"],
      travelAvailable: true,
      verified: true,
    },
    {
      id: "b1000000-0000-0000-0000-000000000002",
      name: "Drishti Visuals",
      city: "Mumbai",
      rating: 4.85,
      reviews: 36,
      experience: "6 Years",
      startingPrice: "â‚¹60,000",
      services: ["Pre-wedding Concept", "Wedding Photography", "Cinematic Film"],
      deliverables: "450+ High-Res Photos, 7-10 Min Extended Film",
      turnaround: "30 Days",
      equipment: ["Canon R5 (2x)", "RED Komodo 6K", "DJI Mavic 3", "Profoto Strobes"],
      travelAvailable: true,
      verified: true,
    },
    {
      id: "b1000000-0000-0000-0000-000000000003",
      name: "Varanasi Heritage Lens",
      city: "Delhi NCR",
      rating: 4.95,
      reviews: 52,
      experience: "10 Years",
      startingPrice: "â‚¹75,000",
      services: ["Traditional & Royal Photography", "Cinematic Heritage Film", "Drone"],
      deliverables: "500+ Curated Photos, 2 Premium Leather Albums, 10 Min Film",
      turnaround: "25 Days",
      equipment: ["Sony A1 (2x)", "Sony FX6 Cinema", "DJI Inspire 2 Drone", "Aputure Rig"],
      travelAvailable: true,
      verified: true,
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      <div className="flex items-center justify-between">
        <Link href="/search" className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Search
        </Link>
        <span className="text-xs text-[#FF5E1E] font-semibold flex items-center gap-1">
          <SlidersHorizontal className="w-3.5 h-3.5" /> Comparing 3 of 4 Professionals
        </span>
      </div>

      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Side-by-Side Comparison</h1>
        <p className="text-xs text-gray-400 mt-1">
          Evaluate capabilities, transparent rates, delivery timelines, and hardware gear across shortlisted candidates.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse bg-[#14151b] border border-white/10 rounded-2xl overflow-hidden text-xs">
          <thead>
            <tr className="border-b border-white/10 bg-[#171822]">
              <th className="p-4 w-48 text-gray-400 font-semibold uppercase tracking-wider text-[11px]">Feature / Profile</th>
              {pros.map((p) => (
                <th key={p.id} className="p-4 min-w-[220px]">
                  <div className="font-bold text-white text-sm">{p.name}</div>
                  <div className="text-gray-400 text-xs mt-0.5">{p.city}</div>
                  <div className="flex items-center gap-1 mt-1 text-emerald-400 font-medium">
                    <ShieldCheck className="w-3.5 h-3.5" /> Verified Studio
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            <tr>
              <td className="p-4 font-semibold text-gray-400">Starting Rate</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4 font-bold text-white text-sm">{p.startingPrice}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Rating & Reviews</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4">
                  <div className="flex items-center gap-1 text-white font-medium">
                    <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                    <span>{p.rating}</span>
                    <span className="text-gray-400 font-normal">({p.reviews} verified)</span>
                  </div>
                </td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Experience</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4">{p.experience}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Services Included</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4 space-y-1">
                  {p.services.map((s) => (
                    <div key={s} className="flex items-center gap-1 text-gray-300">
                      <Check className="w-3 h-3 text-emerald-400 shrink-0" />
                      <span>{s}</span>
                    </div>
                  ))}
                </td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Deliverables</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4 text-gray-300 leading-relaxed">{p.deliverables}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Turnaround Time</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4 font-medium text-white">{p.turnaround}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Camera & Drone Gear</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4 space-y-1">
                  {p.equipment.map((eq) => (
                    <div key={eq} className="flex items-center gap-1 text-[11px] text-gray-400">
                      <Camera className="w-3 h-3 text-gray-500 shrink-0" />
                      <span>{eq}</span>
                    </div>
                  ))}
                </td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-gray-400">Travel Availability</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4 text-emerald-400 font-medium">Pan-India Available</td>
              ))}
            </tr>
            <tr className="bg-[#171822]">
              <td className="p-4 font-semibold text-gray-400">Actions</td>
              {pros.map((p) => (
                <td key={p.id} className="p-4">
                  <Link
                    href={`/customer/dashboard?enquire=${p.id}`}
                    className="block text-center px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-xs transition-colors shadow-md shadow-[#FF5E1E]/20"
                  >
                    Request Quotation
                  </Link>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
