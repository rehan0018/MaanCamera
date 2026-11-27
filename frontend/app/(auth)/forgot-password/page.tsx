"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { KeyRound, ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { notify } = useToast();
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.requestPasswordReset({ email: email.trim() });
      notify("If that email exists, a reset token has been queued.", "success");
      setStep("confirm");
    } catch (err: any) {
      notify(err?.message || "Failed to request password reset.", "error");
    } finally {
      setBusy(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.confirmPasswordReset({ token: token.trim(), new_password: newPassword });
      notify("Password updated cleanly! Please sign in.", "success");
      router.push("/login");
    } catch (err: any) {
      notify(err?.message || "Reset confirmation failed.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md p-8 rounded-3xl bg-[#14151b] border border-white/10 space-y-6 text-xs">
        <Link href="/login" className="inline-flex items-center gap-1.5 text-gray-400 hover:text-white">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Sign In
        </Link>
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-[#FF5E1E]" /> Reset Password
          </h1>
          <p className="text-gray-400">Single-use token resets revoke all active sessions immediately.</p>
        </div>

        {step === "request" ? (
          <form onSubmit={handleRequest} className="space-y-4">
            <input
              type="email"
              required
              placeholder="Account email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-white"
            />
            <button type="submit" disabled={busy} className="w-full py-2.5 rounded-xl bg-[#FF5E1E] text-white font-semibold">
              {busy ? "Sending..." : "Send Password Reset Link"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirm} className="space-y-4">
            <input
              type="text"
              required
              placeholder="Paste reset token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-white"
            />
            <input
              type="password"
              required
              minLength={8}
              placeholder="New password (min 8 chars)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/10 rounded-xl px-4 py-2.5 text-white"
            />
            <button type="submit" disabled={busy} className="w-full py-2.5 rounded-xl bg-[#FF5E1E] text-white font-semibold">
              {busy ? "Updating..." : "Confirm New Password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
