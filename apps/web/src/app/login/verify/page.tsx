"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { PhoenixMark } from "@/components/brand/PhoenixMark";
import { authAPI } from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useAuthStore } from "@/store/authStore";

function Verify() {
  const { t } = useTranslation();
  const router = useRouter();
  const token = useSearchParams().get("token");
  const setMe = useAuthStore((s) => s.setMe);
  const [failed, setFailed] = useState(false);
  // A link works once: never send it twice (React dev mode runs effects twice)
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current) return;
    sent.current = true;
    if (!token) {
      setFailed(true);
      return;
    }
    authAPI
      .verify(token)
      .then((r) => {
        setMe(r.user);
        router.replace(r.redirectPath || "/connect");
      })
      .catch(() => setFailed(true));
  }, [token, router, setMe]);

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-16">
      <div
        className="w-full max-w-sm text-center"
        role="status"
        aria-live="polite"
      >
        <PhoenixMark
          className={`mx-auto mb-6 h-12 w-12 text-gray-200 ${failed ? "" : "animate-pulse"}`}
        />
        {failed ? (
          <>
            <p className="text-lg font-medium text-white">{t.auth.failed}</p>
            <Link href="/login" className="btn-primary mt-6">
              {t.auth.again}
            </Link>
          </>
        ) : (
          <p className="text-gray-300">{t.auth.verifying}</p>
        )}
      </div>
    </main>
  );
}

export default function VerifyPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <Suspense>
        <Verify />
      </Suspense>
    </div>
  );
}
