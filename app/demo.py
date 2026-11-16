"""Fictional examples, not client documents. FX figures are illustrative fixtures."""

SCENARIOS = {
    "us-dividend": {
        "title": "A dividend, across borders",
        "description": "English investment statement · USD → EUR · foreign withholding review",
        "filename": "northstar-dividend-2025.txt",
        "text": """NORTHSTAR SECURITIES — FICTIONAL DEMO DOCUMENT
Dividend statement | NS-2025-0418
Client: Alex Morgan | Client number: DEMO-104
Statement date: 2025-04-18
Period: 2025-01-01 to 2025-03-31
Gross dividend: USD 1,250.00
US withholding tax: USD 187.50 (15%)
Security: Northstar Global Equity Fund
Payment frequency: quarterly
This document is synthetic and has no financial or legal value.""",
        "extraction": {
            "document_id": "NS-2025-0418",
            "client_name": "Alex Morgan",
            "client_number": "DEMO-104",
            "language": "en",
            "document_type": "Dividend statement",
            "document_date": "2025-04-18",
            "period_start": "2025-01-01",
            "period_end": "2025-03-31",
            "tax_year": 2025,
            "original_amount": "1250.00",
            "currency": "USD",
            "party": "Northstar Securities",
            "purpose": "Quarterly equity-fund dividend",
            "tax_deduction": "187.50",
            "tax_types": ["Foreign withholding tax"],
            "periodicity": "Quarterly",
            "warnings": [],
            "translated_text": "NORTHSTAR SECURITIES — FIKTIVES DEMODOKUMENT\nDividendengutschrift NS-2025-0418\nMandant: Alex Morgan (DEMO-104)\nBelegdatum: 18.04.2025\nZeitraum: 01.01.2025–31.03.2025\nBruttodividende: 1.250,00 USD\nUS-Quellensteuer: 187,50 USD (15 %)\nNorthstar Global Equity Fund · vierteljährlich\nFiktives Dokument ohne rechtlichen oder finanziellen Wert.",
        },
        "classification": {
            "income_type": "Investment",
            "relevance": "Relevant",
            "assessment": "Potential investment income under §20 EStG. Foreign withholding requires treaty and creditability review; this is a suggested classification, not tax advice.",
            "evidence": ["Gross dividend: USD 1,250.00", "US withholding tax: USD 187.50 (15%)"],
            "warnings": [
                "Review foreign withholding and any applicable tax treaty before reporting."
            ],
        },
        "fx": {"rate": "0.8812", "date": "2025-04-17"},
    },
    "german-invoice": {
        "title": "An invoice, already in EUR",
        "description": "German consulting invoice · no FX required · structured extraction",
        "filename": "studio-west-invoice-2025.txt",
        "text": """STUDIO WEST — FIKTIVES DEMODOKUMENT
Rechnung SW-2025-092
Mandant: Alex Morgan | Mandantennummer: DEMO-104
Rechnungsdatum: 2025-05-12
Leistungszeitraum: 2025-05-01 bis 2025-05-10
Leistung: Honorar für freiberufliche Designberatung
Rechnungsbetrag gesamt: EUR 2.400,00
Umsatzsteuer: nicht ausgewiesen
Aussteller: Studio West
Einmalige Leistung. Fiktives Dokument ohne rechtlichen Wert.""",
        "extraction": {
            "document_id": "SW-2025-092",
            "client_name": "Alex Morgan",
            "client_number": "DEMO-104",
            "language": "de",
            "document_type": "Invoice",
            "document_date": "2025-05-12",
            "period_start": "2025-05-01",
            "period_end": "2025-05-10",
            "tax_year": 2025,
            "original_amount": "2400.00",
            "currency": "EUR",
            "party": "Studio West",
            "purpose": "Freelance design consulting",
            "tax_deduction": None,
            "tax_types": [],
            "periodicity": "One-time",
            "warnings": [],
            "translated_text": "STUDIO WEST\nRechnung SW-2025-092\nMandant: Alex Morgan\nRechnungsdatum: 12.05.2025\nLeistung: Honorar für freiberufliche Designberatung\nRechnungsbetrag gesamt: EUR 2.400,00\nUmsatzsteuer: nicht ausgewiesen\nFiktives Demodokument.",
        },
        "classification": {
            "income_type": "Self-employment",
            "relevance": "Possibly relevant",
            "assessment": "The document describes freelance services. Confirm whether the client issued or received the invoice before treating the amount as income or expense.",
            "evidence": ["Honorar für freiberufliche Designberatung"],
            "warnings": ["Confirm the client's role: issuer or recipient."],
        },
    },
    "ambiguous-receipt": {
        "title": "Missing data, not invented data",
        "description": "Incomplete receipt · ambiguous $ currency · export blocked until corrected",
        "filename": "travel-receipt-incomplete.txt",
        "text": """HARBOR TRAVEL — FICTIONAL DEMO DOCUMENT
Receipt HT-8821
Passenger: Alex Morgan
Date: unreadable
Total paid: $480.00
Journey: client meeting
The currency country and travel date are not shown.
Synthetic document for demonstrating a manual-review exception.""",
        "extraction": {
            "document_id": "HT-8821",
            "client_name": "Alex Morgan",
            "language": "en",
            "document_type": "Receipt",
            "original_amount": "480.00",
            "currency": None,
            "party": "Harbor Travel",
            "purpose": "Travel to a client meeting",
            "translated_text": "HARBOR TRAVEL\nQuittung HT-8821\nReisender: Alex Morgan\nDatum: unleserlich\nGesamtbetrag: $480,00\nAnlass: Kundentermin\nWährungsland und Reisedatum fehlen. Fiktives Demodokument.",
            "warnings": [
                "The $ symbol alone does not identify a currency.",
                "Document date is missing.",
            ],
        },
        "classification": {
            "income_type": "Unclassified",
            "relevance": "Possibly relevant",
            "assessment": "A possible business-travel expense. A receipt alone does not establish an income category or deductibility.",
            "evidence": ["Journey: client meeting"],
            "warnings": ["Confirm currency, date, and business purpose."],
        },
    },
}
