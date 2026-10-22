# Database Yedekle licensing deployment notes

This repository currently contains the schema foundation and Edge Function starters. These are not live until migrations are applied and functions are deployed to the dedicated Supabase project.

## Project
- Project ref: `hkuoymftockxmynrcjwh`
- API URL: `https://hkuoymftockxmynrcjwh.supabase.co`

## Apply the admin allowlist migration
Run `supabase/migrations/202610220002_admin_users.sql` in the Supabase SQL Editor for this project.

## Configure Edge Function secrets
In Supabase project settings / Edge Function secrets, set:
- `SUPABASE_URL` = project URL
- `SUPABASE_ANON_KEY` = publishable/anon key for auth token validation
- `SUPABASE_SERVICE_ROLE_KEY` = service role key (server-only; never put in the Windows app, GitHub source, browser, or client environment)

Supabase may automatically provide some built-in variables; verify the function runtime has them before adding duplicates.

## Deploy functions
Deploy:
- `supabase/functions/demo-request/index.ts`
- `supabase/functions/admin-review-demo/index.ts`

Keep JWT verification enabled for `admin-review-demo`. The public `demo-request` endpoint accepts unauthenticated requests by design and therefore needs rate limiting/CAPTCHA at the edge before production use. CORS is not authentication.

## Bootstrap the first admin
1. Create the first admin user through Supabase Auth.
2. Copy that user's Auth UUID from the dashboard.
3. Run in SQL Editor, replacing the placeholder with the exact UUID:
   `INSERT INTO public.admin_users (user_id, role) VALUES ('<AUTH_USER_UUID>', 'owner');`
4. Never expose admin allowlist or service-role credentials to the client.

## Required before production
- Add request rate limiting and CAPTCHA/bot protection to demo-request.
- Verify admin endpoint behavior with unauthorized, non-admin, approve, reject, and duplicate-review cases.
- Build the actual admin UI.
- Add license issuance, signed license responses, device activation, 168-hour online verification and 168-hour offline grace.
- Integrate the Windows app; do not embed a service-role key or private signing key.
- Run Supabase security advisors and confirm no anonymous/authenticated grants or policies expose customer/license/payment records.
- Keep production auto-deploy disabled until migrations and functions are reviewed and tested.
