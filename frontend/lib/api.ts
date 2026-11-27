/**
 * MaanCamera Frontend API Client
 * Wraps REST endpoints with generated OpenAPI schema types, cookie credentials, and CSRF protection.
 */

import type { components, paths } from "./api.generated";

export type ApiPaths = paths;
export type ApiSchemas = components["schemas"];

type StripApiPrefix<P extends string> = P extends `/api/v1${infer Rest}` ? Rest : never;
export type ApiEndpoint = StripApiPrefix<keyof paths & string>;

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000/api/v1";
const CSRF_COOKIE_NAME = "mc_csrf";
const MUTATING_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta: {
    request_id: string;
    timestamp: string;
  };
}

export interface UserSessionItem {
  id: string;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  revoked_at: string | null;
  is_current: boolean;
}

export interface ConsentRecordItem {
  id: string;
  consent_type: string;
  policy_version: string;
  granted: boolean;
  recorded_at: string;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

async function ensureCsrfToken(): Promise<string | null> {
  const existing = getCookie(CSRF_COOKIE_NAME);
  if (existing) {
    return existing;
  }
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/auth/csrf`, {
      method: "GET",
      credentials: "include",
    });
    const cookieToken = getCookie(CSRF_COOKIE_NAME);
    if (cookieToken) {
      return cookieToken;
    }
    if (res.ok) {
      const payload = await res.json().catch(() => null);
      return payload?.data?.csrf_token ?? null;
    }
  } catch {
    return null;
  }
  return null;
}

export async function apiFetch<T>(
  endpoint: ApiEndpoint | `${ApiEndpoint}?${string}` | string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  const method = (options.method || "GET").toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (MUTATING_METHODS.has(method) && !headers["X-CSRF-Token"]) {
    const csrfToken = await ensureCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  const response = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: "include", // Send HTTP-only session cookies
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody?.error?.message || `API error: ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  // Authentication & Account Security
  getCsrf: () => apiFetch<{ csrf_token: string }>("/auth/csrf"),
  login: (data: ApiSchemas["UserLoginRequest"]) =>
    apiFetch<any>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  register: (
    data: Omit<ApiSchemas["UserRegisterRequest"], "role" | "accept_terms" | "accept_privacy" | "marketing_opt_in"> & {
      role?: ApiSchemas["UserRegisterRequest"]["role"];
      accept_terms?: boolean;
      accept_privacy?: boolean;
      marketing_opt_in?: boolean;
    }
  ) =>
    apiFetch<any>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        role: data.role ?? "customer",
        accept_terms: data.accept_terms ?? true,
        accept_privacy: data.accept_privacy ?? true,
        marketing_opt_in: data.marketing_opt_in ?? false,
      } satisfies ApiSchemas["UserRegisterRequest"]),
    }),
  refreshSession: () => apiFetch<any>("/auth/refresh", { method: "POST" }),
  logout: () => apiFetch<any>("/auth/logout", { method: "POST" }),
  requestEmailVerification: () => apiFetch<any>("/auth/verify-email/request", { method: "POST" }),
  confirmEmailVerification: (data: ApiSchemas["EmailVerifyConfirmRequest"]) =>
    apiFetch<any>("/auth/verify-email/confirm", { method: "POST", body: JSON.stringify(data) }),
  requestPhoneOtp: (data: ApiSchemas["PhoneOtpRequest"]) =>
    apiFetch<any>("/auth/verify-phone/request", { method: "POST", body: JSON.stringify(data) }),
  confirmPhoneOtp: (data: ApiSchemas["PhoneOtpConfirmRequest"]) =>
    apiFetch<any>("/auth/verify-phone/confirm", { method: "POST", body: JSON.stringify(data) }),
  requestPasswordReset: (data: ApiSchemas["PasswordResetRequest"]) =>
    apiFetch<any>("/auth/password-reset/request", { method: "POST", body: JSON.stringify(data) }),
  confirmPasswordReset: (data: ApiSchemas["PasswordResetConfirmRequest"]) =>
    apiFetch<any>("/auth/password-reset/confirm", { method: "POST", body: JSON.stringify(data) }),
  listSessions: () => apiFetch<UserSessionItem[]>("/auth/sessions"),
  revokeSession: (sessionId: string) =>
    apiFetch<any>(`/auth/sessions/${sessionId}`, { method: "DELETE" }),
  setupTotp: () => apiFetch<{ secret: string; otpauth_uri: string }>("/auth/totp/setup", { method: "POST" }),
  enableTotp: (data: ApiSchemas["TotpCodeRequest"]) =>
    apiFetch<any>("/auth/totp/enable", { method: "POST", body: JSON.stringify(data) }),
  disableTotp: (data: ApiSchemas["TotpCodeRequest"]) =>
    apiFetch<any>("/auth/totp/disable", { method: "POST", body: JSON.stringify(data) }),
  getCurrentUser: () => apiFetch<any>("/users/me"),
  getMyConsents: () => apiFetch<ConsentRecordItem[]>("/users/me/consents"),
  exportMyData: () => apiFetch<Record<string, unknown>>("/users/me/export"),
  deleteMyAccount: (data: ApiSchemas["DeleteAccountRequest"]) =>
    apiFetch<any>("/users/me", { method: "DELETE", body: JSON.stringify(data) }),

  // Discovery & Search
  searchProfessionals: (params: { category_slug?: string; city?: string; verified_only?: boolean; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params.category_slug) query.set("category_slug", params.category_slug);
    if (params.city) query.set("city", params.city);
    if (params.verified_only) query.set("verified_only", "true");
    if (params.page) query.set("page", params.page.toString());
    if (params.limit) query.set("limit", params.limit.toString());
    return apiFetch<any>(`/search/professionals?${query.toString()}`);
  },

  compareProfessionals: (professionalIds: string[]) => {
    return apiFetch<any>("/search/compare", {
      method: "POST",
      body: JSON.stringify({ professional_ids: professionalIds } satisfies ApiSchemas["CompareRequest"]),
    });
  },

  aiSearch: (query: string) => {
    return apiFetch<any>("/search/ai", {
      method: "POST",
      body: JSON.stringify({ query } satisfies ApiSchemas["NaturalLanguageSearchRequest"]),
    });
  },

  // Professionals & Portfolios
  getProfessional: (id: string) => apiFetch<any>(`/professionals/${id}`),
  getProfessionalReviews: (id: string) => apiFetch<any>(`/professionals/${id}/reviews`),
  getMediaAccessUrl: (assetId: string) => apiFetch<any>(`/media/${assetId}/url`),

  // Enquiries & Quotations
  createEnquiry: (data: ApiSchemas["EnquiryCreateRequest"]) =>
    apiFetch<any>("/enquiries", { method: "POST", body: JSON.stringify(data) }),
  getMyEnquiries: () => apiFetch<any[]>("/enquiries/me"),
  acceptQuotation: (quotationId: string) => apiFetch<any>(`/quotations/${quotationId}/accept`, { method: "POST" }),

  // Bookings, Payments & Reviews
  getMyBookings: () => apiFetch<any[]>("/bookings/me"),
  createPaymentOrder: (data: ApiSchemas["CreatePaymentOrderRequest"]) =>
    apiFetch<any>("/payments/create-order", { method: "POST", body: JSON.stringify(data) }),
  verifyPayment: (data: ApiSchemas["VerifyPaymentRequest"]) =>
    apiFetch<any>("/payments/verify", { method: "POST", body: JSON.stringify(data) }),
  getBookingPayments: (bookingId: string) =>
    apiFetch<any>(`/payments/bookings/${bookingId}`),
  refundPayment: (paymentId: string, data: ApiSchemas["RefundRequest"]) =>
    apiFetch<any>(`/payments/${paymentId}/refund`, { method: "POST", body: JSON.stringify(data) }),
  submitReview: (bookingId: string, review: ApiSchemas["ReviewCreateRequest"]) =>
    apiFetch<any>(`/bookings/${bookingId}/review`, { method: "POST", body: JSON.stringify(review) }),

  // Admin Moderation
  listModerationReviews: (params?: { moderation_status?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.moderation_status) query.set("moderation_status", params.moderation_status);
    if (params?.limit) query.set("limit", params.limit.toString());
    const suffix = query.toString();
    return apiFetch<any>(suffix ? `/admin/reviews?${suffix}` : "/admin/reviews");
  },
  moderateReview: (reviewId: string, data: ApiSchemas["ReviewModerationRequest"]) =>
    apiFetch<any>(`/admin/reviews/${reviewId}/moderate`, { method: "POST", body: JSON.stringify(data) }),
};
