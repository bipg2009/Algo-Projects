# ExcelGeneration.py

import csv

import os

from datetime import datetime



REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Reports")





def report_date_slug(test_date):

    """Filename / row date: dd-mm-yy (e.g. 22-05-26)."""

    s = str(test_date).strip()

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):

        try:

            return datetime.strptime(s, fmt).strftime("%d-%m-%y")

        except ValueError:

            continue

    return s.replace("/", "-")





HEADERS = [
    "date",
    "trade id",
    "time ist",
    "event",
    "symbol",
    "strategy",
    "option_type",
    "price",
    "trailing_sl",
    "rsi",
    "oi",
    "outcome",
]





def report_path(filename):

    os.makedirs(REPORTS_DIR, exist_ok=True)

    return os.path.join(REPORTS_DIR, filename)





def trade_book_filename(test_date):

    return f"backtest_trade_book_{report_date_slug(test_date)}.csv"





def initialize_csv(filename, overwrite=False):

    path = report_path(filename)

    if overwrite or not os.path.exists(path):

        with open(path, mode="w", newline="", encoding="utf-8") as f:

            csv.writer(f).writerow(HEADERS)

    return path





def _row_for_headers(row_dict):

    aliases = {

        "trade_id": "trade id",

        "time_ist": "time ist",

        "rsi_1m": "rsi",

    }

    out = {}

    for h in HEADERS:

        out[h] = row_dict.get(h, row_dict.get(aliases.get(h, ""), ""))

    return out





def write_to_book(filename, row_dict):

    initialize_csv(filename)

    with open(report_path(filename), mode="a", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=HEADERS)

        writer.writerow(_row_for_headers(row_dict))





def write_trade_book_rows(test_date, rows, overwrite=True):

    """Write only BUY/SELL rows to backtest_trade_book_dd-mm-yy.csv."""

    fname = trade_book_filename(test_date)

    initialize_csv(fname, overwrite=overwrite)

    for row in rows:

        event = (row.get("event") or "").upper()

        if "BUY" not in event and "SELL" not in event:

            continue

        write_to_book(fname, row)

    return report_path(fname)


