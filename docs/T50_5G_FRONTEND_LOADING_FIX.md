# T50.5G Frontend Infinite Loading Fix

> **Date**: 2026-06-13

---

## Root Cause

4 pages used the pattern `if (authLoading || !user) → show spinner`:

```tsx
// BEFORE (bug)
if (authLoading || !user) {
  return <Spinner />;  // infinite spinner when user has no valid token
}
```

When a user visits without a token (or with an expired token), `user` is null.
The spinner rendered forever because there was no redirect to `/login`.

## Fix

Split the condition: spinner only during loading, redirect when auth fails.

```tsx
// AFTER (fix)
useEffect(() => {
  if (!authLoading && !user) router.push("/login");
}, [authLoading, user, router]);

if (authLoading) return <Spinner />;
if (!user) return null;
```

## Affected Files

| File | Change |
|------|--------|
| `frontend/src/app/page.tsx` | `!user → router.push("/login")` |
| `frontend/src/app/analytics/page.tsx` | same |
| `frontend/src/app/memory/page.tsx` | same + added `useRouter` import |
| `frontend/src/app/reports/page.tsx` | same |

## Behavior

```
No token        → redirect to /login immediately
Invalid token   → AuthContext clears token → redirect to /login
Valid token     → show page normally
Loading         → show spinner briefly
```

## Files

| File | Change |
|------|--------|
| `docs/T50_5G_FRONTEND_LOADING_FIX.md` | Report |
