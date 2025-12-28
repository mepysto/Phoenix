"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Globe, Menu, Search, Settings, X } from "lucide-react";
import { useState, useCallback } from "react";
import { useTranslation } from "@/lib/i18n/useTranslation";

export function Header() {
  const router = useRouter();
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (searchQuery.trim()) {
        router.push(`/events?q=${encodeURIComponent(searchQuery.trim())}`);
      }
    },
    [searchQuery, router],
  );

  return (
    <>
      <header className="flex h-14 items-center justify-between border-b border-gray-800 bg-gray-900 px-4">
        <div className="flex items-center gap-4">
          <button
            className="lg:hidden p-2 hover:bg-gray-800 rounded"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
          <Link href="/" className="flex items-center gap-2">
            <Globe className="h-6 w-6 text-primary-500" />
            <span className="text-xl font-bold text-white">Phoenix</span>
          </Link>
        </div>

        <form
          onSubmit={handleSearch}
          className="hidden md:flex flex-1 max-w-md mx-8"
        >
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={t.common.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 pl-10 pr-4 text-sm text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </form>

        <div className="flex items-center gap-2">
          <nav className="hidden md:flex items-center gap-6 mr-4">
            <Link
              href="/events"
              className="text-sm text-gray-300 hover:text-white transition-colors"
            >
              {t.common.events}
            </Link>
            <Link
              href="/about"
              className="text-sm text-gray-300 hover:text-white transition-colors"
            >
              {t.common.about}
            </Link>
          </nav>
          <Link
            href="/settings"
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <Settings className="h-5 w-5 text-gray-400" />
          </Link>
        </div>
      </header>

      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-gray-800 bg-gray-900">
          <form onSubmit={handleSearch} className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder={t.common.searchPlaceholder}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 pl-10 pr-4 text-sm text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
          </form>
          <nav className="flex flex-col pb-4">
            <Link
              href="/"
              className="px-4 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t.common.home}
            </Link>
            <Link
              href="/events"
              className="px-4 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t.common.events}
            </Link>
            <Link
              href="/about"
              className="px-4 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t.common.about}
            </Link>
            <Link
              href="/settings"
              className="px-4 py-3 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t.common.settings}
            </Link>
          </nav>
        </div>
      )}
    </>
  );
}
