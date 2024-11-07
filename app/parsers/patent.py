from collections import Counter
import datetime
import pathlib
import re
from typing import Optional, Tuple

import pandas as pd

from app.parsers.common import reg_number_to_int


class PatentParser:
    CHUNKSIZE = 1e3

    def __init__(self, df: str):
        self._df = df
        self._kind = None
        self._name_col = None
        self._postal_codes = {
            int(row["INDEX"]): (row["REGION"], row["CITY"])
            for _, row in pd.read_csv(
                pathlib.Path(".").parent / "../backend/app/assets/postal-codes.csv",

            ).iterrows()
        }

    def _detect_kind_and_name_col(
        self, chunk: pd.DataFrame
    ) -> Tuple[Optional[int], Optional[str]]:
        name_cols = {
            "invention name": 1,
            "utility model name": 2,
            "industrial design name": 3,
        }

        for option in name_cols:
            if option in chunk.columns:
                name_col = option
                break
        else:
            return None, None

        return name_cols[name_col], name_col

    def _parse_row(self, row: pd.Series) -> dict:
        row = row.fillna("")

        reg_number = reg_number_to_int(row.get("registration number"))

        try:
            reg_date = datetime.datetime.strptime(
                row.get("registration date"), "%Y%m%d").date()
        except ValueError:
            reg_date = None

        try:
            appl_date = datetime.datetime.strptime(
                row.get("application date"), "%Y%m%d").date()
        except ValueError:
            appl_date = None

        author_raw = row.get("authors", "")
        owner_raw = row.get("patent holders", "")
        address = row.get("correspondence address", "")
        name = row.get(self._name_col, "")

        actual = row.get("actual", "true").lower() == "true"

        kind = self._kind

        category, subcategory = None, None
        if kind in (1, 2):
            class_code = row.get("mpk")
            if class_code:
                category = ", ".join([c.strip()[:3] for c in class_code.split(":")])
                subcategory = ", ".join([c.strip()[:4] for c in class_code.split(":")])

        country_code_regex = re.compile("\((?a:\w{2})\)")
        country_codes = Counter(country_code_regex.findall(owner_raw))
        if len(country_codes) == 0 or "(RU)" in country_codes:
            country_code = "RU"
        elif len(country_codes) == 1:
            country_code = list(country_codes)[0][1:-1]
        else:
            country_code = country_codes.most_common(1)[0][0][1:-1]

        postal_code_regex = re.compile("\d{6}")
        postal_code = postal_code_regex.search(address)
        region, city = None, None
        if postal_code is not None:
            try:
                postal_code = int(postal_code[0])
                region, city = self._postal_codes.get(postal_code, (None, None))
            except Exception:
                pass

        author_count = len(author_raw.split("\r\n"))

        return dict(
            reg_number=reg_number,
            reg_date=reg_date,
            appl_date=appl_date,
            author_raw=author_raw,
            owner_raw=owner_raw,
            address=address,
            name=name,
            actual=actual,
            category=category,
            subcategory=subcategory,
            kind=kind,
            country_code=country_code,
            region=region,
            city=city,
            author_count=author_count,
        )

    def parse(self):
        df = pd.read_csv(self._df, dtype=str, chunksize=self.CHUNKSIZE)

        for chunk in df:
            chunk.drop_duplicates(subset=["registration number"], inplace=True)
            for _, row in chunk.iterrows():
                data = self._parse_row(row)
                yield data

    def setup(self):
        print("Setting up parser")
        df = pd.read_csv(self._df, chunksize=self.CHUNKSIZE)
        chunk = df.get_chunk(1)

        if "registration number" not in chunk.columns:
            print("Column 'Registration number' not found in data")
            return False

        print("Data seems to be correct")

        kind, name_col = self._detect_kind_and_name_col(chunk)
        if kind is None or name_col is None:
            print("Cannot detect kind and name col")
            return False
        print(f"Kind is {kind}, name column is {name_col}")

        self._kind = kind
        self._name_col = name_col

        print("Preloading postal codes")
        self._postal_codes = {
            int(row["INDEX"]): (row["REGION"], row["CITY"])
            for _, row in pd.read_csv(
                pathlib.Path(".").parent / "../backend/app/assets/postal-codes.csv",

            ).fillna("").iterrows()
        }

        return True
