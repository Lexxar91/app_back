import re
from typing import Optional


def format_tax_number(tax_number: str) -> Optional[str]:
    tn_len = len(tax_number)

    if tn_len < 9 or tn_len > 12:
        return None

    if tn_len in (9, 11):
        return tax_number.rjust(tn_len + 1, "0")

    return tax_number


def reg_number_to_int(reg_number: Optional[str]) -> Optional[int]:
    if reg_number is None:
        return None
    elif reg_number.isdigit():
        reg_number = int(reg_number)
    else:
        reg_number = re.search("\d+", reg_number)
        if reg_number is not None:
            reg_number = int(reg_number[0])
        else:
            return None

    return reg_number
