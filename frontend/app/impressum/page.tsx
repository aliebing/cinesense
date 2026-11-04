"use client";

import LegalView from "@/components/legal/LegalView";
import { impressum } from "@/lib/legal/impressum";
import { APP_NOTE } from "@/lib/legal/site";

export default function ImpressumPage() {
  return <LegalView doc={(locale) => impressum(locale, "CineSense", APP_NOTE)} />;
}
