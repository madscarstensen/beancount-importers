import csv as csv_stdlib  # only if you need a custom dialect

import dateutil.parser

import beangulp
from beancount.core import data
from beangulp.importers import csv
from beangulp.importers.csv import Col

from beancount_importers.bank_classifier import payee_to_account_mapping
from decimal import Decimal

UNCATEGORIZED_EXPENSES_ACCOUNT = "Expenses:Uncategorized"
INCOME_ACCOUNT = "Income:Uncategorized"

PAYEE_TO_ACCOUNT = {
    "Netto": "Expenses:Groceries",
    "REMA1000": "Expenses:Groceries",
    "Lidl": "Expenses:Groceries",
    "Coop": "Expenses:Groceries",
    "SuperBrugsen": "Expenses:Groceries",
    "SBrugsen": "Expenses:Groceries",
    "DSB": "Expenses:Transport",
    "Lønoverførsel": "Income:Salary:Netcompany",
    "REVOLUT": "Assets:Revolut",
    "Huslån": "Expenses:Bills:Housing",
    "Husforsikring": "Expenses:Insurance",
    "Årsrejseforsikring": "Expenses:Insurance",
    "IF SKADEFORSIKRING": "Expenses:Insurance",
    "LetsikringVedDoed": "Expenses:Insurance",
    "AKADEMIKERNES": "Expenses:UnionAndAKasse",
    "IDA INGENIØRFORE": "Expenses:UnionAndAKasse",
    "Indboforsikring": "Expenses:Insurance",
    "Vandforbrug": "Expenses:Bills:Water",
    "Spildevand": "Expenses:Bills:Sewage",
    "Renovationsgebyr": "Expenses:Bills:Waste",
    "Kontingent grundejerforening": "Expenses:Bills:Housing:Association",
    "Børne- og Ungeydelse": "Income:ChildBenefit",
    "Den Grønne Kile": "Expenses:ChildCare",
    "Skattestyrelsen": "Expenses:Taxes",
}

def identify(self, filepath):
    import re
    with open(filepath, encoding="utf-8-sig") as f:
        head = f.read(200)
    # our rows look like: 25-09-2026;...;DKK
    return bool(re.match(r"\d{2}-\d{2}-\d{4};", head))

def parse_dk_amount(s: str) -> Decimal:
    """'2.050,45' -> Decimal('2050.45'); '-1.388,02' -> Decimal('-1388.02')."""
    s = s.strip().replace(".", "").replace(",", ".")
    return Decimal(s)


def categorizer(txn, row):
    amount = parse_dk_amount(row[2])
    currency = row[3].strip() or "DKK"

    # Rebuild the bank posting with the corrected amount
    bank_units = data.Amount(amount, currency)
    txn.postings[0] = data.Posting(
        txn.postings[0].account, bank_units, None, None, None, None)

    details = row[1]
    payee = details.split(",")[0].strip()

    if amount < 0:
        posting_account = next(
            (acc for key, acc in PAYEE_TO_ACCOUNT.items()
             if key.lower() in details.lower()),
            UNCATEGORIZED_EXPENSES_ACCOUNT,
        )
    else:
        posting_account = INCOME_ACCOUNT

    txn.postings.append(
        data.Posting(posting_account, -bank_units, None, None, None, None))
    return txn


def get_importer(account, currency):
    return csv.CSVImporter(
        {
            Col.DATE: 0,
            Col.NARRATION: 1,
            Col.AMOUNT: 2,
            Col.CURRENCY: 3,
        },
        account,
        currency,
        categorizer=categorizer,
        dateutil_kwds={"parserinfo": dateutil.parser.parserinfo(dayfirst=True)},
        # Semicolon-delimited file
        csv_dialect="semicolon",
        # utf-8-sig strips the BOM (U+FEFF) from the first line
        encoding="utf-8-sig",
    )


csv_stdlib.register_dialect("semicolon", delimiter=";")


if __name__ == "__main__":
    ingest = beangulp.Ingest([get_importer("Assets:LSBPersonal", "DKK")], [])
    ingest()
