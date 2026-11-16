# Beleg: German Tax Document Review

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Delegated by the user: React/TypeScript/Vite and React Flow; Python/FastAPI,
Pydantic and LangGraph; SQLite and local files. Prefer the standard library,
native browser features and the fewest moving parts that meet the requirements.

## Users
People evaluating Mantaka Mahir's AI engineering work, developers cloning the
repository, and document reviewers evaluating a German tax-intake workflow.

## Product Purpose
Convert an existing n8n document-processing workflow into a useful, publicly
available application. A no-key demo must explain the product; live mode must
execute the real pipeline with the operator's credentials. No deployment is
requested.

## Capabilities and Constraints
- Confirmed scope: document and email-file intake, OCR, German translation,
  historical currency normalization to EUR, structured extraction, German income
  classification, human review, CSV/JSON export and optional Google connectors.
- Demo uses explicitly fictional, prepared responses. It must never call paid
  providers or pretend to process arbitrary documents with a canned response.
- Live AI uses an OpenAI-compatible endpoint and configurable model, default auto.
- Credentials remain backend-only in ignored local configuration; do not publish
  the original client export, client identifiers, real documents or API keys.
- Local-first, single-operator application; not a hosted multi-tenant service.
- User approved code-first implementation and requested a professional README.
- Financial calculations are deterministic; model classifications require review
  and are not tax advice. Do not claim production validation without evidence.

## Evidence on Hand
The user supplied a 31-node n8n export outside this repository. Its active path
starts with Google Drive; Gmail intake is disabled. It uses Gemini OCR, translation,
extraction and tax classification, historical FX lookup and Google Sheets output.
The original is private input, not a shipping asset.

## Product Principles
1. One real workflow, with demo responses substituted only at external boundaries.
2. Inspectable inputs, node outputs, review decisions and export provenance.
3. Simple reproducible local setup rather than speculative infrastructure.
4. No invented financial values, accuracy benchmarks or compliance claims.
