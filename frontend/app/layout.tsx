import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Watari",
  description: "Personal AI Operating System dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
