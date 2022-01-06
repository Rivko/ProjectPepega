import config
import math
import mmap
from loguru import logger
import csv
from arm import get_spreadsheet_type

# logger.add(sys.stdout, format="{time} {level} {message}", level="DEBUG")
logger.add(
    "convert.log",
    level="DEBUG",
    rotation="1 MB",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
)
# logger.remove()
# logger.add(sys.stdout, level="INFO")


def read_hbk_by_offset(offset: int) -> str:
    """
    Reads hex from hbk starting at address and until it gets to 00 byte
    :param offset: starting address in dec
    :return: extracted string
    :rtype: str
    """
    try:
        with open(config.HBK_NAME, "rb") as f:
            hbk = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            # 448
            # 208
            value = ""
            logger.debug(f"Address = {offset}, {hex(offset)=}")
            hbk.seek(offset)
            while True:
                t = hbk.read(1)
                if t == b"\x00":
                    break
                value = value + t.decode("utf-8")
            logger.debug(f"Extracted value = {value}")
            return value

    except ValueError as e:
        logger.error(e)
        exit()


if __name__ == "__main__":
    logger.debug(f"Config: {config.HBK_NAME=}, {config.LIB_TO_EXTRACT=}")
    logger.info(f"Trying to load {config.HBK_NAME}")

    try:
        with open(config.HBK_NAME, "rb") as hbk_file:
            hbk = mmap.mmap(hbk_file.fileno(), 0, access=mmap.ACCESS_READ)
            hbk_size = math.floor(hbk.size() / 656)
    except FileNotFoundError as e:
        logger.error(e)
        exit()

    logger.success(
        f"Loaded {config.HBK_NAME}, file size = {hbk.size()} bytes, addresses = {hbk_size-1}"
    )

    with open(config.HBK_NAME + ".csv", "w") as csvfile:
        filewriter = csv.writer(
            csvfile, delimiter="\t", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        filewriter.writerow(config.COLUMN_NAMES)
        try:
            with open(config.LIB_TO_EXTRACT, "r+b") as f:
                glib = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE)
                start_offset = (
                    448  # первый букмарк лежит через 448 байт от начала файла
                )
                for i in range(hbk_size - 1):
                    name = read_hbk_by_offset(start_offset)
                    address_offset = (
                        start_offset + 80
                    )  # адрес лежит через 80 байт после имени
                    address = read_hbk_by_offset(address_offset)
                    length_offset = (
                        start_offset + 208
                    )  # размер лежит через 208 после имени
                    length = int(read_hbk_by_offset(length_offset), 16)
                    array_count_offset = (
                        start_offset + 336
                    )  # количество значений для массивов лежит через 336 байт после имени
                    array_count = int(read_hbk_by_offset(array_count_offset), 16)
                    start_offset = (
                        start_offset + 656
                    )  # дальше букмарки идут через каждые 656 байт
                    if array_count > 1:
                        logger.info(f"{name} is an array of {array_count} values")
                        for j in range(array_count):
                            array_address = (
                                int(address, 16) + length * j
                            )  # начальный адрес + длина умноженная на номер в массиве = адрес значения в массиве
                            glib.seek(array_address)
                            read_value = glib.read(length)
                            array_address = (
                                hex(array_address).upper().replace("X", "0")
                            )  #
                            logger.debug(
                                f"{array_address=}, {read_value.hex().upper()=}"
                            )
                            arm_type = get_spreadsheet_type(read_value)
                            # arm_type = "HEX VALUE"
                            # if length == 8:
                            #     extracted_value = from_hex_to_double(read_value.hex())
                            #     arm_type = "DBL"
                            # elif length > 8:
                            #     arm_type = "HEX STRING"
                            #     extracted_value = from_hex_to_string(read_value)
                            # else:
                            #     extracted_value = from_hex_to_arm(read_value)
                            #     if extracted_value is None:
                            #         extracted_value = from_hex_to_float(read_value.hex())
                            #         arm_type = "FLT"
                            #     else:
                            #         arm_type = get_arm_type(extracted_value)
                            logger.info(
                                f"#{j}, {name=}, {array_address=}, {length=}, {read_value.hex().upper()=}, {arm_type=}"
                            )
                            filewriter.writerow(
                                [
                                    i + 1,
                                    f"{name} [{j}]",
                                    arm_type,
                                    array_address,
                                    read_value.hex().upper(),
                                ]
                            )
                    else:
                        glib.seek(int(address, 16))
                        default_value = glib.read(length)
                        arm_type = get_spreadsheet_type(default_value)
                        logger.info(
                            f"#{i}, {name=}, {address=}, {length=}, {default_value.hex().upper()=}, {arm_type=}"
                        )
                        filewriter.writerow(
                            [
                                i + 1,
                                name,
                                arm_type,
                                address,
                                default_value.hex().upper(),
                            ]
                        )
        except FileNotFoundError as e:
            logger.error(e)
            exit()
