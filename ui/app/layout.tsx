import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Clinical Knowledge Graph",
  description:
    "Deterministic reasoning substrate for clinical guidelines — USPSTF 2022 statin primary prevention.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased h-screen flex flex-col`}
      >
        <header className="bg-slate-900 text-slate-100 px-5 py-3 flex items-center gap-6 shrink-0 sticky top-0 z-50">
          <h1 className="text-sm font-semibold tracking-tight">
            Clinical Knowledge Graph
          </h1>
          <nav className="flex gap-1 text-xs">
            <Link
              href="/explore"
              className="px-3 py-1.5 rounded hover:bg-slate-700 transition-colors"
            >
              Explore
            </Link>
            <Link
              href="/eval"
              className="px-3 py-1.5 rounded hover:bg-slate-700 transition-colors"
            >
              Eval
            </Link>
            <Link
              href="/interactions"
              className="px-3 py-1.5 rounded hover:bg-slate-700 transition-colors"
            >
              Interactions
            </Link>
          </nav>
          <span className="ml-auto text-xs text-slate-500">
            USPSTF 2022 Statin v0
          </span>
        </header>
        <Providers>
          <main className="flex-1 min-h-0">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
