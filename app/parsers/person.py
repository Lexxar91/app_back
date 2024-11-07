import datetime
import pathlib

import pandas as pd

from app.parsers.common import format_tax_number


class PersonParser():
    CHUNKSIZE = 1e3
    CAT_AC_CODES = {
        "Высокотехнологичные ИТ компании": [
            "62.01", "62.02", "62.02.1", "62.02.4", "62.03.13", "62.09", "63.11.1"
        ],
        "Научные организации": [
            "72", "72.1", "72.11", "72.19", "72.19.1", "72.19.11", "72.19.12",
            "72.19.2", "72.19.3", "72.19.4", "72.19.9", "72.2", "72.20", "72.20.1",
            "72.20.11", "72.20.19", "72.20.2"
        ],
        "Колледжи": ["85.21"],
        "ВУЗ": ["85.22", "85.22.1", "85.22.2", "85.22.3", "85.23"],
     }

    def __init__(self, df_path: pathlib.Path):
        self._df_path = df_path

    def _get_category(self, activity_code: str) -> str:
        for cat, codes in self.CAT_AC_CODES.items():
            if activity_code.strip() in codes:
                return cat

        return "Прочие организации"

    def _parse_row(self, row: pd.Series) -> dict:
        row = row.fillna("")

        tax_number = format_tax_number(row["ИНН"])
        if tax_number is None:
            return None

        if row["ОКОПФ (расшифровка)"] == "Индивидуальные предприниматели":
            kind = 2
        else:
            kind = 1

        try:
            reg_date = datetime.datetime.fromisoformat(
                row["Дата создания"]).date()
        except:
            reg_date = None

        category = self._get_category(row["ОКВЭД2"])

        return dict(
            kind=kind,
            tax_number=tax_number,
            full_name=row["Наименование полное"],
            short_name=row["Наименование краткое"],
            legal_address=row["Юр адрес"],
            fact_address=row["Факт адрес"],
            reg_date=reg_date,
            active=row["Компания действующая (1) или нет (0)"] == "1",
            category=category,
        )

    def parse(self):
        df = pd.read_csv(self._df_path, sep=",", dtype=str, chunksize=self.CHUNKSIZE)

        for chunk in df:
            chunk.dropna(subset=["Наименование полное", "ИНН"], how="any", inplace=True)
            chunk = chunk.loc[chunk["Головная компания (1) или филиал (0)"] == '1', :].copy()
            chunk.drop_duplicates(subset=["ИНН"], inplace=True)

            for _, row in chunk.iterrows():
                data = self._parse_row(row)
                yield data

    def setup(self):
        print("Setting up parser")
        df = pd.read_csv(self._df_path, sep=",", chunksize=self.CHUNKSIZE)
        chunk = df.get_chunk(1)

        if "ИНН" not in chunk.columns:
            print("Column 'ИНН' not found in data")
            return False

        print("Data seems to be correct")

        return True

