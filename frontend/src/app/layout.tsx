import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AuthProvider } from "@/lib/auth-context";
import { Sidebar } from "@/components/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Project Odyssey | Clinical Intelligence",
  description: "Multimodal clinical intelligence system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <AuthProvider>
            <div className="flex h-screen overflow-hidden bg-slate-50/50">
              <Sidebar />
              <div className="flex-1 overflow-auto">{children}</div>
            </div>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
