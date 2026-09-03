import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "RecoverAI — Autonomous Revenue Recovery Platform",
  description: "Autonomous payment recovery and intelligence platform for modern financial infrastructure. Detect, diagnose, govern, recover, and verify.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#070706] text-[#F5F0E8] antialiased min-h-screen">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
