import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northstar Contract Review Assistant",
  description: "AI-assisted contract clause review with human-in-the-loop verification.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <nav className="nav-bar">
          <Link href="/" className="nav-brand">
            Northstar
          </Link>
          <div className="nav-links">
            <Link href="/" className="nav-link">
              Review
            </Link>
            <Link href="/diagnostics" className="nav-link">
              Diagnostics
            </Link>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
