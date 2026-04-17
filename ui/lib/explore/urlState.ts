/**
 * URL state management for the Explore tab.
 *
 * New params: ?domains=uspstf,acc-aha,kdigo&focus=<node_id>
 * Legacy v0 params (?g=&r=&s=) log a console warning and load the default forest view.
 */

import { useSearchParams, useRouter } from "next/navigation";
import { useCallback, useMemo, useEffect, useRef } from "react";

/** All available domain keys (lowercase, hyphenated for URL). */
export const ALL_DOMAIN_KEYS = ["uspstf", "acc-aha", "kdigo"] as const;
export type DomainKey = (typeof ALL_DOMAIN_KEYS)[number];

/** Map URL keys to API domain labels. */
const URL_TO_API: Record<DomainKey, string> = {
  uspstf: "USPSTF",
  "acc-aha": "ACC_AHA",
  kdigo: "KDIGO",
};

/** Map API domain labels to URL keys. */
const API_TO_URL: Record<string, DomainKey> = {
  USPSTF: "uspstf",
  ACC_AHA: "acc-aha",
  KDIGO: "kdigo",
};

export function domainKeysToApiLabels(keys: DomainKey[]): string[] {
  return keys.map((k) => URL_TO_API[k]).filter(Boolean);
}

export function apiLabelToDomainKey(label: string): DomainKey | null {
  return API_TO_URL[label] ?? null;
}

const LEGACY_PARAMS = ["g", "r", "s"];
const LS_KEY = "explore-domains";

export interface ExploreUrlState {
  domains: DomainKey[];
  focus: string | null;
  setDomains: (domains: DomainKey[]) => void;
  setFocus: (nodeId: string | null) => void;
}

export function useExploreUrlState(): ExploreUrlState {
  const searchParams = useSearchParams();
  const router = useRouter();
  const hasWarnedLegacy = useRef(false);

  // Detect legacy v0 params.
  useEffect(() => {
    if (hasWarnedLegacy.current) return;
    const hasLegacy = LEGACY_PARAMS.some((p) => searchParams.has(p));
    if (hasLegacy) {
      console.warn(
        "[Explore] Legacy v0 URL params (?g=&r=&s=) detected. " +
          "Loading default forest view. Old column navigation is deprecated.",
      );
      hasWarnedLegacy.current = true;
    }
  }, [searchParams]);

  const domains = useMemo((): DomainKey[] => {
    // Legacy params → default all domains.
    if (LEGACY_PARAMS.some((p) => searchParams.has(p))) {
      return [...ALL_DOMAIN_KEYS];
    }

    const raw = searchParams.get("domains");
    if (raw === null) {
      // No param = all domains (try localStorage as usability nicety).
      if (typeof window !== "undefined") {
        try {
          const stored = localStorage.getItem(LS_KEY);
          if (stored) {
            const parsed = JSON.parse(stored) as string[];
            const valid = parsed.filter((d): d is DomainKey =>
              (ALL_DOMAIN_KEYS as readonly string[]).includes(d),
            );
            if (valid.length > 0) return valid;
          }
        } catch {
          // Ignore corrupted localStorage.
        }
      }
      return [...ALL_DOMAIN_KEYS];
    }

    if (raw.trim() === "") return [];

    return raw
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter((d): d is DomainKey =>
        (ALL_DOMAIN_KEYS as readonly string[]).includes(d),
      );
  }, [searchParams]);

  const focus = useMemo(
    () => searchParams.get("focus") ?? null,
    [searchParams],
  );

  const buildUrl = useCallback(
    (newDomains: DomainKey[], newFocus: string | null) => {
      const params = new URLSearchParams();
      // Only set domains if not all (default).
      if (
        newDomains.length !== ALL_DOMAIN_KEYS.length ||
        !ALL_DOMAIN_KEYS.every((d) => newDomains.includes(d))
      ) {
        params.set("domains", newDomains.join(","));
      }
      if (newFocus) {
        params.set("focus", newFocus);
      }
      const qs = params.toString();
      return `/explore${qs ? `?${qs}` : ""}`;
    },
    [],
  );

  const setDomains = useCallback(
    (newDomains: DomainKey[]) => {
      // Persist to localStorage.
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem(LS_KEY, JSON.stringify(newDomains));
        } catch {
          // Ignore.
        }
      }
      router.push(buildUrl(newDomains, focus));
    },
    [router, buildUrl, focus],
  );

  const setFocus = useCallback(
    (nodeId: string | null) => {
      router.push(buildUrl(domains, nodeId));
    },
    [router, buildUrl, domains],
  );

  return { domains, focus, setDomains, setFocus };
}
