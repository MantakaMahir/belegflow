# BelegFlow design system

## Product surface

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
