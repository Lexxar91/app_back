from enum import IntEnum

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import date


class PersonKindEnum(IntEnum):
    """
    Перечисление видов лиц:
    1 - юрлицо,
    2 - ИП,
    3 - физлицо.
    """
    LEGAL_ENTITY = 1
    INDIVIDUAL_ENTREPRENEUR = 2
    INDIVIDUAL = 3


class PersonBase(BaseModel):
    kind: int
    tax_number: str
    full_name: Optional[str]
    short_name: Optional[str]
    legal_address: Optional[str]
    fact_address: Optional[str]
    reg_date: Optional[date]
    active: bool
    okopf: Optional[str]
    okvad: Optional[str]
    ogrn: str
    region: Optional[str]
    uk: int
    support_type: Optional[str]
    # @field_validator('kind')
    # @classmethod
    # def check_kind_value(cls, value: int):
    #     if value not in PersonKindEnum.__members__.values():
    #         raise ValueError('Можно использовать только цифры от 1 до 3')
    #     return value


class PersonCreate(PersonBase):
    pass


class PersonUpdate(PersonBase):
    pass


class PersonPatents(BaseModel):
    kind: int
    reg_number: int


class PersonAdditionalFields(PersonBase):
    category: str
    patents: list[PersonPatents] = []
    patent_count: int = 0

    class Config:
        orm_mode = True


class PersonDB(PersonBase):
    class Config:
        orm_mode = True

class StatItem(BaseModel):
    name: str
    count: int

class PersonsList(BaseModel):
    okopf_stats: List[StatItem]
    okvad_stats: List[StatItem]
    mpk_stats: List[StatItem]

    class Config:
        from_attributes = True

class PersonsMskStats(BaseModel):
    total_persons: int
    by_kind: Dict[int, int]
    by_category: Dict[str, int]
    moscow_cluster_percentage: float
    moscow_support_type_percentage: float

class PersonsAllStats(BaseModel):
    total_persons: int
    by_kind: Dict[int, int]
    by_category: Dict[str, int]

    class Config:
        orm_mode = True
