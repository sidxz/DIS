import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthzProvider } from '@sentinel-auth/react'
import { App } from './App'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const SENTINEL_URL = import.meta.env.VITE_SENTINEL_URL || 'http://localhost:9003'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthzProvider config={{ sentinelUrl: SENTINEL_URL }}>
        <App />
      </AuthzProvider>
    </GoogleOAuthProvider>
  </StrictMode>,
)
