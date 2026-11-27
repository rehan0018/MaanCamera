/**
 * MaanCamera Frontend API Client
 * Wraps REST endpoints with generated OpenAPI schema types, cookie credentials, and CSRF protection.
 */

import type { components, paths } from "./api.generated";

export type ApiPaths = paths;
export type ApiSchemas = components["schemas"];

type StripApiPrefix<P extends string> = P extends `/api/v1${infer Rest}` ? Rest : never;
export type ApiEndpoint = StripApiPrefix<keyof paths & string>;

export const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000/api/v1";
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

export class ApiClientError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "API_ERROR") {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
  }
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
    credentials: "include",
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiClientError(
      errorBody?.error?.message || `API error: ${response.statusText}`,
      response.status,
      errorBody?.error?.code || "API_ERROR"
    );
  }

  return response.json();
}

export async function computeFileSha256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  if (typeof crypto !== "undefined" && crypto.subtle) {
    const digest = await crypto.subtle.digest("SHA-256", buffer);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
  return `${file.size.toString(16).padStart(16, "0")}0000000000000000`;
}

export async function uploadFileToPresignedUrl(uploadUrl: string, file: File): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
  if (!res.ok) {
    throw new Error(`Storage upload failed (${res.status})`);
  }
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
  getCategories: () => apiFetch<any[]>("/categories"),
  searchProfessionals: (params: { category_slug?: string; city?: string; verified_only?: boolean; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params.category_slug) query.set("category_slug", params.category_slug);
    if (params.city) query.set("city", params.city);
    if (params.verified_only) query.set("verified_only", "true");
    if (params.page) query.set("page", params.page.toString());
    if (params.limit) query.set("limit", params.limit.toString());
    const qs = query.toString();
    return apiFetch<any>(qs ? `/search/professionals?${qs}` : "/search/professionals");
  },
  compareProfessionals: (professionalIds: string[]) =>
    apiFetch<any>("/search/compare", {
      method: "POST",
      body: JSON.stringify({ professional_ids: professionalIds } satisfies ApiSchemas["CompareRequest"]),
    }),
  aiSearch: (query: string) =>
    apiFetch<any>("/search/ai", {
      method: "POST",
      body: JSON.stringify({ query } satisfies ApiSchemas["NaturalLanguageSearchRequest"]),
    }),
  summarizeReviews: (professionalId: string) =>
    apiFetch<any>("/ai/reviews/summarize", {
      method: "POST",
      body: JSON.stringify({ professional_id: professionalId } satisfies ApiSchemas["ReviewSummaryRequest"]),
    }),

  // Professionals & Portfolios
  getProfessional: (id: string) => apiFetch<any>(`/professionals/${id}`),
  getProfessionalReviews: (id: string) => apiFetch<any[]>(`/professionals/${id}/reviews`),
  getProfessionalPortfolios: (id: string) => apiFetch<any[]>(`/professionals/${id}/portfolios`),
  getMyProfile: () => apiFetch<any>("/professionals/me"),
  createProfessionalProfile: (
    data: Omit<ApiSchemas["ProfileCreateRequest"], "professional_type" | "years_experience" | "service_radius_km" | "travel_available"> &
      Partial<Pick<ApiSchemas["ProfileCreateRequest"], "professional_type" | "years_experience" | "service_radius_km" | "travel_available">>
  ) =>
    apiFetch<any>("/professionals", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        professional_type: data.professional_type ?? "individual",
        years_experience: data.years_experience ?? 1,
        service_radius_km: data.service_radius_km ?? 50,
        travel_available: data.travel_available ?? true,
      } satisfies ApiSchemas["ProfileCreateRequest"]),
    }),
  updateMyProfile: (data: ApiSchemas["ProfileUpdateRequest"]) =>
    apiFetch<any>("/professionals/me", { method: "PATCH", body: JSON.stringify(data) }),
  createMyService: (
    data: Omit<ApiSchemas["ServiceCreateRequest"], "pricing_type" | "starting_price_minor" | "currency_code"> &
      Partial<Pick<ApiSchemas["ServiceCreateRequest"], "pricing_type" | "starting_price_minor" | "currency_code">>
  ) =>
    apiFetch<any>("/professionals/me/services", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        pricing_type: data.pricing_type ?? "starting_from",
        starting_price_minor: data.starting_price_minor ?? 0,
        currency_code: data.currency_code ?? "INR",
      } satisfies ApiSchemas["ServiceCreateRequest"]),
    }),
  listMyVerifications: () => apiFetch<any[]>("/professionals/me/verifications"),
  submitVerification: (data: ApiSchemas["VerificationSubmitRequest"]) =>
    apiFetch<any>("/professionals/me/verifications", { method: "POST", body: JSON.stringify(data) }),
  getMyPortfolios: () => apiFetch<any[]>("/portfolios/me"),
  getPortfolioProjects: (portfolioId: string) => apiFetch<any[]>(`/portfolios/${portfolioId}/projects`),
  getProject: (projectId: string) => apiFetch<any>(`/projects/${projectId}`),
  createProject: (
    data: Omit<ApiSchemas["ProjectCreateRequest"], "tags" | "publication_status"> &
      Partial<Pick<ApiSchemas["ProjectCreateRequest"], "tags" | "publication_status">>
  ) =>
    apiFetch<any>("/projects", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        tags: data.tags ?? [],
        publication_status: data.publication_status ?? "draft",
      } satisfies ApiSchemas["ProjectCreateRequest"]),
    }),
  updateProject: (projectId: string, data: ApiSchemas["ProjectUpdateRequest"]) =>
    apiFetch<any>(`/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteProject: (projectId: string) =>
    apiFetch<any>(`/projects/${projectId}`, { method: "DELETE" }),
  getUploadUrl: (
    data: Omit<ApiSchemas["UploadUrlRequest"], "is_public"> & Partial<Pick<ApiSchemas["UploadUrlRequest"], "is_public">>
  ) =>
    apiFetch<any>("/media/upload-url", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        is_public: data.is_public ?? true,
      } satisfies ApiSchemas["UploadUrlRequest"]),
    }),
  completeMediaUpload: (
    data: Omit<ApiSchemas["CompleteMediaUploadRequest"], "media_type"> &
      Partial<Pick<ApiSchemas["CompleteMediaUploadRequest"], "media_type">>
  ) =>
    apiFetch<any>("/media/complete", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        media_type: data.media_type ?? "image",
      } satisfies ApiSchemas["CompleteMediaUploadRequest"]),
    }),
  getMediaAccessUrl: (assetId: string) => apiFetch<any>(`/media/${assetId}/url`),
  deleteMediaAsset: (assetId: string) =>
    apiFetch<any>(`/media/${assetId}`, { method: "DELETE" }),

  // Enquiries & Quotations
  createEnquiry: (
    data: Omit<ApiSchemas["EnquiryCreateRequest"], "duration_days" | "currency_code"> &
      Partial<Pick<ApiSchemas["EnquiryCreateRequest"], "duration_days" | "currency_code">>
  ) =>
    apiFetch<any>("/enquiries", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        duration_days: data.duration_days ?? 1,
        currency_code: data.currency_code ?? "INR",
      } satisfies ApiSchemas["EnquiryCreateRequest"]),
    }),
  getMyEnquiries: () => apiFetch<any[]>("/enquiries/me"),
  getEnquiry: (id: string) => apiFetch<any>(`/enquiries/${id}`),
  getEnquiryQuotations: (enquiryId: string) => apiFetch<any[]>(`/enquiries/${enquiryId}/quotations`),
  getMyQuotations: () => apiFetch<any[]>("/quotations/me"),
  createQuotation: (
    data: Omit<ApiSchemas["QuotationCreateRequest"], "currency_code" | "advance_amount_minor"> &
      Partial<Pick<ApiSchemas["QuotationCreateRequest"], "currency_code" | "advance_amount_minor">>
  ) =>
    apiFetch<any>("/quotations", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        currency_code: data.currency_code ?? "INR",
        advance_amount_minor: data.advance_amount_minor ?? 0,
      } satisfies ApiSchemas["QuotationCreateRequest"]),
    }),
  reviseQuotation: (
    quotationId: string,
    data: Omit<ApiSchemas["QuotationRevisionRequest"], "advance_amount_minor"> &
      Partial<Pick<ApiSchemas["QuotationRevisionRequest"], "advance_amount_minor">>
  ) =>
    apiFetch<any>(`/quotations/${quotationId}/revisions`, {
      method: "POST",
      body: JSON.stringify({
        ...data,
        advance_amount_minor: data.advance_amount_minor ?? 0,
      } satisfies ApiSchemas["QuotationRevisionRequest"]),
    }),
  acceptQuotation: (quotationId: string) =>
    apiFetch<any>(`/quotations/${quotationId}/accept`, { method: "POST" }),

  // Bookings, Payments & Reviews
  getMyBookings: () => apiFetch<any[]>("/bookings/me"),
  getBooking: (bookingId: string) => apiFetch<any>(`/bookings/${bookingId}`),
  updateBookingStatus: (bookingId: string, data: ApiSchemas["BookingStatusUpdate"]) =>
    apiFetch<any>(`/bookings/${bookingId}/status`, { method: "PATCH", body: JSON.stringify(data) }),
  completeBooking: (bookingId: string) =>
    apiFetch<any>(`/bookings/${bookingId}/complete`, { method: "POST" }),
  cancelBooking: (bookingId: string, data: ApiSchemas["BookingCancelRequest"]) =>
    apiFetch<any>(`/bookings/${bookingId}/cancel`, { method: "POST", body: JSON.stringify(data) }),
  createPaymentOrder: (
    data: Omit<ApiSchemas["CreatePaymentOrderRequest"], "currency_code" | "payment_type"> &
      Partial<Pick<ApiSchemas["CreatePaymentOrderRequest"], "currency_code" | "payment_type">>
  ) =>
    apiFetch<any>("/payments/create-order", {
      method: "POST",
      body: JSON.stringify({
        ...data,
        currency_code: data.currency_code ?? "INR",
        payment_type: data.payment_type ?? "advance",
      } satisfies ApiSchemas["CreatePaymentOrderRequest"]),
    }),
  verifyPayment: (data: ApiSchemas["VerifyPaymentRequest"]) =>
    apiFetch<any>("/payments/verify", { method: "POST", body: JSON.stringify(data) }),
  mockCapturePayment: (paymentId: string) =>
    apiFetch<any>(`/payments/${paymentId}/mock-capture`, { method: "POST" }),
  getBookingPayments: (bookingId: string) =>
    apiFetch<any>(`/payments/bookings/${bookingId}`),
  refundPayment: (paymentId: string, data: ApiSchemas["RefundRequest"]) =>
    apiFetch<any>(`/payments/${paymentId}/refund`, { method: "POST", body: JSON.stringify(data) }),
  submitReview: (bookingId: string, review: ApiSchemas["ReviewCreateRequest"]) =>
    apiFetch<any>(`/bookings/${bookingId}/review`, { method: "POST", body: JSON.stringify(review) }),
  reportReview: (reviewId: string, data: ApiSchemas["ContentReportRequest"]) =>
    apiFetch<any>(`/reviews/${reviewId}/report`, { method: "POST", body: JSON.stringify(data) }),

  // Admin Moderation & Trust
  listModerationReviews: (params?: { moderation_status?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.moderation_status) query.set("moderation_status", params.moderation_status);
    if (params?.limit) query.set("limit", params.limit.toString());
    const suffix = query.toString();
    return apiFetch<any[]>(suffix ? `/admin/reviews?${suffix}` : "/admin/reviews");
  },
  moderateReview: (reviewId: string, data: ApiSchemas["ReviewModerationRequest"]) =>
    apiFetch<any>(`/admin/reviews/${reviewId}/moderate`, { method: "POST", body: JSON.stringify(data) }),
  listAdminVerifications: (verificationStatus = "pending") =>
    apiFetch<any[]>(`/admin/verifications?verification_status=${encodeURIComponent(verificationStatus)}`),
  decideVerification: (verificationId: string, data: ApiSchemas["VerificationDecisionRequest"]) =>
    apiFetch<any>(`/admin/verifications/${verificationId}/decision`, { method: "POST", body: JSON.stringify(data) }),
  listAdminReports: (reportStatus = "pending") =>
    apiFetch<any[]>(`/admin/reports?report_status=${encodeURIComponent(reportStatus)}`),
  resolveReport: (reportId: string, data: ApiSchemas["ReportResolutionRequest"]) =>
    apiFetch<any>(`/admin/reports/${reportId}/resolve`, { method: "POST", body: JSON.stringify(data) }),
  reconcilePayments: (olderThanMinutes = 15) =>
    apiFetch<any>(`/payments/admin/reconcile?older_than_minutes=${olderThanMinutes}`, { method: "POST" }),
};
