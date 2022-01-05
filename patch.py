from io import StringIO
import pandas as pd
from loguru import logger
import sys
import config
import spreadsheet
import mmap

logger.add(sys.stdout, format="{time} {level} {message}", level="DEBUG")
logger.add("patch.log", level="DEBUG", rotation="1 MB")
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
        "Couldn't parse the spreadsheet. Make sure that url and column names are correct and spreadsheet is open to public."
    )
    exit()
logger.success(f"Parsed {config.SHEET_NAME}, num of values = {len(tablichka.index)}")
warning_columns = [
    "Name",
    "Type",
    "Disassemble",
    "Extracted Value",
]
empty_warning_columns = tablichka[warning_columns].isnull().values.any()
if empty_warning_columns:
    logger.warning(
        f"Found empty spreadsheet values in {warning_columns} columns. Script might still work but you should probably fill these."
    )
    logger.info(f"Empty names will be replaced with UNKNOWN")
    tablichka["Name"] = tablichka["Name"].fillna("UNKNOWN")

error_columns = ["Address", "Value Override Converted to HEX", "Value hex original"]
empty_error_columns = tablichka[error_columns].isnull().values.sum()
if empty_error_columns:
    empty_rows = [
        row for row in tablichka[tablichka["Address"].isna()].index
    ]  # TODO: fix
    empty_rows += [
        row
        for row in tablichka[tablichka["Value Override Converted to HEX"].isna()].index
    ]
    empty_rows += [
        row for row in tablichka[tablichka["Value hex original"].isna()].index
    ]
    empty_rows.sort()
    logger.error(
        f"Found {empty_error_columns} empty spreadsheet value(s) with ID {empty_rows} in {error_columns} columns. Exiting..."
    )
    exit()


try:
    with open(config.LIB_TO_PATCH, "r+b") as lib_file:
        lib = mmap.mmap(lib_file.fileno(), 0, access=mmap.ACCESS_WRITE)
except FileNotFoundError as e:
    logger.error(e)
    exit()

logger.success(f"Loaded lib file {config.LIB_TO_PATCH}")
changed_values = tablichka.loc[
    tablichka["Value Override Converted to HEX"] != tablichka["Value hex original"]
]  # выбираются значения где дефолт хекс и новый хекс не совпадают
values_to_patch = list(
    zip(changed_values["Address"], changed_values["Value Override Converted to HEX"])
)
logger.info(f"Patching {len(values_to_patch)} values")
changelog = StringIO()
changelog.write("This is an auto-generated changelog by PepegaPatcher\n\n")
changelog.write(
    changed_values.to_string(
        index=False, na_rep="", columns=["Name", "Extracted Value", "Value override"]
    )
)

with open(config.LIB_TO_PATCH + ".txt", "w", encoding="utf-8") as f:
    print(changelog.getvalue(), file=f)
