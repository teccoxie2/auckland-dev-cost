import type { Metadata } from "next";
import { Geist_Mono, Noto_Sans_SC } from "next/font/google";
import AppHeader from "@/components/app_header";
import "./globals.css";

const noto = Noto_Sans_SC({
  variable: "--font-noto",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "奥克兰开发核算台",
  description: "点选奥克兰议会地址，按地块规划生成开发方案，并用公开报价源核算成本。",
};

export const maxDuration = 120;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN" className={`${noto.variable} ${geistMono.variable} h-full scroll-smooth antialiased`}>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <AppHeader />
        <div className="flex-1">{children}</div>
        <footer className="border-t border-[#e4dccb] px-4 py-4 text-center text-xs leading-5 text-[#7b8474] sm:px-8">
          地址与地籍来自 Auckland Council / LINZ 公开图层。金额只采用带链接的公开标价或官方费率，缺项不计价。
        </footer>
      </body>
    </html>
  );
}
