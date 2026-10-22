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

Before deploying `activate-license`, configure `LICENSE_SIGNING_PRIVATE_JWK` as a Supabase Edge Function secret containing an Ed25519 private JWK JSON object. Generate a fresh Ed25519 key pair in a trusted local environment; store only the private JWK in Supabase secrets and embed only the public key in the desktop client. Never commit either key to GitHub. The activation response is signed over a base64url-encoded JSON payload; the desktop client must verify the Ed25519 signature before trusting any payload fields. The payload sets `verify_again_after` to 168 hours and `offline_grace_until` to 336 hours after issuance. These timestamps are only effective if the desktop app enforces them and checks the device fingerprint hash.

Keep JWT verification enabled for `admin-review-demo`; the function additionally validates the user's access token and checks `public.admin_users` for an active `owner` or `admin` role. The public `demo-request` endpoint intentionally accepts unauthenticated requests. CORS is not authentication; before production, add edge rate limiting and CAPTCHA/bot protection. The `create-license` endpoint requires an authenticated active `owner` or `admin`, accepts an active customer ID, and returns a newly generated license key only once while storing only its SHA-256 hash. The `activate-license` endpoint accepts a license key and device fingerprint, hashes both server-side, and atomically binds the license to one device. A different device is rejected until an administrator releases the current device using `release-license-device`.

The admin-review handler calls `public.review_demo_request_atomic`, which updates the demo request, customer status, and audit event in a single database transaction. Apply migration `202610220003_atomic_demo_review.sql` before deploying the updated admin-review function; without it, the function returns an explicit error. The activation and device-release handlers call `public.activate_license_atomic` and `public.release_license_device_atomic`; apply migration `202610220004_license_activation_and_device_release.sql` first.

## Bootstrap the first admin

1. Create the first admin user through Supabase Auth.
2. Copy that user's Auth UUID from the dashboard.
3. Add the user to the allowlist using SQL Editor, replacing the placeholder with the exact UUID:
   `INSERT INTO public.admin_users (user_id, role) VALUES ('<AUTH_USER_UUID>', 'owner');`
4. Never expose admin allowlist or server-side secret credentials to the client.

## Known implementation gaps — not production-ready yet

- Public demo requests need rate limiting and CAPTCHA/bot protection.
- Build and test the admin UI.
- Move approval/rejection + customer status + audit event into one transaction/RPC.
- Verify unauthorized, non-admin, approve, reject, duplicate-review, and partial-failure cases.
- Integrate signature verification and the 168-hour online verification / 168-hour offline grace rules into the desktop client. The server endpoint now requires `LICENSE_SIGNING_PRIVATE_JWK` and returns an Ed25519-signed response, but it has not been deployed or end-to-end tested.
- Integrate the Windows app without embedding a service-role/secret key or private signing key.
- Run Supabase security advisors and confirm no anonymous/authenticated grants or policies expose private customer/license/payment records.
- Do not enable production auto-deploy until migrations and functions are reviewed and tested.

## Live deployment status

The repository alone cannot prove what version is currently deployed in Supabase. Confirm the deployed Edge Function source/version and test the endpoint after deployment. A successful public demo request does not prove that the admin-review function is deployed or working.
