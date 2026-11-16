# Beleg VPS deployment

This deployment runs Beleg on the existing `gotiq.co` Cloudflare Tunnel and
serves it at `https://belegflow.gotiq.co`. Only Caddy is published, on loopback;
FastAPI stays inside the Compose network. Caddy requires a separate origin
password. FastAPI requires the expected Access identity email, and Caddy removes
the browser's Basic Auth header before forwarding it. That identity header is
trusted only because Tunnel **Protect with Access** validates the Access JWT
before forwarding. Never expose Caddy beyond loopback or disable either
authentication layer.

## One-time VPS setup

1. Create `/srv/belegflow/source` and `/srv/belegflow/secrets`, owned by the
   deployment user. Set the secrets directory to mode `0700`.
2. Create `/srv/belegflow/source/.env` with the exact `PUBLIC_ACCESS_EMAIL`
   configured as the owner's identity in Cloudflare Access. The production
   profile always enables the check; the base local compose file leaves it
   disabled. Set mode `0600`.
3. Create `/srv/belegflow/secrets/proxy.env` with `BELEG_USERNAME` and a bcrypt
   `BELEG_PASSWORD_HASH`. Set mode `0600`. Generate the hash with Caddy's
   `caddy hash-password`; do not put the clear-text password in the file. Use a
   different password than your Cloudflare account.
   The Compose `env_file` uses raw format so the bcrypt hash is passed literally.
   Verify the resolved proxy environment/config before start.
4. Copy this repository to `/srv/belegflow/source` before running its Compose
   commands.
5. Build the image locally on the VPS with
   `docker compose -f compose.yaml -f compose.production.yaml build app`
   (the VPS is ARM64).
6. From `/srv/belegflow/source`, start with
   `docker compose -f compose.yaml -f compose.production.yaml up -d --wait`.
   Only Caddy is published, on loopback. The standard `docker compose up`
   remains the local demo configuration and does not require secrets.
7. Add a Cloudflare Access self-hosted application for `belegflow.gotiq.co` before
   publishing the tunnel route. Add an allow policy limited to the owner's
   identity. In the tunnel route's origin settings, set **Protect with Access**
   to that Access application so the connector validates Access tokens at the
   origin. Follow Cloudflare's documented configuration at
   https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/.
8. In the **existing** Cloudflare Zero Trust tunnel configuration for `gotiq.co`,
   add the public hostname `belegflow.gotiq.co` with service
   `http://127.0.0.1:8080`. Enable **Protect with Access** for that same
   application. Keep existing tunnel hostnames and the catch-all.
   Cloudflare-managed DNS should be created with the route; verify DNS resolves
   before continuing. Do not add a new tunnel or alter existing routes.
9. Enable HTTPS redirection for this hostname and verify `https://belegflow.gotiq.co`
   in a browser before sharing it. Verify direct access to `127.0.0.1:8080`
   without proxy credentials is denied as well.

The app intentionally is not an anonymous public service. Cloudflare Access and
the independent proxy password are defense in depth; neither changes the
single-operator/data-protection limitations in `SECURITY.md`. Do not process real
tax records on this demo deployment.

## Update

Pull the reviewed revision on the VPS and run
`docker compose -f compose.yaml -f compose.production.yaml build app` followed by
`docker compose -f compose.yaml -f compose.production.yaml up -d --no-deps --force-recreate app`.
Check `docker compose ps`, the local `/api/health` endpoint, then the public URL,
Cloudflare Access login, and origin credential gate. The database and uploaded
originals persist in the named `belegflow-data` volume.
