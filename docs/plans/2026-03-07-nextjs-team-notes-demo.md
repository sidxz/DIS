# Next.js Team Notes Demo (AuthZ Mode) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Next.js App Router frontend for the existing team-notes demo that proves authz mode works with a Next.js + separate FastAPI backend architecture (mirroring docu-store).

**Architecture:** Client-side only auth (Option A). Next.js frontend at `demo-authz/frontend-nextjs/` talks directly to the existing Python backend at `:9200`. All auth state lives in `localStorage` via `SentinelAuthz` client. Pages are protected client-side with `AuthzGuard`. No Edge Middleware, no Next.js API routes — this mirrors how docu-store will actually integrate.

**Tech Stack:** Next.js 15, React 19, TailwindCSS v4, @tanstack/react-query v5, @sentinel-auth/nextjs (client re-exports from @sentinel-auth/react)

---

## Pre-requisite: Understand the existing React demo

The React frontend at `demo-authz/frontend/` has these pages and components that we are porting 1:1:

- **Pages:** Login, AuthCallback, NoteList, NoteDetail, Export
- **Components:** Layout (nav bar), NoteCard, ShareDialog, RoleBadge
- **API layer:** `client.ts` (SentinelAuthz instance + apiFetch), `notes.ts` (typed CRUD functions)
- **Auth flow:** AuthzProvider wraps app → AuthzGuard shows Login for unauthenticated → login("google") redirects to IdP → AuthzCallback handles response → protected routes render

The Next.js version replaces react-router-dom with file-based routing and `next/navigation` hooks. All components using React hooks need `'use client'`.

---

### Task 1: Add AuthzCallback export to @sentinel-auth/nextjs SDK

**Files:**
- Modify: `sdks/nextjs/src/index.ts`

**Step 1: Add the missing AuthzCallback export**

The Next.js SDK re-exports authz components from `@sentinel-auth/react` but is missing `AuthzCallback` and its types. Add them:

```typescript
// In the authz-mode exports section, add:
export {
  AuthzProvider,
  useAuthz,
  useAuthzUser,
  useAuthzHasRole,
  useAuthzFetch,
  AuthzGuard,
  AuthzCallback,    // ADD
} from '@sentinel-auth/react'

export type {
  AuthzProviderProps,
  AuthzContextValue,
  AuthzGuardProps,
  AuthzCallbackProps,           // ADD
  AuthzWorkspaceSelectorProps,  // ADD
  SentinelAuthzConfig,
  AuthzTokenStore,
  AuthzResolveResponse,
} from '@sentinel-auth/react'
```

**Step 2: Build the SDK**

Run: `cd sdks/nextjs && npm run build`
Expected: Clean build, no errors

**Step 3: Commit**

```bash
git add sdks/nextjs/src/index.ts
git commit -m "feat(nextjs-sdk): export AuthzCallback and AuthzCallbackProps"
```

---

### Task 2: Scaffold Next.js project

**Files:**
- Create: `demo-authz/frontend-nextjs/package.json`
- Create: `demo-authz/frontend-nextjs/next.config.ts`
- Create: `demo-authz/frontend-nextjs/tsconfig.json`
- Create: `demo-authz/frontend-nextjs/postcss.config.mjs`
- Create: `demo-authz/frontend-nextjs/.env.local`
- Create: `demo-authz/frontend-nextjs/src/app/globals.css`

**Step 1: Create package.json**

```json
{
  "name": "demo-authz-frontend-nextjs",
  "private": true,
  "scripts": {
    "dev": "next dev -p 5174",
    "build": "next build",
    "start": "next start -p 5174"
  },
  "dependencies": {
    "next": "^15.3.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.90.21",
    "@sentinel-auth/js": "file:../../sdks/js",
    "@sentinel-auth/react": "file:../../sdks/react",
    "@sentinel-auth/nextjs": "file:../../sdks/nextjs"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.2.1",
    "tailwindcss": "^4.2.1",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.5.0"
  }
}
```

**Step 2: Create next.config.ts**

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {}

export default nextConfig
```

**Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**Step 4: Create postcss.config.mjs**

```javascript
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

**Step 5: Create .env.local**

```
NEXT_PUBLIC_SENTINEL_URL=http://localhost:9003
NEXT_PUBLIC_BACKEND_URL=http://localhost:9200
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
```

Note: Copy the actual Google client ID from `demo-authz/frontend/.env` if it exists.

**Step 6: Create src/app/globals.css**

```css
@import "tailwindcss";
```

**Step 7: Install dependencies**

Run: `cd demo-authz/frontend-nextjs && npm install`
Expected: Clean install, node_modules created

**Step 8: Commit**

```bash
git add demo-authz/frontend-nextjs/
git commit -m "chore: scaffold Next.js team-notes demo project"
```

---

### Task 3: Create Providers wrapper and root layout

**Files:**
- Create: `demo-authz/frontend-nextjs/src/lib/authz-client.ts`
- Create: `demo-authz/frontend-nextjs/src/components/Providers.tsx`
- Create: `demo-authz/frontend-nextjs/src/app/layout.tsx`

**Step 1: Create the shared SentinelAuthz client**

`src/lib/authz-client.ts` — mirrors React demo's `api/client.ts`:

```typescript
import { SentinelAuthz, IdpConfigs } from "@sentinel-auth/js";

const SENTINEL_URL =
  process.env.NEXT_PUBLIC_SENTINEL_URL || "http://localhost:9003";
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:9200";
const GOOGLE_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export const authzClient = new SentinelAuthz({
  sentinelUrl: SENTINEL_URL,
  idps: {
    google: IdpConfigs.google(GOOGLE_CLIENT_ID),
  },
});

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  return authzClient.fetchJson<T>(`${BACKEND_URL}${path}`, options);
}
```

**Step 2: Create the Providers client component**

`src/components/Providers.tsx` — wraps AuthzProvider + QueryClientProvider:

```tsx
"use client";

import { AuthzProvider } from "@sentinel-auth/nextjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { authzClient } from "@/lib/authz-client";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
      }),
  );

  return (
    <AuthzProvider client={authzClient}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </AuthzProvider>
  );
}
```

**Step 3: Create root layout**

`src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Team Notes — AuthZ Mode (Next.js)",
  description: "Sentinel AuthZ demo with Next.js App Router",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950 text-zinc-100 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

**Step 4: Verify it compiles**

Run: `cd demo-authz/frontend-nextjs && npx next build`
Expected: Build succeeds (may warn about no pages — that's fine)

**Step 5: Commit**

```bash
git add demo-authz/frontend-nextjs/src/
git commit -m "feat: add Providers, authz client, and root layout"
```

---

### Task 4: Create API layer

**Files:**
- Create: `demo-authz/frontend-nextjs/src/lib/notes.ts`

**Step 1: Create notes API functions**

Port `demo-authz/frontend/src/api/notes.ts` — identical logic, different import path:

```typescript
import { apiFetch } from "./authz-client";

export interface Note {
  id: string;
  title: string;
  content: string;
  workspace_id: string;
  owner_id: string;
  owner_name: string;
  created_at: string;
  updated_at: string;
}

export function fetchNotes(): Promise<Note[]> {
  return apiFetch("/notes");
}

export function fetchNote(id: string): Promise<Note> {
  return apiFetch(`/notes/${id}`);
}

export function createNote(title: string, content: string): Promise<Note> {
  return apiFetch("/notes", {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });
}

export function updateNote(
  id: string,
  data: { title?: string; content?: string },
): Promise<Note> {
  return apiFetch(`/notes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteNote(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/notes/${id}`, { method: "DELETE" });
}

export function shareNote(
  noteId: string,
  userId: string,
  permission: string,
): Promise<{ ok: boolean }> {
  return apiFetch(`/notes/${noteId}/share`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, permission }),
  });
}

export function exportNotes(): Promise<{
  format: string;
  count: number;
  notes: Note[];
}> {
  return apiFetch("/notes/export");
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/lib/notes.ts
git commit -m "feat: add notes API layer"
```

---

### Task 5: Create shared components

**Files:**
- Create: `demo-authz/frontend-nextjs/src/components/RoleBadge.tsx`
- Create: `demo-authz/frontend-nextjs/src/components/NoteCard.tsx`
- Create: `demo-authz/frontend-nextjs/src/components/ShareDialog.tsx`

**Step 1: Create RoleBadge**

This is a pure presentational component — no hooks, so no `'use client'` needed (but it will be used inside client components, so it's fine either way):

```tsx
const ROLE_COLORS: Record<string, string> = {
  owner: "bg-purple-500/20 text-purple-400",
  admin: "bg-red-500/20 text-red-400",
  editor: "bg-blue-500/20 text-blue-400",
  viewer: "bg-zinc-500/20 text-zinc-400",
};

export function RoleBadge({ role }: { role: string }) {
  const color = ROLE_COLORS[role] ?? ROLE_COLORS.viewer;
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${color}`}
    >
      {role}
    </span>
  );
}
```

**Step 2: Create NoteCard**

Uses `next/link` instead of react-router-dom's `Link`:

```tsx
import Link from "next/link";
import type { Note } from "@/lib/notes";

export function NoteCard({
  note,
  isOwner,
}: {
  note: Note;
  isOwner: boolean;
}) {
  return (
    <Link
      href={`/notes/${note.id}`}
      className="block rounded-lg border border-zinc-800 bg-zinc-900 p-4 transition hover:border-zinc-700"
    >
      <div className="mb-2 flex items-start justify-between">
        <h3 className="font-medium text-zinc-100">{note.title}</h3>
        {isOwner && (
          <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-400">
            yours
          </span>
        )}
      </div>
      <p className="mb-3 line-clamp-2 text-sm text-zinc-400">{note.content}</p>
      <div className="text-xs text-zinc-600">
        by {note.owner_name} &middot;{" "}
        {new Date(note.created_at).toLocaleDateString()}
      </div>
    </Link>
  );
}
```

**Step 3: Create ShareDialog**

Needs `'use client'` because it uses `useState`:

```tsx
"use client";

import { useState } from "react";
import { shareNote } from "@/lib/notes";

export function ShareDialog({
  noteId,
  onClose,
}: {
  noteId: string;
  onClose: () => void;
}) {
  const [userId, setUserId] = useState("");
  const [permission, setPermission] = useState("view");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleShare() {
    setError("");
    setLoading(true);
    try {
      await shareNote(noteId, userId, permission);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Share failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-zinc-100">
          Share Note
        </h2>

        {success ? (
          <div className="space-y-4">
            <p className="text-sm text-emerald-400">Shared successfully!</p>
            <button
              onClick={onClose}
              className="w-full rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-zinc-400">
                User ID
              </label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="UUID of the user to share with"
                className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-zinc-400">
                Permission
              </label>
              <select
                value={permission}
                onChange={(e) => setPermission(e.target.value)}
                className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none"
              >
                <option value="view">View</option>
                <option value="edit">Edit</option>
              </select>
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={handleShare}
                disabled={!userId || loading}
                className="flex-1 rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {loading ? "Sharing..." : "Share"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add demo-authz/frontend-nextjs/src/components/
git commit -m "feat: add RoleBadge, NoteCard, and ShareDialog components"
```

---

### Task 6: Create nav layout for authenticated pages

**Files:**
- Create: `demo-authz/frontend-nextjs/src/components/AppShell.tsx`

**Step 1: Create the nav/layout component**

This replaces the React demo's `Layout` component. Uses `next/link` and `usePathname()` instead of react-router-dom:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthz, useAuthzUser } from "@sentinel-auth/nextjs";
import { RoleBadge } from "./RoleBadge";

const navLinks = [
  { href: "/notes", label: "Notes" },
  { href: "/notes/export", label: "Export" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const user = useAuthzUser();
  const { logout } = useAuthz();
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-3">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/notes" className="text-lg font-semibold text-zinc-100">
              Team Notes
            </Link>
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
              authz · next.js
            </span>
            <div className="flex gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded px-3 py-1.5 text-sm transition ${
                    pathname === link.href
                      ? "bg-zinc-700 text-zinc-100"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm text-zinc-300">{user.name}</div>
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <span>{user.workspaceSlug}</span>
                <RoleBadge role={user.workspaceRole} />
              </div>
            </div>
            <button
              onClick={() => {
                logout();
                window.location.href = "/";
              }}
              className="rounded bg-zinc-800 px-3 py-1.5 text-xs text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-4xl px-6 py-8">{children}</main>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/components/AppShell.tsx
git commit -m "feat: add AppShell nav layout component"
```

---

### Task 7: Create Login page

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/login/page.tsx`

**Step 1: Create the login page**

```tsx
"use client";

import { useAuthz } from "@sentinel-auth/nextjs";

export default function LoginPage() {
  const { login } = useAuthz();

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="w-full max-w-sm space-y-6 text-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Team Notes</h1>
          <p className="mt-1 text-sm text-zinc-500">
            AuthZ Mode Demo &mdash; Next.js App Router
          </p>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <p className="mb-4 text-sm text-zinc-400">
            Sign in to manage workspace notes. This Next.js demo uses the same
            Python backend as the React version, proving AuthZ mode works with
            a separate API server architecture.
          </p>
          <button
            onClick={() => login("google")}
            className="flex w-full items-center justify-center gap-2 rounded bg-white px-4 py-2.5 text-sm font-medium text-zinc-900 transition hover:bg-zinc-200"
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </button>
        </div>

        <div className="space-y-2 text-xs text-zinc-600">
          <p>
            Powered by{" "}
            <a
              href="https://docs.sentinel-auth.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-500 underline hover:text-zinc-400"
            >
              Sentinel Auth
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/login/
git commit -m "feat: add login page"
```

---

### Task 8: Create Auth Callback page

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/auth/callback/page.tsx`

**Step 1: Create the callback page**

This uses `AuthzCallback` from the Next.js SDK and `useRouter` for navigation:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { AuthzCallback } from "@sentinel-auth/nextjs";
import { RoleBadge } from "@/components/RoleBadge";

export default function AuthCallbackPage() {
  const router = useRouter();

  return (
    <AuthzCallback
      onSuccess={() => router.replace("/notes")}
      loadingComponent={
        <div className="flex h-screen items-center justify-center bg-zinc-950">
          <div className="text-center">
            <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-300" />
            <p className="text-sm text-zinc-500">Signing you in...</p>
          </div>
        </div>
      }
      errorComponent={(error) => (
        <div className="flex h-screen items-center justify-center bg-zinc-950">
          <div className="max-w-sm text-center">
            <p className="mb-4 text-sm text-red-400">{error.message}</p>
            <a
              href="/"
              className="text-sm text-zinc-400 underline hover:text-zinc-200"
            >
              Back to login
            </a>
          </div>
        </div>
      )}
      workspaceSelector={({ workspaces, onSelect, isLoading }) => (
        <div className="flex h-screen items-center justify-center bg-zinc-950">
          <div className="w-full max-w-sm">
            <h2 className="mb-4 text-center text-lg font-semibold text-zinc-100">
              Select Workspace
            </h2>
            <div className="space-y-2">
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => onSelect(ws.id)}
                  disabled={isLoading}
                  className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-left transition hover:border-zinc-700 disabled:opacity-50"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-zinc-100">{ws.name}</div>
                      <div className="text-xs text-zinc-500">{ws.slug}</div>
                    </div>
                    <RoleBadge role={ws.role} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    />
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/auth/
git commit -m "feat: add auth callback page"
```

---

### Task 9: Create protected notes layout with AuthzGuard

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/notes/layout.tsx`

**Step 1: Create the notes layout**

This wraps all `/notes/*` routes with `AuthzGuard` + the `AppShell` nav:

```tsx
"use client";

import { AuthzGuard } from "@sentinel-auth/nextjs";
import { AppShell } from "@/components/AppShell";

export default function NotesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthzGuard
      fallback={
        <meta httpEquiv="refresh" content="0;url=/login" />
      }
      loading={
        <div className="flex h-screen items-center justify-center bg-zinc-950">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-300" />
        </div>
      }
    >
      <AppShell>{children}</AppShell>
    </AuthzGuard>
  );
}
```

Note: The `fallback` uses a meta refresh redirect to `/login` since we can't use `useRouter` inside the fallback (it renders when there's no auth context). An alternative is rendering the `<LoginPage>` inline (like the React demo does), but redirecting is cleaner for Next.js.

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/notes/layout.tsx
git commit -m "feat: add AuthzGuard-protected notes layout"
```

---

### Task 10: Create Notes list page

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/notes/page.tsx`

**Step 1: Create the notes list page**

Port from React demo's `NoteList.tsx`, replacing react-router-dom with next/navigation:

```tsx
"use client";

import { useAuthzUser } from "@sentinel-auth/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createNote, fetchNotes } from "@/lib/notes";
import { NoteCard } from "@/components/NoteCard";

export default function NotesPage() {
  const user = useAuthzUser();
  const queryClient = useQueryClient();
  const canCreate = ["editor", "admin", "owner"].includes(user.workspaceRole);

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ["notes"],
    queryFn: fetchNotes,
  });

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const mutation = useMutation({
    mutationFn: () => createNote(title, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setTitle("");
      setContent("");
      setShowForm(false);
    },
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-zinc-100">Notes</h1>
        {canCreate && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
          >
            {showForm ? "Cancel" : "New Note"}
          </button>
        )}
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mb-3 w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
          />
          <textarea
            placeholder="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            className="mb-3 w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
          />
          <button
            onClick={() => mutation.mutate()}
            disabled={!title || mutation.isPending}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {mutation.isPending ? "Creating..." : "Create"}
          </button>
          {mutation.isError && (
            <p className="mt-2 text-sm text-red-400">
              {mutation.error.message}
            </p>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-300" />
        </div>
      ) : notes.length === 0 ? (
        <p className="py-12 text-center text-sm text-zinc-500">
          No notes yet.{" "}
          {canCreate
            ? "Create one to get started."
            : "Ask an editor to create one."}
        </p>
      ) : (
        <div className="grid gap-3">
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              isOwner={note.owner_id === user.userId}
            />
          ))}
        </div>
      )}

      {!canCreate && (
        <div className="mt-8 rounded border border-zinc-800 bg-zinc-900/50 p-3 text-xs text-zinc-500">
          Your workspace role is <strong>{user.workspaceRole}</strong>. You
          need at least <strong>editor</strong> to create notes. This
          demonstrates <code>require_role(&quot;editor&quot;)</code> from the SDK.
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/notes/page.tsx
git commit -m "feat: add notes list page"
```

---

### Task 11: Create Note detail page

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/notes/[id]/page.tsx`

**Step 1: Create the note detail page**

Port from React demo's `NoteDetail.tsx`. Key changes: `useParams()` and `useRouter()` from `next/navigation`, `Link` from `next/link`:

```tsx
"use client";

import { useAuthzUser } from "@sentinel-auth/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { deleteNote, fetchNote, updateNote } from "@/lib/notes";
import { ShareDialog } from "@/components/ShareDialog";

export default function NoteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthzUser();
  const router = useRouter();
  const queryClient = useQueryClient();

  const {
    data: note,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["note", id],
    queryFn: () => fetchNote(id),
    enabled: !!id,
  });

  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [showShare, setShowShare] = useState(false);

  const updateMutation = useMutation({
    mutationFn: () => updateNote(id, { title, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["note", id] });
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteNote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      router.replace("/notes");
    },
  });

  const canDelete = ["admin", "owner"].includes(user.workspaceRole);
  const isOwner = note?.owner_id === user.userId;

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-300" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="mb-2 text-sm text-red-400">
          {error instanceof Error ? error.message : "Failed to load note"}
        </p>
        <p className="text-xs text-zinc-500">
          This may be a permission issue — the identity service&apos;s entity ACL
          denied access via <code>permissions.can()</code>.
        </p>
        <Link
          href="/notes"
          className="mt-4 inline-block text-sm text-zinc-400 underline"
        >
          Back to notes
        </Link>
      </div>
    );
  }

  if (!note) return null;

  function startEditing() {
    setTitle(note!.title);
    setContent(note!.content);
    setEditing(true);
  }

  return (
    <div>
      <Link
        href="/notes"
        className="mb-4 inline-block text-sm text-zinc-500 hover:text-zinc-300"
      >
        &larr; Back to notes
      </Link>

      {editing ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mb-3 w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-100 focus:border-zinc-500 focus:outline-none"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            className="mb-4 w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none"
          />
          <div className="flex gap-3">
            <button
              onClick={() => setEditing(false)}
              className="rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
            >
              Cancel
            </button>
            <button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {updateMutation.isPending ? "Saving..." : "Save"}
            </button>
          </div>
          {updateMutation.isError && (
            <p className="mt-2 text-sm text-red-400">
              {updateMutation.error.message}
              <span className="block text-xs text-zinc-500">
                Edit requires entity-level &apos;edit&apos; permission via{" "}
                <code>permissions.can()</code>
              </span>
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="mb-4 flex items-start justify-between">
            <h1 className="text-xl font-bold text-zinc-100">{note.title}</h1>
            <div className="flex gap-2">
              {isOwner && (
                <button
                  onClick={() => setShowShare(true)}
                  className="rounded bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700"
                >
                  Share
                </button>
              )}
              <button
                onClick={startEditing}
                className="rounded bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700"
              >
                Edit
              </button>
              {canDelete && (
                <button
                  onClick={() => {
                    if (confirm("Delete this note?")) deleteMutation.mutate();
                  }}
                  disabled={deleteMutation.isPending}
                  className="rounded bg-red-600/20 px-3 py-1.5 text-xs text-red-400 hover:bg-red-600/30"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">
            {note.content}
          </p>
          <div className="mt-6 border-t border-zinc-800 pt-4 text-xs text-zinc-600">
            <p>
              by {note.owner_name} &middot;{" "}
              {new Date(note.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      <div className="mt-4 rounded border border-zinc-800 bg-zinc-900/50 p-3 text-xs text-zinc-500">
        <strong>SDK features shown:</strong> Viewing uses{" "}
        <code>permissions.can(token, &quot;note&quot;, id, &quot;view&quot;)</code>. Editing uses{" "}
        <code>permissions.can(..., &quot;edit&quot;)</code>. Deleting uses{" "}
        <code>require_role(&quot;admin&quot;)</code>. Sharing uses the permission
        service&apos;s share API.
      </div>

      {showShare && (
        <ShareDialog noteId={note.id} onClose={() => setShowShare(false)} />
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/notes/\\[id\\]/
git commit -m "feat: add note detail page with edit, delete, and share"
```

---

### Task 12: Create Export page

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/notes/export/page.tsx`

**Step 1: Create the export page**

Direct port from React demo:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { exportNotes } from "@/lib/notes";

export default function ExportPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["export"],
    queryFn: exportNotes,
  });

  return (
    <div>
      <h1 className="mb-2 text-xl font-bold text-zinc-100">Export Notes</h1>
      <p className="mb-6 text-sm text-zinc-500">
        This page requires the <code>notes:export</code> RBAC action, enforced
        via <code>require_action(role_client, &quot;notes:export&quot;)</code>.
      </p>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-300" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
          <p className="mb-1 text-sm font-medium text-red-400">Access Denied</p>
          <p className="text-xs text-zinc-500">
            {error instanceof Error ? error.message : "Export failed"}. You need
            the <code>notes:export</code> action assigned to your role via the
            admin panel.
          </p>
        </div>
      ) : data ? (
        <div>
          <div className="mb-4 flex items-center gap-4 text-sm text-zinc-400">
            <span>Format: {data.format.toUpperCase()}</span>
            <span>&middot;</span>
            <span>{data.count} note(s)</span>
          </div>
          <pre className="max-h-96 overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-xs text-zinc-300">
            {JSON.stringify(data.notes, null, 2)}
          </pre>
        </div>
      ) : null}

      <div className="mt-6 rounded border border-zinc-800 bg-zinc-900/50 p-3 text-xs text-zinc-500">
        <strong>How this works:</strong> On startup, the demo backend registers{" "}
        <code>notes:export</code> as a service action via{" "}
        <code>role_client.register_actions()</code>. An admin creates a role with
        this action and assigns it to users. The SDK&apos;s{" "}
        <code>require_action()</code> dependency checks the identity service
        before allowing access.
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/notes/export/
git commit -m "feat: add RBAC-gated export page"
```

---

### Task 13: Create root page (redirect to login or notes)

**Files:**
- Create: `demo-authz/frontend-nextjs/src/app/page.tsx`

**Step 1: Create the root redirect page**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthz } from "@sentinel-auth/nextjs";

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuthz();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(isAuthenticated ? "/notes" : "/login");
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="flex h-screen items-center justify-center bg-zinc-950">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-300" />
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add demo-authz/frontend-nextjs/src/app/page.tsx
git commit -m "feat: add root page with auth-aware redirect"
```

---

### Task 14: Add .gitignore, verify build, and test manually

**Files:**
- Create: `demo-authz/frontend-nextjs/.gitignore`

**Step 1: Create .gitignore**

```
node_modules/
.next/
out/
```

**Step 2: Build the SDKs**

Run: `cd sdks/js && npm run build && cd ../react && npm run build && cd ../nextjs && npm run build`
Expected: All three build successfully

**Step 3: Install and build the Next.js app**

Run: `cd demo-authz/frontend-nextjs && npm install && npm run build`
Expected: Build succeeds with all pages compiled

**Step 4: Start the dev server and test**

Prerequisites: Make sure these are running:
- Sentinel service on `:9003` (`make start`)
- Demo backend on `:9200` (`cd demo-authz/backend && uv run uvicorn src.main:app --port 9200`)
- React demo is NOT running on `:5174`

Run: `cd demo-authz/frontend-nextjs && npm run dev`
Expected: Dev server starts on `http://localhost:5174`

Manual test flow:
1. Visit `http://localhost:5174` — should redirect to `/login`
2. Click "Sign in with Google" — redirects to Google
3. After Google auth, redirected to `/auth/callback` — processes token
4. If single workspace: auto-redirected to `/notes`
5. If multiple workspaces: workspace picker shown
6. On `/notes`: notes list shown, create note if editor+
7. Click a note → `/notes/{id}` detail page with edit/delete/share
8. Navigate to `/notes/export` — RBAC-gated export page
9. Click Logout → redirected to `/login`

**Step 5: Final commit**

```bash
git add demo-authz/frontend-nextjs/
git commit -m "feat: complete Next.js team-notes demo (authz mode)"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add AuthzCallback to nextjs SDK | `sdks/nextjs/src/index.ts` |
| 2 | Scaffold Next.js project | `package.json`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs`, `.env.local`, `globals.css` |
| 3 | Providers + root layout | `src/lib/authz-client.ts`, `src/components/Providers.tsx`, `src/app/layout.tsx` |
| 4 | API layer | `src/lib/notes.ts` |
| 5 | Shared components | `RoleBadge`, `NoteCard`, `ShareDialog` |
| 6 | Nav layout | `src/components/AppShell.tsx` |
| 7 | Login page | `src/app/login/page.tsx` |
| 8 | Auth callback page | `src/app/auth/callback/page.tsx` |
| 9 | Notes layout (AuthzGuard) | `src/app/notes/layout.tsx` |
| 10 | Notes list page | `src/app/notes/page.tsx` |
| 11 | Note detail page | `src/app/notes/[id]/page.tsx` |
| 12 | Export page | `src/app/notes/export/page.tsx` |
| 13 | Root redirect page | `src/app/page.tsx` |
| 14 | Gitignore, build, test | `.gitignore` + manual verification |
