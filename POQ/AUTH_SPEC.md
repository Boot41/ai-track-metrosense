# Auth Spec (JWT + HttpOnly Cookie)

## Summary
Add email/password authentication with JWT stored in HttpOnly cookies. Only `signup` and `login` are public. All `/api/*` routes require a valid JWT. The root `/health` remains public for basic uptime checks.

## Backend
- Database: `users` table with `id`, `email` (unique), `password_hash`, `created_at`.
- Endpoints:
  - `POST /api/auth/signup` (public) → creates user, sets JWT cookie.
  - `POST /api/auth/login` (public) → verifies user, sets JWT cookie.
  - `POST /api/auth/logout` (protected) → clears JWT cookie.
  - `GET /api/auth/me` (protected) → returns current user info.
- JWT:
  - Single access token (no refresh).
  - Stored in HttpOnly cookie, `SameSite=Lax`, `Secure` in production.
  - Min password length: 8.
- Protect all `/api/*` routes via auth dependency; `/health` remains public.
- CORS: allow credentials and explicit origins (no `"*"` when cookies are used).

## Frontend
- Routes: `/login`, `/signup`, `/` (chat).
- Protected route guard for `/` and other app routes.
- Auth state:
  - `GET /api/auth/me` on app load to establish session.
  - Login/signup sets session; logout clears session.
- Axios uses `withCredentials: true`.

## Tests
- Backend unit tests for:
  - Signup/login success, invalid login, logout clears cookie.
  - Protected routes reject unauthenticated requests.
  - `/health` remains public.
- Manual: login → access chat → logout redirects to login.
