# Auth Redirect Changes for Mobile Deep Linking

## Problem
The backend was ignoring the `redirect_uri` parameter and always redirecting to `/` after OAuth authentication, preventing mobile apps from receiving the authentication token via deep links.

## Solution
Modified `backend/app/routers/auth.py` to:

1. **Accept `redirect_uri` parameter** in `/api/auth/login` endpoint
2. **Store it in state** alongside PKCE code_verifier: `state → (code_verifier, redirect_uri)`
3. **Use it in callback** to redirect appropriately:
   - **Mobile deep links** (`osmosis://...`): Redirect with token as query parameter
   - **Web URLs** (`http://`, `https://`): Redirect with token as query parameter  
   - **Relative paths** (`/dashboard`): Use cookie-based session (original behavior)
   - **No redirect_uri**: Default to `/` (original behavior)

## Flow Examples

### Mobile App Flow
```
GET /api/auth/login?redirect_uri=osmosis://auth/callback
  ↓ (stores redirect_uri in state)
Redirect to Authentik
  ↓ (user authenticates)
GET /api/auth/callback?code=...&state=...
  ↓ (retrieves redirect_uri from state)
Redirect to: osmosis://auth/callback?token=<session_token>
```

### Web App Flow (unchanged)
```
GET /api/auth/login
  ↓ (no redirect_uri, defaults to /)
Redirect to Authentik
  ↓ (user authenticates)
GET /api/auth/callback?code=...&state=...
  ↓ (no redirect_uri, defaults to /)
Redirect to: / (with session_token cookie)
```

## Backward Compatibility
- Existing web flows continue to work unchanged
- No redirect_uri parameter = defaults to `/` (original behavior)
- Relative paths still use cookie-based sessions

## Security Considerations
- Session tokens are short-lived (24h expiry)
- Mobile apps receive tokens via URL (necessary for deep linking)
- Web apps continue using HttpOnly cookies (more secure)
