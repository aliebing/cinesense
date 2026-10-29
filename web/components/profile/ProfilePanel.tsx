"use client";

import { useEffect, useState } from "react";
import { getProfile, type ProfileSummary, resetProfile } from "@/lib/api";

const title = (f: { title: string; year: number | null }) => (f.year ? `${f.title} (${f.year})` : f.title);

/** What CineSense learned from 👍/👎 in this browser, with a reset. */
export default function ProfilePanel({ onClose }: { onClose: () => void }) {
  const [profile, setProfile] = useState<ProfileSummary | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getProfile().then((r) => {
      if (cancelled) return;
      if (r.ok) setProfile(r.data);
      else setFailed(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const reset = async () => {
    const r = await resetProfile();
    if (r.ok) setProfile(r.data);
  };

  const empty = profile && profile.liked.length === 0 && profile.disliked.length === 0;
  return (
    <aside className="profile-panel" role="dialog" aria-label="Your profile">
      <header>
        <strong>Your taste</strong>
        <button type="button" aria-label="Close profile" onClick={onClose}>
          ×
        </button>
      </header>
      {failed && <p>Couldn&apos;t load your profile.</p>}
      {empty && <p className="profile-empty">Nothing learned yet — use 👍 and 👎 on a film’s stage page.</p>}
      {profile && !empty && (
        <>
          {profile.taste.length > 0 && (
            <section>
              <h3>What CineSense learned</h3>
              <p className="profile-taste">{profile.taste.join(" · ")}</p>
            </section>
          )}
          {profile.liked.length > 0 && (
            <section>
              <h3>👍 More like this</h3>
              <ul>
                {profile.liked.map((f) => (
                  <li key={f.id}>{title(f)}</li>
                ))}
              </ul>
            </section>
          )}
          {profile.disliked.length > 0 && (
            <section>
              <h3>👎 Not for me (hidden from results)</h3>
              <ul>
                {profile.disliked.map((f) => (
                  <li key={f.id}>{title(f)}</li>
                ))}
              </ul>
            </section>
          )}
          <button type="button" className="profile-reset" onClick={reset}>
            Reset profile
          </button>
          <p className="profile-note">Stored only under a random id from this browser — no account, no personal data.</p>
        </>
      )}
    </aside>
  );
}
