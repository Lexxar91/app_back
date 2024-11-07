import pathlib

import pandas as pd

from app.parsers.common import format_tax_number, reg_number_to_int


class OwnershipParser():
    CHUNKSIZE = 1e3

    def __init__(self, df_path: pathlib.Path):
        self._df_path = df_path

    def _parse_row(self, row: pd.Series) -> dict:
        row = row.fillna("")

        patent_kind = int(row["patent_kind"]) if row["patent_kind"].isdigit() else None
        patent_reg_number = reg_number_to_int(row["patent_number"])
        tax_number = format_tax_number(row["person_tax_number"])

        if not (patent_kind and patent_reg_number and tax_number):
            return None

        return dict(
            patent_kind=patent_kind,
            patent_reg_number=patent_reg_number,
            person_tax_number=tax_number,
        )

    def parse(self):
        df = pd.read_csv(self._df_path, dtype=str, chunksize=self.CHUNKSIZE)

        for chunk in df:
            for _, row in chunk.iterrows():
                data = self._parse_row(row)
                yield data

    def setup(self):
        print("Setting up parser")
        df = pd.read_csv(self._df_path, chunksize=self.CHUNKSIZE)
        chunk = df.get_chunk(1)

        if "patent_number" not in chunk.columns:
            print("Column 'patent_number' not found in data")
            return False

        print("Data seems to be correct")

        return True

