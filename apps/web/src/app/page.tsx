import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { MapPageClient } from "./MapPageClient";

export default function HomePage() {
  return (
    <div className="flex h-screen flex-col">
      <Header />
      <div className="relative flex flex-1 overflow-hidden">
        <Sidebar />
        <MapPageClient />
      </div>
    </div>
  );
}
