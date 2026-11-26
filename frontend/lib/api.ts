/**
 * MaanCamera Frontend API Client
 * Wraps REST endpoints with typed requests and cookie credentials.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000/api/v1";

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta: {
    request_id: string;
    timestamp: string;
  };
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include", // Send HTTP-only session cookies
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody?.error?.message || `API error: ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  // Authentication
  login: (data: { email: string; password: string }) =>
    apiFetch<any>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  register: (data: { full_name: string; email: string; phone?: string; password: string; role?: string }) =>
    apiFetch<any>("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  logout: () =>
    apiFetch<any>("/auth/logout", { method: "POST" }),
  getCurrentUser: () =>
    apiFetch<any>("/auth/me"),

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
      body: JSON.stringify({ professional_ids: professionalIds }),
    });
  },

  aiSearch: (query: string) => {
    return apiFetch<any>("/search/ai", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },

  // Professionals
  getProfessional: (id: string) => apiFetch<any>(`/professionals/${id}`),
  getProfessionalReviews: (id: string) => apiFetch<any>(`/professionals/${id}/reviews`),

  // Enquiries & Quotations
  createEnquiry: (data: any) => apiFetch<any>("/enquiries", { method: "POST", body: JSON.stringify(data) }),
  getMyEnquiries: () => apiFetch<any[]>("/enquiries/me"),
  acceptQuotation: (quotationId: string) => apiFetch<any>(`/quotations/${quotationId}/accept`, { method: "POST" }),

  // Bookings & Payments
  getMyBookings: () => apiFetch<any[]>("/bookings/me"),
  createPaymentOrder: (data: any) => apiFetch<any>("/payments/create-order", { method: "POST", body: JSON.stringify(data) }),
  verifyPayment: (data: any) => apiFetch<any>("/payments/verify", { method: "POST", body: JSON.stringify(data) }),
  submitReview: (bookingId: string, review: any) => apiFetch<any>(`/bookings/${bookingId}/review`, { method: "POST", body: JSON.stringify(review) }),
};
