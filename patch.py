from io import StringIO
import pandas as pd
from loguru import logger
import config
import spreadsheet
import mmap
from datetime import datetime
from shutil import copyfile
from os import makedirs, path

now = datetime.now()
dt_string = now.strftime("[%d.%m.%Y %H.%M.%S]")
#logger.add(sys.stderr, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("patch.log", level="DEBUG", rotation="1 MB", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.debug(
    f"Config: {config.SPREADSHEET_URL=}, {config.SHEET_NAME=}, {config.LIB_TO_PATCH=}"
)
try:
    sheet_id = spreadsheet.extract_id_from_url(config.SPREADSHEET_URL)
    full_url = spreadsheet.get_full_url(sheet_id, config.SHEET_NAME)
except IndexError:
    logger.error("Enter a valid spreadsheet url in config.py")
    exit()

logger.debug(f"Extracted {sheet_id=}, {full_url=}")
try:
    logger.info(f"Trying to access {full_url}")
    tablichka = pd.read_csv(
        full_url,
        index_col=0,
        usecols=config.COLUMN_NAMES,
        dtype={"Name": "str", "Value override": "str", "Extracted Value": "str"},
    )
except ValueError as e:
    logger.error(e)
    logger.error(
        "Couldn't parse the spreadsheet. Make sure that url and column names are correct and spreadsheet is open to public."
    )
    exit()
logger.success(
    f"Parsed {config.SHEET_NAME}, total num of values = {len(tablichka.index)}"
)
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
    empty_rows = []
    for column in error_columns:
        empty_rows += [
            row for row in tablichka[tablichka[column].isna()].index
        ]  # список индексов с пустыми строками
    empty_rows = sorted(set(empty_rows))
    logger.error(
        f"Found {empty_error_columns} empty spreadsheet value(s) with ID {empty_rows} in {error_columns} columns. Exiting..."
    )
    exit()

changed_values = tablichka.loc[
    tablichka["Value Override Converted to HEX"] != tablichka["Value hex original"]
]  # выбираются значения где дефолт хекс и новый хекс не совпадают
values_to_patch = list(
    zip(changed_values["Address"], changed_values["Value Override Converted to HEX"])
)


if (
    changed_values["Value Override Converted to HEX"].str.contains("Loading").any()
    or changed_values["Value Override Converted to HEX"].str.contains("NAME").any()
):
    logger.error(
        "Google Spreadsheet is still processing some values. Please wait a minute and try running the script again."
    )
    exit()

try:
    NEW_LIB_NAME = config.LIB_TO_PATCH.split(".so")[0] + "_" + dt_string
    logger.debug(f"Copying {config.LIB_TO_PATCH} to /patched/{NEW_LIB_NAME}.so")
    makedirs(path.dirname("patched/"), exist_ok=True)
    copyfile(config.LIB_TO_PATCH, "patched/" + NEW_LIB_NAME + ".so")
except Exception as e:
    logger.error(e)
    exit()

try:
    with open("patched/" + NEW_LIB_NAME + ".so", "r+b") as lib_file:
        logger.debug(f"Trying to open patched/{NEW_LIB_NAME}")
        lib = mmap.mmap(lib_file.fileno(), 0, access=mmap.ACCESS_WRITE)
except FileNotFoundError as e:
    logger.error(e)
    exit()

logger.success(f"Loaded lib file {NEW_LIB_NAME}.so")

logger.info(f"Patching {len(values_to_patch)} values")
for value in values_to_patch:
    if str(value[0]) == "nan" or str(value[1]) == "nan":
        logger.error(f"Found an empty address or value. This should not happen.")
        continue
    logger.debug(f"Patching address = {value[0]}, value = {value[1]}")
    try:
        lib.seek(int(value[0], 16), 0)
        lib.write(bytes.fromhex(value[1]))
    except ValueError as e:
        logger.error(f"Address {value[0]} is out of range.")
        exit()
lib.flush()

changelog = StringIO()
changelog.write(
    f"This is an auto-generated changelog by PepegaPatcher\nPatched on {dt_string}\n"
)
changelog.write(
    changed_values.to_string(
        index=False, na_rep="", columns=["Name", "Extracted Value", "Value override"]
    )
)
with open("patched/" + NEW_LIB_NAME + ".txt", "w", encoding="utf-8") as f:
    print(changelog.getvalue(), file=f)
logger.success("All finished :)")