"""
Final Assignment: Acquiring and Processing Information on the World's Largest Banks

Pipeline:
    1. Extract  - scrape the list of largest banks (name and market cap in USD billion)
    2. Transform - convert market cap to GBP, EUR and INR using exchange rates
    3. Load     - save results to CSV and to an SQLite database
    4. Query    - run SQL queries against the database and print the results
    5. Log      - record each stage with a timestamp in a log file
"""

import sqlite3
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
URL = (
    "https://web.archive.org/web/20230908091635/"
    "https://en.wikipedia.org/wiki/List_of_largest_banks"
)
EXCHANGE_RATE_CSV = "exchange_rate.csv"
TABLE_ATTRIBS = ["Name", "MC_USD_Billion"]
OUTPUT_CSV = "Largest_banks_data.csv"
DB_NAME = "Banks.db"
TABLE_NAME = "Largest_banks"
LOG_FILE = "code_log.txt"
CURRENCIES = ["GBP", "EUR", "INR"]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log_progress(message: str) -> None:
    """Append a timestamped message to the log file."""
    timestamp = datetime.now().strftime("%Y-%h-%d-%H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} : {message}\n")


# ---------------------------------------------------------------------------
# 1. Extract
# ---------------------------------------------------------------------------
def extract(url: str, table_attribs: list) -> pd.DataFrame:
    """Scrape bank names and market capitalisation (USD billion) from the first wikitable."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="wikitable")
    if table is None:
        raise ValueError("Could not find the banks table on the page.")

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cols = tr.find_all("td")
        if len(cols) < 3:
            continue  # skip header or malformed rows
        name = cols[1].get_text(strip=True)
        market_cap_text = cols[2].get_text(strip=True).replace(",", "")
        try:
            market_cap = float(market_cap_text)
        except ValueError:
            continue
        rows.append([name, market_cap])

    df = pd.DataFrame(rows, columns=table_attribs)
    log_progress("Data extraction complete. Initiating Transformation process")
    return df


# ---------------------------------------------------------------------------
# 2. Transform
# ---------------------------------------------------------------------------
def transform(df: pd.DataFrame, csv_path: str) -> pd.DataFrame:
    """Add market cap columns converted to GBP, EUR and INR (rounded to 2 decimals)."""
    rates = pd.read_csv(csv_path)
    rate_map = rates.set_index("Currency")["Rate"].to_dict()

    for currency in CURRENCIES:
        column = f"MC_{currency}_Billion"
        df[column] = (df["MC_USD_Billion"] * rate_map[currency]).round(2)

    log_progress("Data transformation complete. Initiating Loading process")
    return df


# ---------------------------------------------------------------------------
# 3. Load
# ---------------------------------------------------------------------------
def load_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """Save the DataFrame to a CSV file."""
    df.to_csv(output_path, index=False)
    log_progress("Data saved to CSV file")


def load_to_db(df: pd.DataFrame, sql_connection, table_name: str) -> None:
    """Write the DataFrame to an SQLite table, replacing it if it exists."""
    df.to_sql(table_name, sql_connection, if_exists="replace", index=False)
    log_progress("Data loaded to Database as a table, Executing queries")


# ---------------------------------------------------------------------------
# 4. Query
# ---------------------------------------------------------------------------
def run_queries(query_statements: list, sql_connection) -> None:
    """Execute each SQL query and print its result."""
    for query in query_statements:
        print(f"\nQuery: {query}")
        result = pd.read_sql(query, sql_connection)
        print(result.to_string(index=False))
    log_progress("Process Complete")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log_progress("Preliminaries complete. Initiating ETL process")

    df = extract(URL, TABLE_ATTRIBS)
    df = transform(df, EXCHANGE_RATE_CSV)
    load_to_csv(df, OUTPUT_CSV)

    conn = sqlite3.connect(DB_NAME)
    try:
        load_to_db(df, conn, TABLE_NAME)

        queries = [
            f"SELECT * FROM {TABLE_NAME}",
            f"SELECT AVG(MC_GBP_Billion) AS avg_mc_gbp FROM {TABLE_NAME}",
            f"SELECT Name FROM {TABLE_NAME} LIMIT 5",
        ]
        run_queries(queries, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
