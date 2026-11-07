"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Camera, Lock, Mail, User, Briefcase, ArrowRight } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<"customer" | "professional">("customer");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      if (role === "professional") {
        router.push("/professional/dashboard");
      } else {
        router.push("/customer/dashboard");
      }
    }, 800);
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md p-8 rounded-3xl bg-[#14151b] border border-white/10 shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-[#FF5E1E] mx-auto flex items-center justify-center shadow-lg shadow-[#FF5E1E]/25">
            <Camera className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white">Join MaanCamera</h1>
          <p className="text-xs text-gray-400">Discover or showcase creative photography & videography</p>
        </div>

        {/* Account Role Selector */}
        <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-[#1b1c23] border border-white/10 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setRole("customer")}
            className={`py-2 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              role === "customer" ? "bg-[#FF5E1E] text-white shadow-md" : "text-gray-400 hover:text-white"
            }`}
          >
            <User className="w-3.5 h-3.5" /> Customer
          </button>
          <button
            type="button"
            onClick={() => setRole("professional")}
            className={`py-2 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              role === "professional" ? "bg-[#FF5E1E] text-white shadow-md" : "text-gray-400 hover:text-white"
            }`}
          >
            <Briefcase className="w-3.5 h-3.5" /> Professional / Studio
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300">
              {role === "professional" ? "Studio / Professional Name" : "Full Name"}
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder={role === "professional" ? "e.g. Aura Weddings & Films" : "e.g. Rahul Sharma"}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#FF5E1E]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#FF5E1E]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300">Mobile Number (India +91)</label>
            <input
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#FF5E1E]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300">Create Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#FF5E1E]"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-xs shadow-lg shadow-[#FF5E1E]/20 transition-all flex items-center justify-center gap-2"
          >
            {loading ? "Creating Account..." : "Complete Registration"}
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="pt-4 border-t border-white/5 text-center text-xs text-gray-400">
          Already registered?{" "}
          <Link href="/login" className="font-semibold text-[#FF5E1E] hover:underline">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
