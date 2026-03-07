export { SentinelAuthProvider, type SentinelAuthContextValue, type SentinelAuthProviderProps } from './provider'
export { useAuth, useUser, useHasRole, useAuthFetch } from './hooks'
export { AuthGuard, type AuthGuardProps } from './auth-guard'
export { AuthCallback, type AuthCallbackProps, type WorkspaceSelectorProps } from './callback'

// Authz-mode provider, hooks, and guard
export { AuthzProvider, AuthzContext, type AuthzContextValue, type AuthzProviderProps } from './authz-provider'
export { useAuthz, useAuthzUser, useAuthzHasRole, useAuthzFetch } from './authz-hooks'
export { AuthzGuard, type AuthzGuardProps } from './authz-guard'

// Re-export commonly used types from @sentinel-auth/js
export type {
  SentinelConfig,
  SentinelUser,
  WorkspaceOption,
  WorkspaceRole,
  SentinelAuthzConfig,
  AuthzTokenStore,
  AuthzResolveResponse,
} from '@sentinel-auth/js'
