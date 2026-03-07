import type { AuthzTokenStore } from './authz-types'

const PREFIX = 'sentinel_'

/** Authz token storage using browser localStorage. */
export class AuthzLocalStorageStore implements AuthzTokenStore {
  getIdpToken(): string | null {
    return localStorage.getItem(`${PREFIX}idp_token`)
  }

  getAuthzToken(): string | null {
    return localStorage.getItem(`${PREFIX}authz_token`)
  }

  getProvider(): string | null {
    return localStorage.getItem(`${PREFIX}idp_provider`)
  }

  getWorkspaceId(): string | null {
    return localStorage.getItem(`${PREFIX}workspace_id`)
  }

  setTokens(idpToken: string, authzToken: string, provider: string, workspaceId: string): void {
    localStorage.setItem(`${PREFIX}idp_token`, idpToken)
    localStorage.setItem(`${PREFIX}authz_token`, authzToken)
    localStorage.setItem(`${PREFIX}idp_provider`, provider)
    localStorage.setItem(`${PREFIX}workspace_id`, workspaceId)
  }

  clear(): void {
    localStorage.removeItem(`${PREFIX}idp_token`)
    localStorage.removeItem(`${PREFIX}authz_token`)
    localStorage.removeItem(`${PREFIX}idp_provider`)
    localStorage.removeItem(`${PREFIX}workspace_id`)
  }
}

/** In-memory authz token storage for SSR or testing. */
export class AuthzMemoryStore implements AuthzTokenStore {
  private idpToken: string | null = null
  private authzToken: string | null = null
  private provider: string | null = null
  private workspaceId: string | null = null

  getIdpToken(): string | null {
    return this.idpToken
  }

  getAuthzToken(): string | null {
    return this.authzToken
  }

  getProvider(): string | null {
    return this.provider
  }

  getWorkspaceId(): string | null {
    return this.workspaceId
  }

  setTokens(idpToken: string, authzToken: string, provider: string, workspaceId: string): void {
    this.idpToken = idpToken
    this.authzToken = authzToken
    this.provider = provider
    this.workspaceId = workspaceId
  }

  clear(): void {
    this.idpToken = null
    this.authzToken = null
    this.provider = null
    this.workspaceId = null
  }
}
