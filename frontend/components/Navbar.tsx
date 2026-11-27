"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Camera,
  Search,
  Sparkles,
  User,
  Briefcase,
  SlidersHorizontal,
  Menu,
  X,
  LogOut,
  Settings,
  LayoutDashboard,
} from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

export default function Navbar() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const dashboardHref =
    user?.role === "admin"
      ? "/admin/dashboard"
      : user?.role === "professional"
        ? "/professional/dashboard"
        : "/customer/dashboard";

  const handleLogout = async () => {
    await logout();
    setMobileOpen(false);
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-50 bg-[#131418]/95 backdrop-blur-md border-b border-white/10 text-white">
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
          <Link href="/search?ai=true" className="hover:text-[#FF5E1E] transition-colors flex items-center gap-1.5 text-[#FF5E1E]">
            <Sparkles className="w-4 h-4" />
            AI Match
          </Link>
          <Link href="/compare" className="hover:text-white transition-colors flex items-center gap-1.5">
            <SlidersHorizontal className="w-4 h-4 text-gray-400" />
            Compare
          </Link>
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              <Link
                href={dashboardHref}
                className="flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg border border-white/15 hover:border-white/30 text-gray-200 hover:text-white transition-colors"
              >
                <LayoutDashboard className="w-3.5 h-3.5 text-[#FF5E1E]" />
                Dashboard
              </Link>
              <Link
                href="/settings"
                aria-label="Account Settings"
                className="p-2 rounded-lg border border-white/10 hover:border-white/25 text-gray-300 hover:text-white transition-colors"
              >
                <Settings className="w-4 h-4" />
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/register"
                className="flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg border border-white/15 hover:border-white/30 text-gray-200 hover:text-white transition-colors"
              >
                <Briefcase className="w-3.5 h-3.5 text-[#FF5E1E]" />
                Join Studio / Client
              </Link>
              <Link
                href="/login"
                className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] text-white shadow-md shadow-[#FF5E1E]/20 transition-all"
              >
                <User className="w-3.5 h-3.5" />
                Sign In
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          aria-label="Toggle mobile menu"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((prev) => !prev)}
          className="md:hidden p-2 rounded-lg border border-white/15 text-gray-200 hover:text-white"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-white/10 bg-[#131418] px-4 py-4 space-y-3 text-sm">
          <Link href="/search" onClick={() => setMobileOpen(false)} className="block py-1.5 text-gray-200 hover:text-white">
            Explore Professionals
          </Link>
          <Link href="/search?ai=true" onClick={() => setMobileOpen(false)} className="block py-1.5 text-[#FF5E1E]">
            AI Requirement Match
          </Link>
          <Link href="/compare" onClick={() => setMobileOpen(false)} className="block py-1.5 text-gray-200 hover:text-white">
            Compare Studios
          </Link>
          <div className="pt-2 border-t border-white/10 flex flex-col gap-2">
            {user ? (
              <>
                <Link
                  href={dashboardHref}
                  onClick={() => setMobileOpen(false)}
                  className="px-3 py-2 rounded-lg bg-[#FF5E1E] text-white text-xs font-semibold text-center"
                >
                  Open Dashboard ({user.full_name})
                </Link>
                <Link
                  href="/settings"
                  onClick={() => setMobileOpen(false)}
                  className="px-3 py-2 rounded-lg border border-white/15 text-xs font-semibold text-center text-gray-200"
                >
                  Account & Privacy Settings
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="px-3 py-2 rounded-lg bg-white/10 text-xs font-semibold text-white"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="px-3 py-2 rounded-lg bg-[#FF5E1E] text-white text-xs font-semibold text-center"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileOpen(false)}
                  className="px-3 py-2 rounded-lg border border-white/15 text-xs font-semibold text-center text-gray-200"
                >
                  Create Account
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
