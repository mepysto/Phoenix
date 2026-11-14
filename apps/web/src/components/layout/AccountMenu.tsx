"use client";

import Link from "next/link";
import { ChevronDown, Info, Languages, LogIn, LogOut, Settings, UserRound, UsersRound } from "lucide-react";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useAuthStore } from "@/store/authStore";
import { LANGUAGE_LABELS, useSettingsStore, type Language } from "@/store/settingsStore";
import { Dropdown } from "./Dropdown";

const ROW =
  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-200 transition-colors hover:bg-gray-800 hover:text-white";

/** Language choice; the interface serves seven languages */
export function LanguageSelect({ id }: { id: string }) {
  const { t } = useTranslation();
  const language = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);
  return (
    <div className="flex items-center gap-3 px-3 py-2 text-sm text-gray-200">
      <Languages className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
      <label htmlFor={id} className="flex-1">
        {t.ux.language}
      </label>
      <select
        id={id}
        value={language}
        onChange={(e) => setLanguage(e.target.value as Language)}
        className="cursor-pointer rounded-md border border-gray-700 bg-gray-950 px-2 py-1 text-sm text-gray-100"
      >
        {(Object.keys(LANGUAGE_LABELS) as Language[]).map((code) => (
          <option key={code} value={code}>
            {LANGUAGE_LABELS[code]}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Everything about the visitor in one place: sign-in, own activity, language, settings */
export function AccountItems({ idPrefix }: { idPrefix: string }) {
  const { t } = useTranslation();
  const { me, status, logout } = useAuthStore();
  const signedIn = status === "signed-in" && !!me;

  return (
    <div className="flex flex-col">
      {signedIn ? (
        <>
          <p className="truncate px-3 pb-2 pt-1.5 text-sm text-gray-400" title={me.email}>
            {me.email}
          </p>
          <Link href="/connect/mine" className={ROW}>
            <UsersRound className="h-4 w-4 text-gray-400" aria-hidden="true" />
            {t.ux.myActivity}
          </Link>
        </>
      ) : (
        <Link href="/login" className="btn-primary m-1.5">
          <LogIn className="h-4 w-4" aria-hidden="true" />
          {t.auth.signIn}
        </Link>
      )}
      <div className="my-1 border-t border-gray-800" />
      <LanguageSelect id={`${idPrefix}-language`} />
      <Link href="/settings" className={ROW}>
        <Settings className="h-4 w-4 text-gray-400" aria-hidden="true" />
        {t.common.settings}
      </Link>
      <Link href="/about" className={ROW}>
        <Info className="h-4 w-4 text-gray-400" aria-hidden="true" />
        {t.common.about}
      </Link>
      {signedIn && (
        <>
          <div className="my-1 border-t border-gray-800" />
          <button type="button" onClick={() => void logout()} className={ROW}>
            <LogOut className="h-4 w-4 text-gray-400" aria-hidden="true" />
            {t.auth.signOut}
          </button>
        </>
      )}
    </div>
  );
}

export function AccountMenu() {
  const { t } = useTranslation();
  const { me, status } = useAuthStore();
  const signedIn = status === "signed-in" && !!me;

  return (
    <Dropdown
      triggerLabel={signedIn ? `${t.auth.account}: ${me.email}` : t.auth.account}
      triggerClassName={(open) =>
        `flex items-center gap-1 rounded-full p-1 ps-1 transition-colors hover:bg-gray-800 ${open ? "bg-gray-800" : ""}`
      }
      trigger={
        <>
          {signedIn ? (
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-400/20 text-sm font-semibold uppercase text-primary-100 ring-1 ring-primary-400/40">
              {me.email.charAt(0)}
            </span>
          ) : (
            <span className="flex h-8 w-8 items-center justify-center rounded-full text-gray-300 ring-1 ring-gray-700">
              <UserRound className="h-4 w-4" aria-hidden="true" />
            </span>
          )}
          <ChevronDown className="h-3.5 w-3.5 text-gray-400" aria-hidden="true" />
        </>
      }
      panelClassName="w-72"
    >
      <AccountItems idPrefix="account-menu" />
    </Dropdown>
  );
}
