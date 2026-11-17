# Beleg VPS deployment

This deployment serves a public, anonymous, read-only demo at
`https://belegflow.gotiq.co` through the existing `gotiq.co` Cloudflare Tunnel.
Only Caddy is published, on loopback; FastAPI stays inside the Compose network.
The production profile disables live AI credentials, uses a fresh demo data
volume, and blocks upload, review/approval, retry, and external connector APIs.
The public demo must contain no real tax records. Cloudflare Access and Caddy
Basic Auth are intentionally not used for this demo deployment.

## One-time VPS setup

1. Create `/srv/belegflow/source`, owned by the deployment user.
2. Copy this repository to `/srv/belegflow/source` before running its Compose
   commands.
3. Build the image locally on the VPS with
   `docker compose -f compose.yaml -f compose.production.yaml build app`
   (the VPS is ARM64).
4. From `/srv/belegflow/source`, start with
   `docker compose -f compose.yaml -f compose.production.yaml up -d --wait`.
   Only Caddy is published, on loopback. The standard `docker compose up`
   remains the local demo configuration and does not require secrets.
5. In the **existing** Cloudflare Zero Trust tunnel configuration for `gotiq.co`,
   add the public hostname `belegflow.gotiq.co` with service
   `http://127.0.0.1:8080`. Do **not** enable **Protect with Access**. Keep
   existing tunnel hostnames and the catch-all.
   Cloudflare-managed DNS should be created with the route; verify DNS resolves
   before continuing. If a BelegFlow Access app already exists, remove/disable
   its owner-only Access policy or delete that Access app so it does not continue
   to gate the hostname. Do not add a new tunnel or alter existing routes.
6. Verify `https://belegflow.gotiq.co` in a browser. The UI should open
   anonymously and offer fictional samples. Test `/api/upload` and the live
   actions to confirm they return 403. Verify direct access to `127.0.0.1:8080`
   is only available on the VPS loopback interface.

This anonymous demo is not suitable for real tax records. Do not enable live AI,
Google connectors, uploads, or real document processing on this public deployment.

## Update

Pull the reviewed revision on the VPS and run
`docker compose -f compose.yaml -f compose.production.yaml build app` followed by
`docker compose -f compose.yaml -f compose.production.yaml up -d --no-deps --force-recreate app`.
Check `docker compose ps`, the local `/api/health` endpoint, then the public URL
and demo-only endpoints. The public demo has a separate named
`belegflow-public-demo-data` volume; never attach a volume containing private records.
