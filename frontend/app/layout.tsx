import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "MaanCamera — India's AI-Powered Photography & Videography Marketplace",
  description: "Discover, compare, and hire verified wedding, commercial, and portrait photographers and filmmakers across India.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#0d0e12] text-gray-100 antialiased selection:bg-[#FF5E1E] selection:text-white">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
