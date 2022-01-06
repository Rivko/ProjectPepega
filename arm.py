import re
import struct

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM


def from_hex_to_arm(hex_bytes: bytes) -> str:
    """
    :param hex_bytes: hex bytes to convert to ARM64
    :return: ARM64 mnemonic
    """
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    for instruction in md.disasm(hex_bytes, 0x1000):
        mnemonic, op_str = instruction.mnemonic, instruction.op_str
        return mnemonic + " " + op_str


def get_arm_type(mnemonic: str) -> str:
    """
    :param mnemonic: arm mnemonic string
    :return: arm type of input string
    """
    armrpl_mnemonics = ["fmul", "fdiv", "fcvt", "fsqrt", "fmax", "fmaxnm", "fmin"]
    if mnemonic.split()[0] in armrpl_mnemonics:
        return "ARMRPL"
    armdbl = re.compile("movz.*lsl.#48")
    if armdbl.match(mnemonic):
        return "ARMDBL"
    armflt = re.compile("mov[z|k].*lsl.#(16|48)")
    if armflt.match(mnemonic):
        return "ARMFLT"
    if mnemonic.split()[0] == "movz":
        return "ARMDEC"
    arm_normal = re.compile("fmov.*#")
    if arm_normal.match(mnemonic):
        return "ARM"
    if mnemonic.split()[0] == "fmov" or mnemonic[:5] == "ldr s":
        return "ARMRPL"
    return "ARMMANUAL"


def from_hex_to_double(hex_string: str) -> str:
    """
    :param hex_string: hex string to convert to double
    :return: double
    """
    return struct.unpack("<d", bytes.fromhex(hex_string))[0]


def from_hex_to_float(hex_string: str) -> str:
    """
    :param hex_string: hex string to convert to float
    :return: float
    """
    return struct.unpack("<f", bytes.fromhex(hex_string))[0]


def from_hex_to_string(hex_string: bytes) -> str:
    """
    :param hex_string: hex string in bytes that you need to convert to normal looking string
    :return: normal looking string
    """
    try:
        decoded_hex = str(hex_string.decode("utf-8")).replace("\x00", "")
    except Exception as e:
        decoded_hex = "[Error while decoding]"
    return decoded_hex


def get_spreadsheet_type(hex_string: bytes) -> str:
    arm_type = "HEXSTRING"
    length = len(hex_string)
    if length == 8:
        extracted_value = from_hex_to_double(hex_string.hex())
        arm_type = "DBL"
    elif length > 8:
        extracted_value = from_hex_to_string(hex_string)
    else:
        extracted_value = from_hex_to_arm(hex_string)
        if extracted_value is None:
            extracted_value = from_hex_to_float(hex_string.hex())
            arm_type = "FLT"
        else:
            arm_type = get_arm_type(extracted_value)
    return arm_type
