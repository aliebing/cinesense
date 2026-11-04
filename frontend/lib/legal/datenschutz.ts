import { AUTHORITY, OPERATOR, UPDATED, type LegalDoc, type LegalLocale } from "./site";

/**
 * Privacy notice of CineSense. It describes what the code actually does (checked 2026-11-05): chat and
 * search to OpenRouter (Claude Haiku; plot search embeddings by OpenAI), conversation only in server
 * memory, token counts logged without content, turn limits counted per IP in memory, the anonymous
 * taste id (localStorage "cinesense.user", created on the first rating, header X-CineSense-User) with 👍/👎 in the `feedback` table,
 * posters from Wikimedia and Movie of the Night, trailers in the youtube-nocookie player. Change it
 * together with any of these.
 */
export function datenschutz(locale: LegalLocale): LegalDoc {
  const who = `${OPERATOR.name}, ${OPERATOR.street}, ${OPERATOR.city}, ${OPERATOR.country[locale]}, ${OPERATOR.email}`;
  if (locale === "en") {
    return {
      title: "Privacy notice",
      bindingNote: "This is a translation; the German version (Datenschutzerklärung) is binding.",
      updated: UPDATED.en,
      sections: [
        { h: "1. Controller", body: [who] },
        {
          h: "2. Hosting",
          body: [
            "CineSense runs on a server rented from Contabo GmbH, Aschauer Straße 32a, 81549 Munich, Germany, which processes data on our behalf (Art. 28 GDPR).",
            "When you open a page, the server necessarily processes your IP address and the request to deliver it. No access logs with IP addresses are kept.",
          ],
        },
        {
          h: "3. Search and chat",
          body: [
            "To understand your wishes, your chat messages and search texts are sent with the conversation to OpenRouter, Inc. (USA, https://openrouter.ai/privacy), which passes them to the providers of the language models (currently Anthropic and, for the plot search, OpenAI, both USA). This is a transfer to a third country. Please do not enter personal data in the chat. Legal basis: Art. 6 (1) (f) GDPR (providing the search you are using).",
            "The conversation is kept only in the server's memory while it runs and is not stored. The server logs only how many tokens a turn used, not its content.",
            "To limit use, the server counts chat turns per IP address (per minute and per day). The counters are kept only in memory and reset daily and on every restart (Art. 6 (1) (f) GDPR, preventing misuse and costs).",
          ],
        },
        {
          h: "4. Taste profile (👍/👎)",
          body: [
            "CineSense works without an account. When you rate a film 👍 or 👎 for the first time, your browser creates a random id (localStorage entry „cinesense.user“) to remember your taste and sends it with later requests; without a rating there is no id. The server stores this id only with the films you rated 👍 or 👎; it is not linked to your name, IP address or any other data.",
            "The 👤 panel shows what was learned and deletes it with one click; deleting the browser's site data removes the id. Legal basis: Art. 6 (1) (f) GDPR and Section 25 (2) no. 2 TDDDG (a function you use).",
          ],
        },
        {
          h: "5. Content loaded from other servers",
          body: [
            "Some content is loaded by your browser directly from other servers, which therefore see your IP address (Art. 6 (1) (f) GDPR, showing posters and trailers):",
            {
              list: [
                "Posters and backdrops: Wikimedia Commons of the Wikimedia Foundation, Inc. (USA) and the image server of Movie of the Night (Streaming Availability API).",
                "Trailers: the YouTube player in privacy-enhanced mode (youtube-nocookie.com) of Google Ireland Limited, Gordon House, Barrow Street, Dublin 4, Ireland; data may be transferred to Google LLC (USA). It loads when a trailer is shown. See https://policies.google.com/privacy.",
              ],
            },
            "Streaming offers, film data and missing trailers are looked up by our server (Streaming Availability API, Wikidata, Wikipedia, YouTube Data API) with film titles only; no data about you is sent. Fonts are delivered by our own server.",
          ],
        },
        {
          h: "6. Cookies and tracking",
          body: ["CineSense sets no cookies and uses no tracking, analytics or advertising. Only the operator's technical view (/tech) uses a browser login."],
        },
        {
          h: "7. Your rights",
          body: [
            "You have the right to access (Art. 15 GDPR), rectification (Art. 16), erasure (Art. 17), restriction of processing (Art. 18), data portability (Art. 20) and to object to processing based on Art. 6 (1) (f) (Art. 21). Write to the address above.",
            `You can also complain to a supervisory authority, for example: ${AUTHORITY.name}, ${AUTHORITY.address}, ${AUTHORITY.url}.`,
          ],
        },
      ],
    };
  }
  return {
    title: "Datenschutzerklärung",
    updated: UPDATED.de,
    sections: [
      { h: "1. Verantwortlicher", body: [who] },
      {
        h: "2. Hosting",
        body: [
          "CineSense läuft auf einem gemieteten Server der Contabo GmbH, Aschauer Straße 32a, 81549 München, die Daten in unserem Auftrag verarbeitet (Art. 28 DSGVO).",
          "Beim Aufruf einer Seite verarbeitet der Server technisch notwendig Ihre IP-Adresse und die Anfrage, um die Seite auszuliefern. Zugriffsprotokolle mit IP-Adressen werden nicht gespeichert.",
        ],
      },
      {
        h: "3. Suche und Chat",
        body: [
          "Damit CineSense Ihre Wünsche versteht, werden Ihre Chat-Nachrichten und Suchtexte mit dem Gesprächsverlauf an die OpenRouter, Inc. (USA, https://openrouter.ai/privacy) übermittelt, die sie an die Anbieter der Sprachmodelle weitergibt (derzeit Anthropic und für die Inhaltssuche OpenAI, beide USA). Es handelt sich um eine Übermittlung in ein Drittland. Bitte geben Sie im Chat keine personenbezogenen Daten ein. Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (Bereitstellung der von Ihnen genutzten Suche).",
          "Der Gesprächsverlauf liegt nur im Arbeitsspeicher des laufenden Servers und wird nicht gespeichert. Protokolliert wird nur, wie viele Tokens eine Anfrage verbraucht hat, nicht ihr Inhalt.",
          "Um die Nutzung zu begrenzen, zählt der Server Chat-Anfragen je IP-Adresse (pro Minute und pro Tag). Die Zähler liegen nur im Arbeitsspeicher und werden täglich und bei jedem Neustart gelöscht (Art. 6 Abs. 1 lit. f DSGVO, Schutz vor Missbrauch und Kosten).",
        ],
      },
      {
        h: "4. Geschmacksprofil (👍/👎)",
        body: [
          "CineSense funktioniert ohne Konto. Wenn Sie zum ersten Mal einen Film mit 👍 oder 👎 bewerten, legt Ihr Browser eine zufällige Kennung an (localStorage-Eintrag „cinesense.user“), damit Ihr Geschmack erhalten bleibt, und sendet sie bei späteren Anfragen mit; ohne Bewertung gibt es keine Kennung. Der Server speichert diese Kennung nur zusammen mit den Filmen, die Sie mit 👍 oder 👎 bewertet haben; sie ist nicht mit Ihrem Namen, Ihrer IP-Adresse oder anderen Daten verknüpft.",
          "Das 👤-Fenster zeigt, was gelernt wurde, und löscht es mit einem Klick; das Löschen der Website-Daten im Browser entfernt die Kennung. Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO und § 25 Abs. 2 Nr. 2 TDDDG (eine von Ihnen genutzte Funktion).",
        ],
      },
      {
        h: "5. Inhalte von anderen Servern",
        body: [
          "Einige Inhalte lädt Ihr Browser direkt von anderen Servern, die dabei Ihre IP-Adresse erhalten (Art. 6 Abs. 1 lit. f DSGVO, Anzeige von Postern und Trailern):",
          {
            list: [
              "Poster und Hintergrundbilder: Wikimedia Commons der Wikimedia Foundation, Inc. (USA) und der Bildserver von Movie of the Night (Streaming Availability API).",
              "Trailer: der YouTube-Player im erweiterten Datenschutzmodus (youtube-nocookie.com) der Google Ireland Limited, Gordon House, Barrow Street, Dublin 4, Irland; dabei können Daten an die Google LLC (USA) übermittelt werden. Er wird geladen, wenn ein Trailer gezeigt wird. Siehe https://policies.google.com/privacy.",
            ],
          },
          "Streaming-Angebote, Filmdaten und fehlende Trailer fragt unser Server ab (Streaming Availability API, Wikidata, Wikipedia, YouTube Data API), und zwar nur mit Filmtiteln; Daten über Sie werden dabei nicht übermittelt. Schriften liefert unser eigener Server aus.",
        ],
      },
      {
        h: "6. Cookies und Tracking",
        body: ["CineSense setzt keine Cookies und nutzt kein Tracking, keine Reichweitenmessung und keine Werbung. Nur die technische Ansicht des Betreibers (/tech) verwendet eine Browser-Anmeldung."],
      },
      {
        h: "7. Ihre Rechte",
        body: [
          "Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch gegen Verarbeitungen nach Art. 6 Abs. 1 lit. f (Art. 21). Schreiben Sie dazu an die oben genannte Adresse.",
          `Sie können sich außerdem bei einer Datenschutz-Aufsichtsbehörde beschweren, zum Beispiel: ${AUTHORITY.name}, ${AUTHORITY.address}, ${AUTHORITY.url}.`,
        ],
      },
    ],
  };
}
