import { create } from "zustand";
import { APIError } from "@/lib/api/client";
import { authAPI, type Me } from "@/lib/api/community";

type Status = "unknown" | "signed-in" | "signed-out";

interface AuthState {
  me: Me | null;
  status: Status;
  refresh: () => Promise<void>;
  setMe: (me: Me) => void;
  logout: () => Promise<void>;
}

/** The signed-in user, loaded once from /auth/me (the session is a cookie). */
export const useAuthStore = create<AuthState>((set) => ({
  me: null,
  status: "unknown",
  refresh: async () => {
    try {
      set({ me: await authAPI.me(), status: "signed-in" });
    } catch (err) {
      // 401 is the normal signed-out answer; anything else, treat as signed out too
      if (!(err instanceof APIError) || err.statusCode === 401)
        set({ me: null, status: "signed-out" });
      else set({ me: null, status: "signed-out" });
    }
  },
  setMe: (me) => set({ me, status: "signed-in" }),
  logout: async () => {
    try {
      await authAPI.logout();
    } finally {
      set({ me: null, status: "signed-out" });
    }
  },
}));

/** Approved organisations the user belongs to (they can post needs for these) */
export function approvedOrgs(me: Me | null) {
  return (me?.memberships ?? [])
    .filter((m) => m.org.status === "approved")
    .map((m) => m.org);
}
