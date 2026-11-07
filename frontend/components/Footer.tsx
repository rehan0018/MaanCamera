import Link from "next/link";
import { Camera, ShieldCheck, Heart, Sparkles } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-[#0b0c0f] border-t border-white/10 text-gray-400 py-12 text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-[#FF5E1E] flex items-center justify-center">
              <Camera className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-base text-white">MAANCAMERA</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed mb-4">
            India's trusted AI-powered marketplace connecting clients with verified wedding, commercial, portrait, and cinematic visual storytellers.
          </p>
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
            <ShieldCheck className="w-4 h-4" />
            100% Free & Open-Source Foundation
          </div>
        </div>

        <div>
          <h4 className="text-white font-semibold text-xs tracking-wider uppercase mb-3">Popular Categories</h4>
          <ul className="space-y-2 text-xs">
            <li><Link href="/search?category=wedding-photography" className="hover:text-white transition-colors">Wedding Photography</Link></li>
            <li><Link href="/search?category=cinematic-films" className="hover:text-white transition-colors">Cinematic Wedding Films</Link></li>
            <li><Link href="/search?category=portrait-fashion" className="hover:text-white transition-colors">Fashion & Portrait</Link></li>
            <li><Link href="/search?category=corporate-commercial" className="hover:text-white transition-colors">Corporate & Commercial</Link></li>
            <li><Link href="/search?category=drone-aerial" className="hover:text-white transition-colors">Drone & Aerial Shoots</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-white font-semibold text-xs tracking-wider uppercase mb-3">Top Cities</h4>
          <ul className="space-y-2 text-xs">
            <li><Link href="/search?city=Pune" className="hover:text-white transition-colors">Photographers in Pune</Link></li>
            <li><Link href="/search?city=Mumbai" className="hover:text-white transition-colors">Photographers in Mumbai</Link></li>
            <li><Link href="/search?city=Delhi" className="hover:text-white transition-colors">Photographers in Delhi NCR</Link></li>
            <li><Link href="/search?city=Bengaluru" className="hover:text-white transition-colors">Photographers in Bengaluru</Link></li>
            <li><Link href="/search?city=Jaipur" className="hover:text-white transition-colors">Photographers in Jaipur</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-white font-semibold text-xs tracking-wider uppercase mb-3">Platform & Governance</h4>
          <ul className="space-y-2 text-xs">
            <li><Link href="/about" className="hover:text-white transition-colors">About MaanCamera</Link></li>
            <li><Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
            <li><Link href="/privacy" className="hover:text-white transition-colors">DPDPA 2023 Privacy Policy</Link></li>
            <li><Link href="/admin/dashboard" className="hover:text-white transition-colors">Admin & Moderation</Link></li>
            <li><a href="https://github.com/rehan0018/MaanCamera" target="_blank" rel="noopener noreferrer" className="hover:text-[#FF5E1E] transition-colors flex items-center gap-1 font-medium text-white">GitHub Repository â†—</a></li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between text-xs text-gray-500 gap-4">
        <p>Â© 2026 MaanCamera Inc. Designed and engineered for Indian creative professionals.</p>
        <p className="flex items-center gap-1">
          Built with <Heart className="w-3.5 h-3.5 text-[#FF5E1E] inline fill-current" /> using Open-Source Python & Next.js
        </p>
      </div>
    </footer>
  );
}
