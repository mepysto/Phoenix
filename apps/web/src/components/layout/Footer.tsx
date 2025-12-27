import Link from "next/link";
import { ExternalLink } from "lucide-react";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-gray-800 bg-gray-900/50 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-700">
              <span className="text-sm font-bold text-white">P</span>
            </div>
            <span className="text-sm text-gray-400">
              &copy; {currentYear} Phoenix. Open Humanitarian Platform.
            </span>
          </div>

          <div className="flex items-center gap-6">
            <Link
              href="/events"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Events
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              GitHub
            </a>
            <a
              href="https://gdacs.org"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              GDACS
            </a>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-800">
          <p className="text-center text-xs text-gray-500">
            Data sources: GDACS, Copernicus EMS, HDX, UNOSAT
          </p>
        </div>
      </div>
    </footer>
  );
}
