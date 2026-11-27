"""Render the public demo from the same fictional fixtures as the local app."""

import argparse
import html
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path
from string import Template

from app.demo import SCENARIOS
from app.money import convert_money

SITE = Path(__file__).resolve().parents[1] / "site"
COPY = {
    "us-dividend": (
        "US dividend",
        "USD to EUR",
        "Check whether the US tax withheld can be credited in Germany.",
    ),
    "german-invoice": (
        "German invoice",
        "Already in EUR",
        "Confirm whether the client sent or received the invoice before treating it as income.",
    ),
    "ambiguous-receipt": (
        "Incomplete receipt",
        "Date and currency missing",
        "Confirm the date, what currency the $ symbol represents, and the business purpose.",
    ),
}


def format_date(value):
    day = date.fromisoformat(value)
    return f"{day.day} {day:%b %Y}"


def render_transcript(text, sample_id, linked_lines=()):
    lines = []
    for index, line in enumerate(text.splitlines()):
        line_id = f"{sample_id}-line-{index}"
        target = f' id="{line_id}" tabindex="-1"' if index in linked_lines else ""
        lines.append(f"<p{target}>{html.escape(line)}</p>")
    return "\n".join(lines)


def render_sample(sample_id, scenario, template):
    extraction = scenario["extraction"]
    classification = scenario["classification"]
    currency = extraction.get("currency")
    day = extraction.get("document_date")
    amount = Decimal(extraction["original_amount"])
    converted = "Unavailable"
    rate_note = "Conversion requires a document date and an explicit currency."
    withholding = ""
    if currency and day:
        if currency == "EUR":
            rate, rate_note = Decimal(1), "The source is already in euros."
        else:
            fx = scenario["fx"]
            rate = Decimal(fx["rate"])
            rate_note = (
                f"1 {currency} = {rate} EUR on {format_date(fx['date'])} (illustrative rate)."
            )
        converted = f"€{Decimal(convert_money(amount, rate)):,.2f}"
        tax = convert_money(extraction.get("tax_deduction"), rate)
        if tax is not None:
            withholding = f"<div><dt>Withheld tax in euros</dt><dd>€{Decimal(tax):,.2f}</dd></div>"

    source_lines = scenario["text"].splitlines()
    amount_line = next(
        i for i, line in enumerate(source_lines) if line.startswith(scenario["amount_line"])
    )
    linked_lines = {amount_line}
    evidence_links = []
    for quote in classification["evidence"]:
        index = next(i for i, line in enumerate(source_lines) if quote in line)
        linked_lines.add(index)
        if index == amount_line:
            continue
        evidence_links.append(
            f'<li><a href="#{sample_id}-line-{index}">{html.escape(quote)}</a></li>'
        )

    title, _, review_note = COPY[sample_id]
    translated = extraction["language"] != "de"
    language_controls = ""
    translation_panel = ""
    if translated:
        language_controls = f'''
        <div class="language-switch" role="group" aria-label="Document language" hidden>
          <button type="button" data-language="original" aria-pressed="true" aria-controls="{sample_id}-original">Original</button>
          <button type="button" data-language="german" aria-pressed="false" aria-controls="{sample_id}-german">German translation</button>
        </div>
        '''
        translation_panel = f'''
        <div id="{sample_id}-german" class="transcript" data-transcript="german" lang="de" hidden>
          {render_transcript(extraction["translated_text"], sample_id)}
        </div>
        '''
    values = {
        "id": sample_id,
        "title": title,
        "filename": scenario["filename"],
        "state_class": "is-blocked" if not currency or not day else "",
        "state": "Missing information" if not currency or not day else "Needs human review",
        "language": extraction["language"],
        "source_note": "Fictional English source with German translation"
        if translated
        else "Fictional German source",
        "original_amount": f"{amount:,.2f} {currency}" if currency else f"${amount:,.2f}",
        "eur_amount": converted,
        "rate_note": rate_note,
        "amount_source": f"#{sample_id}-line-{amount_line}",
        "record_id": extraction["document_id"],
        "document_date": format_date(day) if day else "Missing",
        "category": classification["income_type"],
        "review_note": review_note,
    }
    return template.substitute(
        {key: html.escape(value) for key, value in values.items()},
        original=render_transcript(scenario["text"], sample_id, linked_lines),
        language_controls=language_controls,
        translation_panel=translation_panel,
        withholding=withholding,
        evidence_links="\n".join(evidence_links),
    )


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    page = Template((SITE / "index.html").read_text(encoding="utf-8"))
    sample = Template((SITE / "sample.html").read_text(encoding="utf-8"))
    controls = []
    panels = []
    for sample_id, scenario in SCENARIOS.items():
        title, description, _ = COPY[sample_id]
        controls.append(
            f'<button type="button" aria-controls="{sample_id}" aria-pressed="false">'
            '<svg aria-hidden="true" viewBox="0 0 24 24" width="19" height="19">'
            '<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6m-6 4h6"/></svg>'
            f"<span><strong>{html.escape(title)}</strong><small>{html.escape(description)}</small></span>"
            "</button>"
        )
        panels.append(render_sample(sample_id, scenario, sample))
    (output / "index.html").write_text(
        page.substitute(sample_controls="\n".join(controls), sample_panels="\n".join(panels)),
        encoding="utf-8",
    )
    for name in ("styles.css", "demo.js"):
        shutil.copyfile(SITE / name, output / name)
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("beleg.svg", "archivo-latin.woff2", "archivo-license.txt"):
        shutil.copyfile(SITE / "assets" / name, assets / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SITE / "dist")
    build(parser.parse_args().output)
