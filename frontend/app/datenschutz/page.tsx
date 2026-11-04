"use client";

import LegalView from "@/components/legal/LegalView";
import { datenschutz } from "@/lib/legal/datenschutz";

export default function DatenschutzPage() {
  return <LegalView doc={datenschutz} />;
}
