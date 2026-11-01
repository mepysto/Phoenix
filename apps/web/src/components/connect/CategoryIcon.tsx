import {
  Banknote,
  Bath,
  Droplet,
  GraduationCap,
  HeartPulse,
  Package,
  RadioTower,
  Shield,
  Tent,
  Truck,
  Wheat,
  Zap,
  type LucideIcon,
} from "lucide-react";
import type { Category } from "@/lib/api/community";

export const CATEGORY_ICONS: Record<Category, LucideIcon> = {
  shelter: Tent,
  water: Droplet,
  sanitation: Bath,
  food: Wheat,
  health: HeartPulse,
  power: Zap,
  communications: RadioTower,
  logistics: Truck,
  education: GraduationCap,
  protection: Shield,
  cash: Banknote,
  other: Package,
};

export function CategoryIcon({
  category,
  className = "h-4 w-4",
}: {
  category: string;
  className?: string;
}) {
  const Icon = CATEGORY_ICONS[category as Category] ?? Package;
  return <Icon className={className} aria-hidden="true" />;
}
