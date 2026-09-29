"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap, LogOut } from "lucide-react";
import { clearToken } from "@/lib/auth";

export default function Navbar({ email }: { email?: string }) {
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="flex items-center gap-2 font-bold text-brand-600">
          <GraduationCap size={22} />
          Assignment Helper
        </Link>
        <div className="flex items-center gap-4">
          {email && (
            <span className="hidden text-sm text-slate-500 sm:block">{email}</span>
          )}
          <button onClick={handleLogout} className="btn-secondary text-xs" aria-label="Log out">
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
