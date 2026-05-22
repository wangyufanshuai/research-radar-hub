import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Research Radar Hub",
  description: "Local-first research intelligence for papers, repositories, courses, and daily reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="ml-64 flex-1">
            <div className="mx-auto max-w-7xl px-8 py-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
