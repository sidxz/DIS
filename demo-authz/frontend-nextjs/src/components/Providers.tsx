"use client";

import { AuthzProvider } from "@sentinel-auth/nextjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { getAuthzClient } from "@/lib/authz-client";
import type { SentinelAuthz } from "@sentinel-auth/js";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
      }),
  );
  const clientRef = useRef<SentinelAuthz | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    clientRef.current = getAuthzClient();
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <AuthzProvider client={clientRef.current!}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </AuthzProvider>
  );
}
