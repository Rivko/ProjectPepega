import mmap
from datetime import datetime
from io import StringIO
from os import makedirs, path
from shutil import copyfile

import pandas as pd
from loguru import logger

import config
import spreadsheet
from updater import check_for_updates

# logger.add(sys.stderr, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add(
    "patch.log",
    level="DEBUG",
    rotation="1 MB",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}"
    ),
)

if __name__ == "__main__":
    now = datetime.now()
    dt_string = now.strftime("[%d.%m.%Y %H.%M.%S]")
    logger.debug(
        f"Config: {config.SPREADSHEET_URL=}, {config.SHEET_NAME=},"
        f" {config.LIB_TO_PATCH=}"
    )
    try:
        sheet_id = spreadsheet.extract_id_from_url(config.SPREADSHEET_URL)
        full_url = spreadsheet.get_full_url(sheet_id, config.SHEET_NAME)
    except IndexError:
        logger.error("Enter a valid spreadsheet url in config.py")
        exit()

    logger.debug(f"Extracted {sheet_id=}, {full_url=}")

    # обработка csv из гугл таблиц
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
            "Couldn't parse the spreadsheet. Make sure that url and column names are"
            " correct and spreadsheet is open to public."
        )
        exit()
    logger.success(
        f"Parsed {config.SHEET_NAME}, total num of values = {len(tablichka.index)}"
    )

    # столбцы без которых можно обойтись
    warning_columns = [
        "Name",
        "Type",
        "Disassemble",
        "Extracted Value",
    ]
    empty_warning_columns = tablichka[warning_columns].isnull().values.any()
    if empty_warning_columns:
        logger.warning(
            f"Found empty spreadsheet values in {warning_columns} columns. Script might"
            " still work but you should probably fill these."
        )
        logger.info(f"Empty names will be replaced with UNKNOWN")
        tablichka["Name"] = tablichka["Name"].fillna("UNKNOWN")

    # столбцы без значений которые обязательно нужны
    error_columns = ["Address", "Value Override Converted to HEX", "Value hex original"]
    empty_error_columns = tablichka[error_columns].isnull().values.sum()
    if empty_error_columns:
        empty_rows = []
        for column in error_columns:
            empty_rows += [
                row for row in tablichka[tablichka[column].isna()].index
            ]  # список индексов с пустыми строками
        empty_rows = sorted(
            set(empty_rows)
        )  # сортировка и удаление дубликатов индексов
        logger.error(
            f"Found {empty_error_columns} empty spreadsheet value(s) with ID"
            f" {empty_rows} in {error_columns} columns. These rows will be ignored during patching."
        )
        # exit()

    # выбираются значения где дефолт хекс и новый хекс не совпадают
    changed_values = tablichka.loc[
        tablichka["Value Override Converted to HEX"] != tablichka["Value hex original"]
    ]

    # чистка записей у которых есть NaN значения
    changed_values = changed_values[changed_values["Address"].notna()]
    changed_values = changed_values[
        changed_values["Value Override Converted to HEX"].notna()
    ]
    changed_values = changed_values[changed_values["Value hex original"].notna()]

    # зипуем вместе оставшиеся адреса и значения
    values_to_patch = list(
        zip(
            changed_values["Address"], changed_values["Value Override Converted to HEX"], changed_values['Value hex original']
        )
    )

    # проверка если скрипт гугл таблиц еще пытается перевести значения в хекс или обратно (Loading...)
    # или если есть ошибка в таблице и формула не работает (#NAME)
    # TODO: конченая таблица может выдавать лоадинг на других языках, нужна нормальная проверка или хз
    if (
        changed_values["Value Override Converted to HEX"].str.contains("Loading").any()
        or changed_values["Value Override Converted to HEX"].str.contains("NAME").any()
    ):
        logger.error(
            "Google Spreadsheet is still processing some values. Please wait a minute"
            " and try running the script again."
        )
        exit()

    # создаем папку /patched если её нет
    # делаем копию указанной либы в этой папке с текущей датой и временем в имени
    try:
        NEW_LIB_NAME = config.LIB_TO_PATCH.split(".so")[0] + "_" + dt_string
        logger.debug(f"Copying {config.LIB_TO_PATCH} to /patched/{NEW_LIB_NAME}.so")
        makedirs(path.dirname("patched/"), exist_ok=True)
        copyfile(config.LIB_TO_PATCH, "patched/" + NEW_LIB_NAME + ".so")
    except Exception as e:
        logger.exception(e)
        exit()

    # открываем скопированную либу для записи
    try:
        with open("patched/" + NEW_LIB_NAME + ".so", "r+b") as lib_file:
            logger.debug(f"Trying to open patched/{NEW_LIB_NAME}")
            lib = mmap.mmap(lib_file.fileno(), 0, access=mmap.ACCESS_WRITE)
    except FileNotFoundError as e:
        logger.exception(e)
        exit()

    logger.success(f"Loaded lib file {NEW_LIB_NAME}.so")
    logger.info(f"Patching {len(values_to_patch)} values")

    # патчим все выбранные значения
    for value in values_to_patch:
        if str(value[0]) == "nan" or str(value[1]) == "nan":
            logger.critical(
                f"Found an empty address or value. This should never happen."
            )
            continue
        if (str(value[0]).lower()) == "pattern":
            logger.info(f"Found pattern {value=}")
            index = lib.find(bytes.fromhex(value[2]))
            while index != -1:
                logger.debug(f"Patching pattern {value[2]} = {value[1]} at {hex(index).upper().replace('X', '0')}")
                lib.seek(index, 0)
                lib.write(bytes.fromhex(value[1]))
                index = lib.find(bytes.fromhex(value[2]))
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
        "This is an auto-generated changelog by PepegaPatcher\nPatched on"
        f" {dt_string}\n"
    )

    # копируем весь датафрейм в файл ченджлога
    changelog.write(
        changed_values.to_string(
            index=False,
            na_rep="",
            columns=["Name", "Extracted Value", "Value override"],
        )
    )

    # ченджлог записывается в файл с таким же названием как и либа
    with open("patched/" + NEW_LIB_NAME + ".txt", "w", encoding="utf-8") as f:
        print(changelog.getvalue(), file=f)
    logger.success("All finished :)")

    # проверка есть ли версии новее на гитхабе
    github_updated = check_for_updates(config.__VERSION__)
    if github_updated:
        logger.success(
            f"New update {github_updated} is available @"
            " https://github.com/Rivko/ProjectPepega"
        )
