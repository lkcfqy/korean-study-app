import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "한걸음 · 一句一步学韩语",
  description: "通过韩中对话闯关学习韩语，SunHi 语音与跨设备云端进度。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
