# React Integration

`@sentinel-auth/react` provides context providers, hooks, and components for React apps. This page covers authz mode (recommended). For proxy mode, the package also exports `SentinelAuthProvider`, `useAuth`, `AuthGuard`, and `AuthCallback`.

```bash
npm install @sentinel-auth/js @sentinel-auth/react
```

## AuthzProvider

Wrap your app to provide auth context.

```tsx
import { AuthzProvider } from '@sentinel-auth/react'
import { IdpConfigs } from '@sentinel-auth/js'

function App() {
  return (
    <AuthzProvider config={{
      sentinelUrl: 'http://localhost:9003',
      idps: { google: IdpConfigs.google('your-google-client-id') },
    }}>
      <YourApp />
    </AuthzProvider>
  )
}
```

Pass a pre-created client via the `client` prop when you need the instance outside React.

## useAuthz()

Full auth context. Throws if used outside `AuthzProvider`.

```tsx
const {
  user,             // SentinelUser | null
  isAuthenticated,  // boolean
  isLoading,        // boolean
  login,            // (provider: string) => void
  resolve,          // (idpToken, provider) => Promise<AuthzResolveResponse>
  selectWorkspace,  // (idpToken, provider, wsId) => Promise<void>
  logout,           // () => void
  fetch,            // dual-header fetch
  fetchJson,        // <T>(input, init?) => Promise<T>
  client,           // SentinelAuthz instance
} = useAuthz()
```

## Other hooks

**useAuthzUser()** -- returns `SentinelUser`, throws if not authenticated.

```tsx
const user = useAuthzUser()
// { userId, email, name, workspaceId, workspaceSlug, workspaceRole, groups }
```

**useAuthzHasRole(minimum)** -- checks workspace role hierarchy (`viewer` < `editor` < `admin` < `owner`).

```tsx
const isAdmin = useAuthzHasRole('admin')
```

**useAuthzFetch()** -- shortcut to the dual-header fetch wrapper.

## AuthzGuard

Gate content behind authentication.

```tsx
<AuthzGuard fallback={<LoginPage />} loading={<Spinner />}>
  <Dashboard />
</AuthzGuard>
```

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | required | Shown when authenticated |
| `fallback` | `ReactNode` | required | Shown when not authenticated |
| `loading` | `ReactNode` | `null` | Shown while checking auth state |

## AuthzCallback

Handles the OAuth callback. Reads `id_token` from the URL hash, resolves workspaces, auto-selects if one, shows picker if multiple.

```tsx
<AuthzCallback
  onSuccess={(user) => navigate('/dashboard')}
  onError={(err) => console.error(err)}
  workspaceSelector={({ workspaces, onSelect, isLoading }) => (
    <ul>
      {workspaces.map((ws) => (
        <li key={ws.id}>
          <button onClick={() => onSelect(ws.id)} disabled={isLoading}>
            {ws.name} ({ws.role})
          </button>
        </li>
      ))}
    </ul>
  )}
/>
```

| Prop | Type | Description |
|------|------|-------------|
| `onSuccess` | `(user: SentinelUser) => void` | Called after auth completes |
| `onError` | `(error: Error) => void` | Called on error |
| `loadingComponent` | `ReactNode` | Loading UI |
| `errorComponent` | `(error: Error) => ReactNode` | Error UI |
| `workspaceSelector` | `(props) => ReactNode` | Custom workspace picker |

## Complete example

```tsx
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import { AuthzProvider, AuthzGuard, AuthzCallback, useAuthz, useAuthzUser } from '@sentinel-auth/react'
import { IdpConfigs } from '@sentinel-auth/js'

function App() {
  return (
    <AuthzProvider config={{
      sentinelUrl: 'http://localhost:9003',
      idps: { google: IdpConfigs.google(import.meta.env.VITE_GOOGLE_CLIENT_ID) },
    }}>
      <BrowserRouter>
        <Routes>
          <Route path="/auth/callback" element={<Callback />} />
          <Route path="/*" element={
            <AuthzGuard fallback={<Login />} loading={<p>Loading...</p>}>
              <Dashboard />
            </AuthzGuard>
          } />
        </Routes>
      </BrowserRouter>
    </AuthzProvider>
  )
}

function Login() {
  const { login } = useAuthz()
  return <button onClick={() => login('google')}>Sign in with Google</button>
}

function Callback() {
  const navigate = useNavigate()
  return <AuthzCallback onSuccess={() => navigate('/', { replace: true })} />
}

function Dashboard() {
  const user = useAuthzUser()
  const { logout } = useAuthz()
  return (
    <div>
      <p>Welcome, {user.name} ({user.workspaceRole})</p>
      <button onClick={logout}>Logout</button>
    </div>
  )
}
```
