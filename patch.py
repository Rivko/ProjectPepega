import pandas as pd
from loguru import logger
import sys
import config
import spreadsheet
import numpy as np

logger.add(sys.stdout, format="{time} {level} {message}", level="DEBUG")
# logger.add("patch_{time}.log", level="DEBUG")
logger.debug(
    f"Config: {config.SPREADSHEET_URL=}, {config.SHEET_NAME=}, {config.LIB_TO_PATCH=}"
)
try:
    sheet_id = spreadsheet.extract_id_from_url(config.SPREADSHEET_URL)
    full_url = spreadsheet.get_full_url(sheet_id, config.SHEET_NAME)
except IndexError:
    logger.error("Enter a valid spreadsheet url in config file.")
    exit()

logger.debug(f"Extracted {sheet_id=}, {full_url=}")
try:
    tablichka = pd.read_csv(full_url, index_col=0, usecols=config.COLUMN_NAMES)
except ValueError as e:
    logger.error(e)
    logger.error(
        "Couldn't parse spreadsheet. Make sure that url and column names are correct and spreadsheet is open to public."
    )
    exit()
logger.success(f"Parsed {full_url}, num of values = {len(tablichka.index)}")
print(tablichka.head(5))
warning_columns = [
    "Name",
    "Type",
    "Value hex original",
    "Disassemble",
    "Extracted Value",
]
empty_important_columns = tablichka[warning_columns].isnull().values.any()
if empty_important_columns:
    logger.warning(
        f"Found empty spreadsheet values in {warning_columns} columns. Script can still work but you should probably fill these."
    )

error_columns = ["Address", "Value Override Converted to HEX"]
empty_error_columns = tablichka[error_columns].isnull().values.sum()
if empty_error_columns:
    empty_rows = [row for row in tablichka[tablichka["Address"].isna()].index]
    empty_rows += [
        row
        for row in tablichka[tablichka["Value Override Converted to HEX"].isna()].index
    ]
    logger.error(
        f"Found {empty_error_columns} empty spreadsheet value(s) with ID {empty_rows} in {error_columns} columns. Exiting..."
    )
    exit()
