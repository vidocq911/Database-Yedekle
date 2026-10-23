# Database Yedekle licensing deployment notes

This repository contains the licensing/customer schema and Edge Function source. A GitHub commit does **not** deploy a function to Supabase unless a deployment workflow is explicitly configured and succeeds.

## Project

- Project ref: `hkuoymftockxmynrcjwh`
- API URL: `https://hkuoymftockxmynrcjwh.supabase.co`

## Database setup

The schema foundation and admin allowlist migrations are:

- `supabase/migrations/202610220001_licensing_customer_management.sql`
- `supabase/migrations/202610220002_admin_users.sql`
- `supabase/migrations/202610220003_atomic_demo_review.sql`
- `supabase/migrations/202610220004_license_activation_and_device_release.sql`

Only apply migrations that have not already been applied. The schema uses RLS with no client-facing policies on the private customer, demo, license, device, sales, payment, and event tables. Do not add broad `anon` or `authenticated` policies to make the application work.

The database-generated customer number uses `public.customer_number_seq`. The public demo function requires server-side insert/select access to `customers` and `demo_requests`, plus `USAGE, SELECT` on that sequence for the privileged function key. Grant only what is needed to the trusted server role.

## Edge Function keys

Supabase projects may expose modern built-in environment variables such as:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEYS` (JSON map; the default publishable key is used for Auth user-token validation)
- `SUPABASE_SECRET_KEYS` (JSON map; the default secret key is server-only)

The functions now prefer the modern key variables and fall back to legacy `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` variables for older projects. Never put a secret/service-role key in a Windows app, browser, public repository, or client environment. Do not paste keys into issues or chat.

## Functions and security

Deploy these functions from the current branch when ready:

- `supabase/functions/demo-request/index.ts`
- `supabase/functions/admin-review-demo/index.ts`
- `supabase/functions/create-license/index.ts`
- `supabase/functions/activate-license/index.ts`
- `supabase/functions/release-license-device/index.ts`
- `supabase/functions/admin-dashboard/index.ts` (authenticated dashboard data; owner/admin allowlist required)
- `supabase/functions/admin-manage/index.ts` (authenticated sales, payment, customer-status, and license-status actions)

Before deploying `activate-license`, generate an Ed25519 key pair locally:
```powershell
python -m pip install cryptography
python scripts/generate_license_signing_key.py
```
This writes local private/public JWK JSON files; both are excluded by `.gitignore`. In PowerShell with Supabase CLI logged in, set the private key secret (do not paste it into chat or GitHub):
```powershell
$privateJwk = Get-Content .\\license-signing-private.jwk.json -Raw
supabase secrets set LICENSE_SIGNING_PRIVATE_JWK="$privateJwk" --project-ref hkuoymftockxmynrcjwh
supabase functions deploy activate-license --project-ref hkuoymftockxmynrcjwh --no-verify-jwt
```
Keep the public JWK from `license-signing-public.jwk.json` for the desktop client. Never commit either key file. The activation response is signed over a base64url-encoded JSON payload; a client must verify the Ed25519 signature before trusting claims. The payload sets `verify_again_after` to 168 hours and `offline_grace_until` to 336 hours after issuance. The GUI now has a **Lisans** action, online activation, signature verification, and a local cache of the signed envelope. The activation client checks that the public JWK is present before contacting the server, preventing an activation slot from being consumed when the client cannot verify the response. However, the app does not yet enforce a license gate before backup operations or perform the scheduled online recheck automatically. Those are remaining implementation tasks.

Keep JWT verification enabled for `admin-review-demo`; the function additionally validates the user's access token and checks `public.admin_users` for an active `owner` or `admin` role. The public `demo-request` endpoint intentionally accepts unauthenticated requests. CORS is not authentication; before production, add edge rate limiting and CAPTCHA/bot protection. The `create-license` endpoint requires an authenticated active `owner` or `admin`, accepts an active customer ID, and returns a newly generated license key only once while storing only its SHA-256 hash. The `activate-license` endpoint accepts a license key and device fingerprint, hashes both server-side, and atomically binds the license to one device. A different device is rejected until an administrator releases the current device using `release-license-device`.

The admin-review handler calls `public.review_demo_request_atomic`, which updates the demo request, customer status, and audit event in a single database transaction. Apply migration `202610220003_atomic_demo_review.sql` before deploying the updated admin-review function; without it, the function returns an explicit error. The activation and device-release handlers call `public.activate_license_atomic` and `public.release_license_device_atomic`; apply migration `202610220004_license_activation_and_device_release.sql` first.

## Bootstrap the first admin

1. Create the first admin user through Supabase Auth.
2. Copy that user's Auth UUID from the dashboard.
3. Add the user to the allowlist using SQL Editor, replacing the placeholder with the exact UUID:
   `INSERT INTO public.admin_users (user_id, role) VALUES ('<AUTH_USER_UUID>', 'owner');`
4. Never expose admin allowlist or server-side secret credentials to the client.

## Admin dashboard setup

- Static dashboard UI: `docs/admin.html` (link from the product landing page).
- The page uses Supabase Auth password sign-in and calls `admin-dashboard`, `admin-review-demo`, `create-license`, and `release-license-device`.
- Deploy `admin-dashboard` alongside the other functions. The dashboard function verifies the current Auth user and checks `public.admin_users` for an active `owner` or `admin` role before returning customer, demo, license, device, sales, or payment data. The `admin-manage` function performs authorized sale creation, payment recording, customer blocking/unblocking, and license suspend/reactivate/revoke actions.
- Publish the `docs/` folder using GitHub Pages. If the site is served from the repository's `docs/` directory, the panel URL is `https://<owner>.github.io/<repository>/admin.html`.
- On the sign-in page, enter the project's public publishable/anon key and a Supabase Auth administrator email/password. Never enter a secret/service-role key in the browser.
- Bootstrap the owner with the SQL statement in the previous section. The dashboard does not offer public self-registration or a way to grant admin privileges.
- Dashboard UI includes overview, customer list, demo approval/rejection, license creation, device release, sale creation, payment recording, customer block/unblock, license suspend/reactivate/revoke, and sales/payment views.

## Known implementation gaps — not production-ready yet

- Public demo requests need rate limiting and CAPTCHA/bot protection.
- Deploy and test the new `admin-dashboard` and `admin-manage` Edge Functions and verify that all functions are deployed to the intended Supabase project.
- Review the atomic demo-review RPC and test unauthorized, non-admin, approve, reject, duplicate-review, and partial-failure cases.
- Verify unauthorized, non-admin, approve, reject, duplicate-review, and partial-failure cases.
- Bundle the generated public JWK as `license-public-jwk.json` with the Windows app; never bundle the private signing key or any Supabase secret.
- Enforce the verified license state before backup operations, re-verify the cached envelope on each launch, and implement online rechecks at 168 hours plus the offline cutoff at 336 hours.
- Add automated tests for the activation/cache flow and run an end-to-end test against the deployed Supabase function before production release.
- Run Supabase security advisors and confirm no anonymous/authenticated grants or policies expose private customer/license/payment records.
- Do not enable production auto-deploy until migrations and functions are reviewed and tested.

## Live deployment status

The repository alone cannot prove what version is currently deployed in Supabase. Confirm the deployed Edge Function source/version and test the endpoint after deployment. A successful public demo request does not prove that the admin-review function is deployed or working.
