"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Inbox,
  Calendar,
  CreditCard,
  Star,
  ArrowRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  FileText,
  RotateCcw,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";

export default function CustomerDashboard() {
  const { user, loading: authLoading } = useAuth();
  const { notify } = useToast();

  const [activeTab, setActiveTab] = useState<"bookings" | "enquiries">("bookings");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [enquiries, setEnquiries] = useState<any[]>([]);

  // Active modals/drawers
  const [quoteEnquiry, setQuoteEnquiry] = useState<any | null>(null);
  const [enquiryQuotes, setEnquiryQuotes] = useState<any[]>([]);
  const [loadingQuotes, setLoadingQuotes] = useState(false);

  const [paymentBooking, setPaymentBooking] = useState<any | null>(null);
  const [paymentSummary, setPaymentSummary] = useState<any | null>(null);
  const [activeOrder, setActiveOrder] = useState<any | null>(null);
  const [paymentStage, setPaymentStage] = useState<"advance" | "balance">("advance");
  const [rzpPayId, setRzpPayId] = useState("");
  const [rzpSig, setRzpSig] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [paymentBusy, setPaymentBusy] = useState(false);

  const [reviewBooking, setReviewBooking] = useState<any | null>(null);
  const [ratingVal, setRatingVal] = useState(5);
  const [reviewText, setReviewText] = useState("");

  const [cancelBookingTarget, setCancelBookingTarget] = useState<any | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const loadDashboard = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [bRes, eRes] = await Promise.all([api.getMyBookings(), api.getMyEnquiries()]);
      setBookings(Array.isArray(bRes.data) ? bRes.data : []);
      setEnquiries(Array.isArray(eRes.data) ? eRes.data : []);
    } catch (err: any) {
      setError(err?.message || "Failed to load your bookings and enquiries.");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading && user) {
      loadDashboard();
    } else if (!authLoading && !user) {
      setLoading(false);
    }
  }, [authLoading, user, loadDashboard]);

  const openQuotations = async (enq: any) => {
    setQuoteEnquiry(enq);
    setLoadingQuotes(true);
    try {
      const res = await api.getEnquiryQuotations(enq.id);
      setEnquiryQuotes(Array.isArray(res.data) ? res.data : []);
    } catch (err: any) {
      notify(err?.message || "Failed to fetch quotations.", "error");
      setEnquiryQuotes([]);
    } finally {
      setLoadingQuotes(false);
    }
  };

  const handleAcceptQuotation = async (quotationId: string) => {
    try {
      await api.acceptQuotation(quotationId);
      notify("Quotation accepted and booking created.", "success");
      setQuoteEnquiry(null);
      setActiveTab("bookings");
      await loadDashboard();
    } catch (err: any) {
      notify(err?.message || "Unable to accept quotation.", "error");
    }
  };

  const openPaymentsDrawer = async (booking: any) => {
    setPaymentBooking(booking);
    setActiveOrder(null);
    setPaymentStage((booking.paid_amount_minor || 0) === 0 ? "advance" : "balance");
    try {
      const res = await api.getBookingPayments(booking.id);
      setPaymentSummary(res.data);
    } catch (err: any) {
      notify(err?.message || "Failed to load payment ledger.", "error");
    }
  };

  const handleCreateOrder = async () => {
    if (!paymentBooking) return;
    setPaymentBusy(true);
    try {
      const res = await api.createPaymentOrder({
        booking_id: paymentBooking.id,
        payment_type: paymentStage,
      });
      setActiveOrder(res.data);
      const sumRes = await api.getBookingPayments(paymentBooking.id);
      setPaymentSummary(sumRes.data);
      notify(`Order ${res.data.provider_order_id} created (${res.data.provider}).`, "success");
    } catch (err: any) {
      notify(err?.message || "Order creation failed.", "error");
    } finally {
      setPaymentBusy(false);
    }
  };

  const handleMockCapture = async (paymentId: string) => {
    if (!paymentBooking) return;
    setPaymentBusy(true);
    try {
      await api.mockCapturePayment(paymentId);
      notify("Dev mock payment captured cleanly!", "success");
      setActiveOrder(null);
      await loadDashboard();
      const sumRes = await api.getBookingPayments(paymentBooking.id);
      setPaymentSummary(sumRes.data);
    } catch (err: any) {
      notify(err?.message || "Mock capture failed.", "error");
    } finally {
      setPaymentBusy(false);
    }
  };

  const handleVerifySignature = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentBooking || !activeOrder) return;
    setPaymentBusy(true);
    try {
      await api.verifyPayment({
        payment_id: activeOrder.payment_id,
        provider_payment_id: rzpPayId.trim(),
        provider_signature: rzpSig.trim(),
      });
      notify("Payment verified and captured.", "success");
      setActiveOrder(null);
      setRzpPayId("");
      setRzpSig("");
      await loadDashboard();
      const sumRes = await api.getBookingPayments(paymentBooking.id);
      setPaymentSummary(sumRes.data);
    } catch (err: any) {
      notify(err?.message || "Signature verification failed.", "error");
    } finally {
      setPaymentBusy(false);
    }
  };

  const handleRefundPayment = async (paymentId: string, amountMinor: number) => {
    if (!paymentBooking) return;
    const reason = refundReason.trim() || "Customer requested booking cancellation refund";
    setPaymentBusy(true);
    try {
      await api.refundPayment(paymentId, { amount_minor: amountMinor, reason });
      notify("Refund processed and recorded in payment ledger.", "success");
      setRefundReason("");
      await loadDashboard();
      const sumRes = await api.getBookingPayments(paymentBooking.id);
      setPaymentSummary(sumRes.data);
    } catch (err: any) {
      notify(err?.message || "Refund failed.", "error");
    } finally {
      setPaymentBusy(false);
    }
  };

  const handleCompleteBooking = async (bookingId: string) => {
    try {
      await api.completeBooking(bookingId);
      notify("Booking marked completed & delivered!", "success");
      await loadDashboard();
    } catch (err: any) {
      notify(err?.message || "Could not complete booking.", "error");
    }
  };

  const handleCancelBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelBookingTarget) return;
    try {
      await api.cancelBooking(cancelBookingTarget.id, { cancellation_reason: cancelReason.trim() });
      notify("Booking cancelled cleanly.", "info");
      setCancelBookingTarget(null);
      setCancelReason("");
      await loadDashboard();
    } catch (err: any) {
      notify(err?.message || "Could not cancel booking.", "error");
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewBooking) return;
    try {
      await api.submitReview(reviewBooking.id, {
        overall_rating: ratingVal,
        work_quality_rating: ratingVal,
        communication_rating: ratingVal,
        punctuality_rating: ratingVal,
        value_rating: ratingVal,
        review_text: reviewText.trim(),
      });
      notify("Review submitted! It enters pending moderation before appearing publicly.", "success");
      setReviewBooking(null);
      setReviewText("");
      await loadDashboard();
    } catch (err: any) {
      notify(err?.message || "Failed to submit review.", "error");
    }
  };

  if (authLoading || loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-xs text-gray-400 flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading customer dashboard...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center space-y-4">
        <h1 className="text-2xl font-extrabold text-white">Sign in to view your Customer Dashboard</h1>
        <p className="text-xs text-gray-400">
          Track enquiries, compare quotations, pay booking deposits, and manage deliveries securely.
        </p>
        <Link
          href="/login?next=/customer/dashboard"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#FF5E1E] text-white text-xs font-semibold"
        >
          Sign In <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Customer Dashboard</h1>
          <p className="text-xs text-gray-400 mt-1">
            Signed in as <strong className="text-gray-200">{user.full_name}</strong> ({user.email})
          </p>
        </div>
        <Link
          href="/search"
          className="px-4 py-2.5 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold text-xs shadow-md transition-colors flex items-center gap-1.5"
        >
          <span>Find New Professional</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-white/10 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setActiveTab("bookings")}
          className={`pb-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "bookings"
              ? "border-[#FF5E1E] text-white"
              : "border-transparent text-gray-400 hover:text-white"
          }`}
        >
          <Calendar className="w-4 h-4" /> My Bookings ({bookings.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("enquiries")}
          className={`pb-3 px-2 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "enquiries"
              ? "border-[#FF5E1E] text-white"
              : "border-transparent text-gray-400 hover:text-white"
          }`}
        >
          <Inbox className="w-4 h-4" /> My Enquiries ({enquiries.length})
        </button>
      </div>

      {/* Bookings View */}
      {activeTab === "bookings" && (
        <div className="space-y-4">
          {bookings.length === 0 ? (
            <div className="p-10 rounded-2xl bg-[#14151b] border border-white/10 text-center space-y-3">
              <p className="text-sm font-bold text-white">No bookings yet</p>
              <p className="text-xs text-gray-400">
                Browse verified photographers, send an enquiry, and accept a quotation to create a booking.
              </p>
              <Link
                href="/search"
                className="inline-block px-4 py-2 rounded-xl bg-[#FF5E1E] text-white text-xs font-semibold"
              >
                Explore Professionals
              </Link>
            </div>
          ) : (
            bookings.map((b) => {
              const agreedInr = Math.round((b.agreed_amount_minor || 0) / 100);
              const paidInr = Math.round((b.paid_amount_minor || 0) / 100);
              const balanceMinor = Math.max(0, (b.agreed_amount_minor || 0) - (b.paid_amount_minor || 0));
              const balanceInr = Math.round(balanceMinor / 100);

              return (
                <div
                  key={b.id}
                  className="p-6 rounded-2xl bg-[#14151b] border border-white/10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6"
                >
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-white text-base">
                        {b.professional_name || `Studio ${b.professional_id.slice(0, 8)}`}
                      </span>
                      <span className="text-xs text-gray-400">({b.location})</span>
                      <span className="px-2 py-0.5 rounded bg-white/10 text-gray-200 text-[11px] font-semibold capitalize">
                        {b.booking_status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-gray-500" /> {b.shoot_date}
                      </span>
                      <span>•</span>
                      <span>Total: <strong className="text-white">₹{agreedInr.toLocaleString("en-IN")}</strong></span>
                      <span>•</span>
                      <span>Paid: <strong className="text-emerald-400">₹{paidInr.toLocaleString("en-IN")}</strong></span>
                      {balanceMinor > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-amber-400 font-medium">
                            Balance Due: ₹{balanceInr.toLocaleString("en-IN")}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openPaymentsDrawer(b)}
                      className="px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold flex items-center gap-1.5"
                    >
                      <CreditCard className="w-3.5 h-3.5 text-[#FF5E1E]" />
                      {balanceMinor > 0 && b.booking_status !== "cancelled" ? "Pay / Ledger" : "Payment Ledger"}
                    </button>

                    {(b.booking_status === "confirmed" || b.booking_status === "in_progress") && (
                      <button
                        type="button"
                        onClick={() => handleCompleteBooking(b.id)}
                        className="px-3.5 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Mark Completed
                      </button>
                    )}

                    {b.booking_status === "completed" && b.completion_status === "customer_accepted" && (
                      <button
                        type="button"
                        onClick={() => setReviewBooking(b)}
                        className="px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 text-xs font-semibold flex items-center gap-1.5"
                      >
                        <Star className="w-3.5 h-3.5 fill-current" /> Submit Verified Review
                      </button>
                    )}

                    {["pending_payment", "confirmed", "in_progress"].includes(b.booking_status) && (
                      <button
                        type="button"
                        onClick={() => setCancelBookingTarget(b)}
                        className="px-3.5 py-2 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 text-xs font-semibold flex items-center gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Cancel
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Enquiries View */}
      {activeTab === "enquiries" && (
        <div className="space-y-4">
          {enquiries.length === 0 ? (
            <div className="p-10 rounded-2xl bg-[#14151b] border border-white/10 text-center space-y-3">
              <p className="text-sm font-bold text-white">No enquiries sent yet</p>
              <p className="text-xs text-gray-400">
                Open a verified professional&apos;s profile to request a tailored quotation.
              </p>
            </div>
          ) : (
            enquiries.map((e) => (
              <div
                key={e.id}
                className="p-6 rounded-2xl bg-[#14151b] border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <h3 className="font-bold text-white text-sm">{e.title}</h3>
                  <p className="text-xs text-gray-400">
                    {e.category_name || "Photography"} • {e.city} • Date: {e.shoot_date || "Flexible"}
                    {e.budget_max_minor ? ` • Budget ₹${Math.round(e.budget_max_minor / 100).toLocaleString("en-IN")}` : ""}
                  </p>
                  <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[11px] font-medium">
                    {e.quotations_count ?? 0} Quotations Received • Status: {e.status}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => openQuotations(e)}
                  className="px-4 py-2 rounded-xl bg-[#FF5E1E] hover:bg-[#E04E15] text-white text-xs font-semibold flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" /> Review Quotations
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* Quotations Modal */}
      {quoteEnquiry && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6 rounded-2xl bg-[#14151b] border border-white/15 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Quotations for: {quoteEnquiry.title}</h2>
              <button type="button" onClick={() => setQuoteEnquiry(null)} className="text-xs text-gray-400 hover:text-white">
                Close
              </button>
            </div>
            {loadingQuotes ? (
              <div className="text-xs text-gray-400 flex items-center gap-2 py-6">
                <Loader2 className="w-4 h-4 animate-spin text-[#FF5E1E]" /> Loading quotations...
              </div>
            ) : enquiryQuotes.length === 0 ? (
              <p className="text-xs text-gray-400 py-4">No studios have sent a quotation for this enquiry yet.</p>
            ) : (
              <div className="space-y-3">
                {enquiryQuotes.map((q) => (
                  <div key={q.id} className="p-4 rounded-xl bg-[#1a1b24] border border-white/10 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm">
                        {q.professional_name || "Studio"} (v{q.version_number})
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white/10 text-gray-200 uppercase text-[10px]">
                        {q.status}
                      </span>
                    </div>
                    <p className="text-gray-300">{q.scope_of_work}</p>
                    <div className="flex flex-wrap items-center gap-4 text-gray-400">
                      <span>Total: <strong className="text-white">₹{Math.round(q.total_amount_minor / 100).toLocaleString("en-IN")}</strong></span>
                      <span>Advance: <strong className="text-[#FF5E1E]">₹{Math.round(q.advance_amount_minor / 100).toLocaleString("en-IN")}</strong></span>
                    </div>
                    {q.status === "sent" && (
                      <button
                        type="button"
                        onClick={() => handleAcceptQuotation(q.id)}
                        className="mt-2 px-4 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] text-white font-semibold"
                      >
                        Accept Quotation & Create Booking
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Checkout & Ledger Modal */}
      {paymentBooking && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6 rounded-2xl bg-[#14151b] border border-white/15 space-y-5 text-xs">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">
                Payments & Ledger — {paymentBooking.professional_name}
              </h2>
              <button type="button" onClick={() => setPaymentBooking(null)} className="text-xs text-gray-400 hover:text-white">
                Close
              </button>
            </div>

            {paymentSummary && (
              <div className="grid grid-cols-3 gap-3 p-4 rounded-xl bg-[#1a1b24] border border-white/10">
                <div>
                  <span className="text-gray-400 block">Agreed Total</span>
                  <strong className="text-white text-sm">₹{Math.round(paymentSummary.agreed_amount_minor / 100).toLocaleString("en-IN")}</strong>
                </div>
                <div>
                  <span className="text-gray-400 block">Captured Net</span>
                  <strong className="text-emerald-400 text-sm">₹{Math.round(paymentSummary.paid_amount_minor / 100).toLocaleString("en-IN")}</strong>
                </div>
                <div>
                  <span className="text-gray-400 block">Remaining</span>
                  <strong className="text-amber-400 text-sm">₹{Math.round(paymentSummary.remaining_amount_minor / 100).toLocaleString("en-IN")}</strong>
                </div>
              </div>
            )}

            {paymentBooking.booking_status !== "cancelled" &&
              (paymentSummary?.remaining_amount_minor ?? 1) > 0 && (
                <div className="p-4 rounded-xl bg-[#1a1b24] border border-white/10 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">Payment Stage:</span>
                      <select
                        value={paymentStage}
                        onChange={(e) => setPaymentStage(e.target.value as "advance" | "balance")}
                        className="bg-[#131418] border border-white/15 rounded-lg px-2.5 py-1.5 text-white"
                      >
                        <option value="advance">Advance Deposit</option>
                        <option value="balance">Remaining Balance</option>
                      </select>
                    </div>
                    <button
                      type="button"
                      disabled={paymentBusy}
                      onClick={handleCreateOrder}
                      className="px-4 py-2 rounded-lg bg-[#FF5E1E] hover:bg-[#E04E15] disabled:opacity-50 text-white font-semibold"
                    >
                      {paymentBusy ? "Processing..." : "Create Payment Order"}
                    </button>
                  </div>

                  {activeOrder && (
                    <div className="p-3 rounded-lg bg-black/40 border border-white/10 space-y-3">
                      <p className="text-gray-200">
                        Order <strong className="text-white">{activeOrder.provider_order_id}</strong> ({activeOrder.provider}) • Amount{" "}
                        <strong className="text-white">₹{Math.round(activeOrder.amount_minor / 100).toLocaleString("en-IN")}</strong>
                      </p>

                      {activeOrder.provider === "mock" ? (
                        <button
                          type="button"
                          disabled={paymentBusy}
                          onClick={() => handleMockCapture(activeOrder.payment_id)}
                          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                        >
                          Complete Dev Mock Payment
                        </button>
                      ) : (
                        <form onSubmit={handleVerifySignature} className="space-y-2">
                          <input
                            type="text"
                            required
                            placeholder="Gateway Payment ID (e.g. pay_...)"
                            value={rzpPayId}
                            onChange={(e) => setRzpPayId(e.target.value)}
                            className="w-full bg-[#131418] border border-white/15 rounded-lg px-3 py-2 text-white"
                          />
                          <input
                            type="text"
                            required
                            placeholder="Gateway Signature HMAC"
                            value={rzpSig}
                            onChange={(e) => setRzpSig(e.target.value)}
                            className="w-full bg-[#131418] border border-white/15 rounded-lg px-3 py-2 text-white"
                          />
                          <button type="submit" disabled={paymentBusy} className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold">
                            Verify & Capture Payment
                          </button>
                        </form>
                      )}
                    </div>
                  )}
                </div>
              )}

            {paymentSummary?.payments?.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-bold text-white">Payment Transactions</h3>
                {paymentSummary.payments.map((p: any) => (
                  <div key={p.id} className="p-3 rounded-lg bg-[#1a1b24] border border-white/5 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <span className="font-semibold text-white capitalize">{p.payment_type}</span> • {p.provider_order_id} •{" "}
                      <strong className="text-emerald-400">₹{Math.round(p.amount_minor / 100).toLocaleString("en-IN")}</strong> ({p.payment_status})
                    </div>
                    {p.payment_status === "captured" &&
                      (paymentBooking.booking_status === "cancelled" || paymentBooking.booking_status === "disputed") && (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Refund reason..."
                            value={refundReason}
                            onChange={(e) => setRefundReason(e.target.value)}
                            className="bg-[#131418] border border-white/15 rounded px-2 py-1 text-white"
                          />
                          <button
                            type="button"
                            onClick={() => handleRefundPayment(p.id, p.amount_minor)}
                            className="px-2.5 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1"
                          >
                            <RotateCcw className="w-3 h-3" /> Refund
                          </button>
                        </div>
                      )}
                  </div>
                ))}
              </div>
            )}

            {paymentSummary?.ledger_entries?.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-bold text-white">Append-Only Ledger Entries</h3>
                <div className="space-y-1">
                  {paymentSummary.ledger_entries.map((entry: any) => (
                    <div key={entry.id} className="p-2.5 rounded bg-black/30 flex items-center justify-between text-[11px] text-gray-300">
                      <span>{entry.entry_type} ({entry.direction}) — {entry.notes}</span>
                      <span className="font-semibold text-white">₹{Math.round(entry.amount_minor / 100).toLocaleString("en-IN")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cancel Booking Modal */}
      {cancelBookingTarget && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleCancelBooking} className="w-full max-w-md p-6 rounded-2xl bg-[#14151b] border border-white/15 space-y-4 text-xs">
            <h2 className="text-lg font-bold text-white">Cancel Booking</h2>
            <p className="text-gray-400">Provide a cancellation reason (minimum 5 characters).</p>
            <textarea
              required
              minLength={5}
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              className="w-full bg-[#1b1c23] border border-white/15 rounded-lg px-3 py-2 text-white"
            />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setCancelBookingTarget(null)} className="px-3 py-1.5 rounded-lg bg-white/10 text-white">
                Keep Booking
              </button>
              <button type="submit" className="px-4 py-1.5 rounded-lg bg-red-600 text-white font-semibold">
                Confirm Cancellation
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Verified Review Modal */}
      {reviewBooking && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleSubmitReview} className="w-full max-w-md p-6 rounded-2xl bg-[#14151b] border border-white/15 space-y-4 text-xs">
            <h2 className="text-lg font-bold text-white">Submit Verified Booking Review</h2>
            <p className="text-gray-400">
              Reviews enter admin moderation (<code className="text-amber-300">pending</code>) before updating public studio ratings.
            </p>
            <div className="space-y-1">
              <label className="font-semibold text-gray-300">Overall Rating (1–5)</label>
              <select
                value={ratingVal}
                onChange={(e) => setRatingVal(Number(e.target.value))}
                className="w-full bg-[#1b1c23] border border-white/15 rounded-lg px-3 py-2 text-white"
              >
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>{n} Stars</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="font-semibold text-gray-300">Review Feedback</label>
              <textarea
                required
                minLength={10}
                rows={4}
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="Share your honest experience about delivery quality, punctuality, and communication..."
                className="w-full bg-[#1b1c23] border border-white/15 rounded-lg px-3 py-2 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setReviewBooking(null)} className="px-3 py-1.5 rounded-lg bg-white/10 text-white">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 rounded-lg bg-[#FF5E1E] text-white font-semibold">
                Submit Review
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
