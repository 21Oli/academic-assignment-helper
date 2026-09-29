"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

/** Root redirects to dashboard if logged in, otherwise to login. */
export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(isLoggedIn() ? "/dashboard" : "/login");
  }, [router]);
  return null;
}
