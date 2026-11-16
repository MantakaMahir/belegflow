import csv
import io
from decimal import Decimal, InvalidOperation

# These aliases preserve the business meaning of the original sheet, not its secrets.
COLUMNS = {
    "Client Name/Mandant": "client_name",
    "Client No/No": "client_number",
    "Document Summary/DocID": "document_id",
    "Document Language/DocLanguage": "language",
    "Document Summary/Datei": "filename",
    "Document Type/Doctype": "document_type",
    "Tax Classifyer/Einkunftsart": "income_type",
    "Tax Relevance/Relevanz": "relevance",
    "Tax Result/Rechtliche_Würdigung": "assessment",
    "Date Extractor/Belegdatum": "document_date",
    "Service Period Extractor/Zeitraum_Start": "period_start",
    "Service Period Extractor/Zeitraum_Ende": "period_end",
    "Year Allocator/Tax Year": "tax_year",
    "Value Extractor/Betrag_Original": "original_amount",
    "Currency identifier/Währung": "currency",
    "FX Rate/EZB_Kurs_Jahr": "fx.rate",
    "FX Converter/Betrag_EUR": "fx.amount_eur",
    "Counterparty Identifier/Partei": "party",
    "Transaction Purpose/Zweck": "purpose",
    "Identify Tax Deductions/Steuer_Abzüge": "fx.tax_deduction_eur",
    "Classify Tax Deduction Type/Steuerart": "tax_types",
    "Determine Recurring/Periodizität": "periodicity",
    "Cumulative Confidence/Confidence": "quality",
    "Create Comment/Notes": "review_note",
    "invoice link": "source_url",
}
NUMERIC_FIELDS = {
    "original_amount",
    "tax_deduction",
    "fx.rate",
    "fx.amount_eur",
    "fx.tax_deduction_eur",
    "tax_year",
}


def spreadsheet_value(value):
    """Prevent document-controlled strings from becoming spreadsheet formulas."""
    text = "" if value is None else str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def export_row(run):
    data = {
        **run["result"],
        "filename": run["filename"],
        "source_url": run.get("source_url", ""),
        "quality": "Human reviewed; no calibrated confidence score",
    }
    row = []
    for key in COLUMNS.values():
        value = data
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, list):
            value = ", ".join(value)
        if key in NUMERIC_FIELDS and value is not None:
            try:
                number = Decimal(str(value))
                if number.is_finite():
                    row.append(format(number, "f"))
                    continue
            except InvalidOperation:
                pass
        row.append(spreadsheet_value(value))
    return row


def csv_export(runs):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    writer.writerows(export_row(run) for run in runs)
    return "\ufeff" + buffer.getvalue()
