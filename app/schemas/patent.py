from datetime import date
from enum import IntEnum
from typing import Dict, List, Optional

from pydantic import BaseModel


class KindEnum(IntEnum):
    """
    Перечисление видов патентов:
    1 - изобретение,
    2 - полезная модель,
    3 - промышленный образец.
    """
    INVENTION = 1
    UTILITY_MODEL = 2
    INDUSTRIAL_DESIGN = 3


class PatentHolder(BaseModel):
    full_name: str
    tax_number: str


class PatentBase(BaseModel):
    reg_number: int
    reg_date: Optional[date] = None
    appl_date: Optional[date] = None
    owner_raw: Optional[str] = None
    address: Optional[str] = None
    name: str
    actual: bool | str
    subcategory: Optional[str] = None
    kind: int
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    appl_number: Optional[str] = None
    patent_starting_date: date
    publication_url: Optional[str] = None
    # @field_validator('kind')
    # @classmethod
    # def check_kind_value(cls, value: int):
    #     if value not in KindEnum.__members__.values():
    #         raise ValueError('Можно использовать только цифры от 1 до 3')
    #     return value


class PatentCreate(PatentBase):
    pass


class PatentUpdate(PatentBase):
    pass


class PatentAdditionalFields(PatentBase):
    patent_holders: list[PatentHolder]


    class Config:
        orm_mode = True


class PatentDB(PatentBase):
    class Config:
        orm_mode = True


class PatentsList(BaseModel):
    total: int
    items: Optional[List[PatentAdditionalFields]]


class PatentsStats(BaseModel):
    total_patents: int
    total_ru_patents: int
    total_with_holders: int
    total_ru_with_holders: int
    with_holders_percent: int
    ru_with_holders_percent: int
    by_author_count: Dict[str, int]
    by_patent_kind: Dict[int, int]
