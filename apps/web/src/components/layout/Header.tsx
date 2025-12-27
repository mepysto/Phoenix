"use client";

import { Globe, Menu, Search, Settings } from "lucide-react";
import { useState } from "react";

export function Header() {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-800 bg-gray-900 px-4">
      <div className="flex items-center gap-4">
        <button className="lg:hidden p-2 hover:bg-gray-800 rounded">
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <Globe className="h-6 w-6 text-primary-500" />
          <span className="text-xl font-bold text-white">Phoenix</span>
        </div>
      </div>

      <div className="hidden md:flex flex-1 max-w-md mx-8">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search events, locations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 pl-10 pr-4 text-sm text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <nav className="hidden md:flex items-center gap-6 mr-4">
          <a
            href="/events"
            className="text-sm text-gray-300 hover:text-white transition-colors"
          >
            Events
          </a>
          <a
            href="/about"
            className="text-sm text-gray-300 hover:text-white transition-colors"
          >
            About
          </a>
        </nav>
        <button className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <Settings className="h-5 w-5 text-gray-400" />
        </button>
      </div>
    </header>
  );
}
