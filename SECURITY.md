# Security policy and operating boundary

Beleg: German Tax Document Review is a local, single-operator portfolio product.
It is not designed for untrusted internet traffic or certified for regulated
financial data. The VPS production profile requires owner-only Cloudflare Access
and origin authentication. Publish only after the Access app/policy, Tunnel
origin-token validation, loopback-only ports, and origin credential have all been
configured and verified. Do not bypass that boundary or publish the API directly.

## Credentials

Never commit `.env`, OAuth refresh tokens, service-account keys, or real source
documents. Keep Google credentials outside the repository or in ignored `secrets/`.
Only load trusted Google credential configurations: some Google credential types
can invoke local or external identity mechanisms. This app does not accept
credential uploads through its UI.

If a key has been shared in chat, screenshots, or a previous workflow export,
rotate it with the provider. Removing it from the working tree is not a rotation.

## Data flow

Demo data is fictional and no-key. Live source text/images leave the machine for
the operator-configured AI endpoint. Google requests happen only after explicit
import/export actions; historical FX lookup sends a date and currency.

Originals, outputs, audit events, and graph checkpoints are retained unencrypted
in the selected local data directory. Use disk encryption and an appropriate
retention policy. Localhost does not protect against other users or malware on
the same machine.

## Implemented safeguards

- Backend-only credentials; no key-bearing configuration returned to the frontend.
- Loopback defaults, trusted-host validation, and origin checks on browser writes.
- Streaming HTTP body limits, per-file bounds, and owner-only POSIX data/database
  permissions (Windows uses the user's configured directory ACLs).
- Fixed-host historical FX requests; models cannot supply an arbitrary request URL.
- Upload type/size limits, PDF page limits, image pixel bounds, safe stored filenames.
- Typed model/review validation, no invented missing financial values, human export approval.
- Formula escaping for CSV; RAW values and explicit actions for Google Sheets.
- Content-hash duplicate prevention and persistent review/checkpoint state.

These controls do not amount to tenant isolation, full sandboxing, exactly-once
delivery, protection from other processes running as the same local user, or
complete prompt-injection prevention. Model text is untrusted;
review source documents before relying on any extracted result.

## Reporting

For sensitive reports, contact the maintainer through the contact details on
https://mantakamahir.github.io/. Do not attach keys or private financial documents
to public issues. Include the affected revision, reproducible steps using fictional
data, and the expected trust boundary.
