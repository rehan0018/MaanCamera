"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Shield, Key, Smartphone, Download, Trash2, Loader2, LogOut } from "lucide-react";
import { api, ConsentRecordItem, UserSessionItem } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";

export default function SettingsPage() {
  const { user, loading: authLoading, refreshUser, logout } = useAuth();
  const { notify } = useToast();

  const [sessions, setSessions] = useState<UserSessionItem[]>([]);
  const [consents, setConsents] = useState<ConsentRecordItem[]>([]);
  const [totpSecret, setTotpSecret] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [phoneInput, setPhoneInput] = useState("");
  const [phoneOtp, setPhoneOtp] = useState("");
  const [emailToken, setEmailToken] = useState("");

  const loadSettingsData = useCallback(async () => {
    if (!user) return;
    try {
      const [sRes, cRes] = await Promise.all([api.listSessions(), api.getMyConsents()]);
      setSessions(Array.isArray(sRes.data) ? sRes.data : []);
      setConsents(Array.isArray(cRes.data) ? cRes.data : []);
    } catch (err: any) {
      notify(err?.message || "Failed to load security settings.", "error");
    }
  }, [user, notify]);

  useEffect(() => {
    if (!authLoading && user) {
      setPhoneInput(user.phone || "");
      loadSettingsData();
    }
  }, [authLoading, user, loadSettingsData]);

  if (authLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading security settings...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center space-y-4">
        <h1 className="text-2xl font-extrabold text-white">Account & Privacy Settings</h1>
        <p className="text-xs text-gray-400">Sign in to manage 2FA, sessions, OTP verification, and DPDPA privacy controls.</p>
        <Link href="/login?next=/settings" className="inline-block px-5 py-2.5 rounded-xl bg-[#FF5E1E] text-white text-xs font-semibold">
          Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8 text-xs">
      <div>
        <h1 className="text-2xl font-extrabold text-white">Account Security & DPDPA Privacy</h1>
        <p className="text-gray-400 mt-1">{user.full_name} ({user.email}) • Role: {user.role}</p>
      </div>

      {/* Verification */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-[#FF5E1E]" /> Email & Phone Verification
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-[#1a1b24] space-y-2">
            <div className="font-semibold text-white">
              Email: {user.email_verified ? "Verified" : "Unverified"}
            </div>
            <button
              type="button"
              onClick={() => api.requestEmailVerification().then(() => notify("Verification email requested.", "success")).catch((e) => notify(e.message, "error"))}
              className="px-3 py-1.5 rounded-lg bg-white/10 text-white"
            >
              Request Verification Token
            </button>
            <div className="flex gap-2 pt-1">
              <input
                type="text"
                placeholder="Email token"
                value={emailToken}
                onChange={(e) => setEmailToken(e.target.value)}
                className="flex-1 bg-[#131418] border border-white/10 rounded px-2 py-1 text-white"
              />
              <button
                type="button"
                onClick={() => api.confirmEmailVerification({ token: emailToken }).then(() => { notify("Email verified!", "success"); refreshUser(); }).catch((e) => notify(e.message, "error"))}
                className="px-3 py-1 rounded bg-[#FF5E1E] text-white font-semibold"
              >
                Verify
              </button>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#1a1b24] space-y-2">
            <div className="font-semibold text-white">
              Phone OTP: {user.phone_verified ? "Verified" : "Unverified"}
            </div>
            <div className="flex gap-2">
              <input
                type="tel"
                placeholder="+91..."
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                className="flex-1 bg-[#131418] border border-white/10 rounded px-2 py-1 text-white"
              />
              <button
                type="button"
                onClick={() => api.requestPhoneOtp({ phone: phoneInput }).then(() => notify("OTP dispatched.", "success")).catch((e) => notify(e.message, "error"))}
                className="px-3 py-1 rounded bg-white/10 text-white"
              >
                Send OTP
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="6-digit OTP"
                value={phoneOtp}
                onChange={(e) => setPhoneOtp(e.target.value)}
                className="flex-1 bg-[#131418] border border-white/10 rounded px-2 py-1 text-white"
              />
              <button
                type="button"
                onClick={() => api.confirmPhoneOtp({ code: phoneOtp }).then(() => { notify("Phone verified!", "success"); refreshUser(); }).catch((e) => notify(e.message, "error"))}
                className="px-3 py-1 rounded bg-[#FF5E1E] text-white font-semibold"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* TOTP 2FA */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-3">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Key className="w-4 h-4 text-emerald-400" /> Two-Factor Authentication (TOTP)
        </h2>
        {!user.totp_enabled ? (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => api.setupTotp().then((res) => setTotpSecret(res.data.secret)).catch((e) => notify(e.message, "error"))}
              className="px-3.5 py-2 rounded-lg bg-white/10 text-white font-semibold"
            >
              Generate TOTP Secret
            </button>
            {totpSecret && <p className="text-amber-300">Secret Key: <code>{totpSecret}</code></p>}
            <div className="flex gap-2 max-w-sm">
              <input
                type="text"
                placeholder="Authenticator 6-digit code"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="flex-1 bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
              />
              <button
                type="button"
                onClick={() => api.enableTotp({ code: totpCode }).then(() => { notify("2FA Enabled.", "success"); refreshUser(); }).catch((e) => notify(e.message, "error"))}
                className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold"
              >
                Enable 2FA
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2 max-w-sm">
            <input
              type="text"
              placeholder="Current 6-digit TOTP code"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              className="flex-1 bg-[#1b1c23] border border-white/10 rounded-lg px-3 py-2 text-white"
            />
            <button
              type="button"
              onClick={() => api.disableTotp({ code: totpCode }).then(() => { notify("2FA Disabled.", "info"); refreshUser(); }).catch((e) => notify(e.message, "error"))}
              className="px-4 py-2 rounded-lg bg-red-600 text-white font-semibold"
            >
              Disable 2FA
            </button>
          </div>
        )}
      </div>

      {/* Sessions */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-3">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Shield className="w-4 h-4 text-[#FF5E1E]" /> Active Device Sessions ({sessions.length})
        </h2>
        <div className="space-y-2">
          {sessions.map((s) => (
            <div key={s.id} className="p-3 rounded-xl bg-[#1a1b24] flex items-center justify-between gap-3">
              <div>
                <div className="text-white font-medium">{s.user_agent || "Browser Session"} {s.is_current && "(Current)"}</div>
                <div className="text-gray-400">IP: {s.ip_address || "n/a"} • Last used: {new Date(s.last_used_at).toLocaleString()}</div>
              </div>
              {!s.revoked_at && (
                <button
                  type="button"
                  onClick={() => api.revokeSession(s.id).then(() => { notify("Session revoked.", "info"); loadSettingsData(); }).catch((e) => notify(e.message, "error"))}
                  className="px-3 py-1 rounded bg-white/10 text-gray-200 flex items-center gap-1"
                >
                  <LogOut className="w-3 h-3" /> Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* DPDPA Data Export & Account Erasure */}
      <div className="p-6 rounded-2xl bg-[#14151b] border border-white/10 space-y-4">
        <h2 className="text-base font-bold text-white">DPDPA 2023 Data Portability & Erasure</h2>
        <p className="text-gray-400">Recorded consents: {consents.length}</p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={async () => {
              const res = await api.exportMyData();
              const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "maancamera-data-export.json";
              link.click();
              URL.revokeObjectURL(url);
            }}
            className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> Download Personal Data JSON
          </button>
          <button
            type="button"
            onClick={() => {
              api
                .deleteMyAccount({ confirm_phrase: "DELETE" })
                .then(async () => {
                  await logout();
                  notify("Account anonymized cleanly under DPDPA.", "info");
                })
                .catch((e) => notify(e.message, "error"));
            }}
            className="px-4 py-2 rounded-xl bg-red-500/20 text-red-300 border border-red-500/30 font-semibold flex items-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" /> Anonymize & Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
