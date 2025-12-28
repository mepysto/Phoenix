"use client";

import Link from "next/link";
import {
  Globe,
  Database,
  Filter,
  RefreshCw,
  Code2,
  ExternalLink,
  ArrowLeft,
  Satellite,
  Shield,
  Users,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { useTranslation } from "@/lib/i18n/useTranslation";

const FEATURES = [
  {
    icon: Globe,
    title: "3D Digital Twin Globe",
    description:
      "Interactive 3D globe visualization powered by MapLibre GL JS for immersive disaster monitoring.",
  },
  {
    icon: RefreshCw,
    title: "Real-time Updates",
    description:
      "Automatic data synchronization every 5 minutes from multiple humanitarian data sources.",
  },
  {
    icon: Filter,
    title: "Smart Filtering",
    description:
      "Filter events by disaster type, severity level, and geographic region.",
  },
  {
    icon: Satellite,
    title: "Satellite Imagery",
    description:
      "Toggle between dark map and satellite imagery for detailed terrain analysis.",
  },
  {
    icon: Shield,
    title: "Severity Classification",
    description:
      "Events classified by severity (Critical, High, Medium, Low) for prioritized response.",
  },
  {
    icon: Users,
    title: "Open Participation",
    description:
      "Anyone can contribute to recovery planning and humanitarian efforts.",
  },
];

const DATA_SOURCES = [
  {
    name: "GDACS",
    fullName: "Global Disaster Alert and Coordination System",
    url: "https://www.gdacs.org",
  },
  {
    name: "Copernicus EMS",
    fullName: "Emergency Management Service",
    url: "https://emergency.copernicus.eu",
  },
  {
    name: "HDX",
    fullName: "Humanitarian Data Exchange",
    url: "https://data.humdata.org",
  },
  {
    name: "UNOSAT",
    fullName: "UN Satellite Centre",
    url: "https://unosat.org",
  },
];

const TECH_STACK = [
  {
    category: "Frontend",
    items: ["Next.js 15", "React 19", "TypeScript", "Tailwind CSS"],
  },
  { category: "3D Map", items: ["MapLibre GL JS", "deck.gl"] },
  { category: "Backend", items: ["FastAPI", "Python 3.12+"] },
  { category: "Database", items: ["PostgreSQL 16", "PostGIS", "TimescaleDB"] },
  { category: "Infrastructure", items: ["Docker", "Turborepo", "Redis"] },
];

export default function AboutPage() {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />

      <main className="flex-1 px-4 py-8 md:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.common.backToMap}
          </Link>

          <section className="mb-12 text-center">
            <div className="mb-4 flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-600">
                <Globe className="h-8 w-8 text-white" />
              </div>
            </div>
            <h1 className="mb-4 text-4xl font-bold text-white">Phoenix</h1>
            <p className="text-xl text-primary-400">{t.about.tagline}</p>
            <p className="mx-auto mt-4 max-w-2xl text-gray-400">
              {t.about.description}
            </p>
          </section>

          <section className="mb-12">
            <h2 className="mb-6 text-2xl font-bold text-white">
              {t.about.keyFeatures}
            </h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-lg border border-gray-800 bg-gray-900 p-5"
                >
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600/20">
                    <feature.icon className="h-5 w-5 text-primary-500" />
                  </div>
                  <h3 className="mb-2 font-semibold text-white">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-gray-400">{feature.description}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-12">
            <h2 className="mb-6 text-2xl font-bold text-white">
              {t.about.dataSources}
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              {DATA_SOURCES.map((source) => (
                <a
                  key={source.name}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900 p-4 hover:border-gray-700 hover:bg-gray-800/50 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <Database className="h-5 w-5 text-primary-500" />
                    <div>
                      <div className="font-medium text-white">
                        {source.name}
                      </div>
                      <div className="text-sm text-gray-400">
                        {source.fullName}
                      </div>
                    </div>
                  </div>
                  <ExternalLink className="h-4 w-4 text-gray-500" />
                </a>
              ))}
            </div>
          </section>

          <section className="mb-12">
            <h2 className="mb-6 text-2xl font-bold text-white">
              {t.about.techStack}
            </h2>
            <div className="overflow-hidden rounded-lg border border-gray-800">
              {TECH_STACK.map((stack, index) => (
                <div
                  key={stack.category}
                  className={`flex items-center gap-4 bg-gray-900 px-5 py-4 ${
                    index !== TECH_STACK.length - 1
                      ? "border-b border-gray-800"
                      : ""
                  }`}
                >
                  <div className="w-28 flex-shrink-0 text-sm font-medium text-gray-400">
                    {stack.category}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {stack.items.map((item) => (
                      <span
                        key={item}
                        className="rounded-full bg-gray-800 px-3 py-1 text-sm text-gray-300"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-12">
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center">
              <Code2 className="mx-auto mb-4 h-8 w-8 text-white" />
              <h2 className="mb-2 text-xl font-bold text-white">
                {t.about.openSource}
              </h2>
              <p className="mb-4 text-gray-400">{t.about.openSourceDesc}</p>
              <a
                href="https://github.com/your-org/phoenix"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 transition-colors"
              >
                <Code2 className="h-4 w-4" />
                {t.about.viewOnGithub}
              </a>
            </div>
          </section>

          <footer className="border-t border-gray-800 pt-6 text-center text-sm text-gray-500">
            <p>{t.about.footer}</p>
            <p className="mt-1">
              MIT License &copy; {new Date().getFullYear()} Phoenix Project
            </p>
          </footer>
        </div>
      </main>
    </div>
  );
}
