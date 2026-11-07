"use client";

import Link from "next/link";
import { Camera, Search, Sparkles, User, Briefcase, SlidersHorizontal } from "lucide-react";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-[#131418]/90 backdrop-blur-md border-b border-white/10 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FF5E1E] to-[#FFA07A] flex items-center justify-center shadow-lg shadow-[#FF5E1E]/20 group-hover:scale-105 transition-transform">
            <Camera className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold tracking-tight text-lg text-white">
              MAAN<span className="text-[#FF5E1E]">CAMERA</span>
            </span>
            <span className="text-[10px] tracking-wider text-gray-400 uppercase -mt-1 font-medium">
              Discover. Compare. Connect.
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-300">
          <Link href="/search" className="hover:text-white transition-colors flex items-center gap-1.5">
            <Search className="w-4 h-4 text-gray-400" />
            Explore
          </Link>
          <Link href="/search" className="hover:text-white transition-colors">
            Categories
          </Link>
          <Link href="/search?ai=true" className="hover:text-[#FF5E1E] transition-colors flex items-center gap-1.5 text-[#FF5E1E]">
            <Sparkles className="w-4 h-4" />
            AI Match
          </Link>
          <Link href="/compare" className="hover:text-white transition-colors flex items-center gap-1.5">
            <SlidersHorizontal className="w-4 h-4 text-gray-400" />
            Compare
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/professional/dashboard"
            className="hidden sm:flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg border border-white/15 hover:border-white/30 text-gray-200 hover:text-white transition-colors"
          >
            <Briefcase className="w-3.5 h-3.5 text-[#FF5E1E]" />
            For Professionals
          </Link>
          <Link
            href="/login"
            className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] text-white shadow-md shadow-[#FF5E1E]/20 transition-all"
          >
            <User className="w-3.5 h-3.5" />
            Sign In
          </Link>
        </div>
      </div>
    </header>
  );
}
