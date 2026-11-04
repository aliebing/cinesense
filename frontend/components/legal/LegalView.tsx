"use client";

import { useState } from "react";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import LegalPage from "@/lib/legal/LegalPage";
import type { LegalDoc, LegalLocale } from "@/lib/legal/site";

/** A legal page in the cinema frame: German (binding) first, English one click away. */
export default function LegalView({ doc }: { doc: (locale: LegalLocale) => LegalDoc }) {
  const [locale, setLocale] = useState<LegalLocale>("de");
  const other: LegalLocale = locale === "de" ? "en" : "de";
  return (
    <CinemaFrame>
      <div className="mx-auto w-full max-w-3xl px-4 py-8 text-white/90">
        <button type="button" className="mb-4 text-sm underline underline-offset-4" onClick={() => setLocale(other)}>
          {other === "en" ? "English version" : "Deutsche Fassung"}
        </button>
        <LegalPage doc={doc(locale)} updatedLabel={locale === "de" ? "Stand" : "Last updated"} />
      </div>
    </CinemaFrame>
  );
}
