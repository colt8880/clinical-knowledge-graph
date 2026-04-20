"use client";

import { Suspense, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchGuidelines } from "@/lib/api/client";
import GuidelineIndex from "@/components/GuidelineIndex";

export default function ExplorePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-slate-400">
          Loading...
        </div>
      }
    >
      <ExploreIndexContent />
    </Suspense>
  );
}

function ExploreIndexContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Backward compatibility: redirect old ?domains= params to /explore/all.
  useEffect(() => {
    const domains = searchParams.get("domains");
    if (domains !== null) {
      const qs = searchParams.toString();
      router.replace(`/explore/all${qs ? `?${qs}` : ""}`);
    }
  }, [searchParams, router]);

  const guidelinesQuery = useQuery({
    queryKey: ["guidelines"],
    queryFn: fetchGuidelines,
    staleTime: 5 * 60 * 1000,
  });

  if (guidelinesQuery.isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        Loading guidelines...
      </div>
    );
  }

  if (guidelinesQuery.error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500 text-sm">
        Error: {(guidelinesQuery.error as Error).message}
      </div>
    );
  }

  return <GuidelineIndex guidelines={guidelinesQuery.data ?? []} />;
}
