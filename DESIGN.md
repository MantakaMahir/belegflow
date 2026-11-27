# Beleg: German Tax Document Review design system

## Public walkthrough

The public site speaks to a first-time visitor. Its opening pairs a short product
explanation with the sample selector and the start of a source-to-record
comparison. The US dividend is the default because the translation and USD-to-EUR
conversion communicate the workflow in one example. The invoice shows when no
conversion is needed; the incomplete receipt shows where review stops.

- **Color:** a moss-tinted canvas, paper for the original, fir green for the
  extracted record, and a pale green highlight for converted values and cited
  evidence. Amber denotes missing information.
- **Type:** one locally served Archivo variable font. Monetary fields use
  tabular figures; interface copy uses sentence case.
- **Layout:** side-by-side source and record on desktop. On narrow screens the
  conversion comes first, followed by the document and review details.
- **Interaction:** sample selection updates the shareable fragment. An evidence
  link opens the original and focuses the line it cites. Reduced-motion users
  see the same content without transitions.
- **Delivery:** `site/` contains the templates, styles, script, and assets;
  `deploy/build_demo.py` renders static HTML from the fictional app fixtures.
  All three original documents and records remain readable without JavaScript.
  Only `site/dist/` is published.

## Local workbench

The primary surface is a local document-review workbench. Its first screen keeps
the queue, source evidence, currency conversion, classification, and next action
visible together. Demo content is explicitly fictional; live processing and human
review use the same restrained information hierarchy.

## Visual language

- **Navigation:** deep marine blue, persistent on wide screens and compact,
  icon-first navigation on phones.
- **Work surfaces:** cool off-white canvas, white document/review panels, fine
  blue-gray dividers, square-edged document pages, and a restrained cobalt action.
- **Semantic states:** teal means completed/approved; amber means review/attention;
  red is reserved for failed processing.
- **Typography:** native system sans stack for stable, fast local startup. Tabular
  figures for financial amounts. Labels remain readable at mobile sizes.
- **Interaction:** native buttons, inputs, dates and selects; keyboard-visible
  focus; reduced-motion support; no dependency for visual effects.

## Layout and components

- `web/src/styles.css` owns tokens, layout, state styling, and responsive rules.
- `web/src/App.tsx` composes the inbox, source preview, review panel, and settings.
- `web/src/Flow.tsx` lazy-loads React Flow for persisted workflow inspection.
- `web/src/types.ts` mirrors the API's document, run, and graph contracts.

Wide screens use a navigation rail, a bounded document queue, a flexible source
pane, and a fixed-width review pane. At tablet/mobile widths the source stacks
above the review, while the document queue becomes an explicit selection panel.
The workflow canvas remains pannable and zoomable instead of shrinking its nodes
into unreadable cards.

## Accessibility and motion

Controls have names, the page includes a skip link, forms have labels, status is
expressed in text as well as color, and `prefers-reduced-motion` disables motion.
Any design change should retain keyboard operation, focus visibility, readable
contrast, and mobile overflow checks.

## Verified trade-offs

Use a system font instead of downloading a hosted font. Show extracted text rather
than a pixel-perfect PDF viewer. Keep the source and review data close together;
do not replace the workbench with generic metric cards or an agent chat surface.
