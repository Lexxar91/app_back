from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Filter(Base):
    """
    Модель фильтра.

    Атрибуты:
        id (int): Уникальный идентификатор фильтра.
        name (str): Название фильтра (уникальное, не более 1000 символов).
        filename (str): Название файла, из которого был создан фильтр (не более 1000 символов).
        created (datetime): Дата и время создания фильтра.
        tax_numbers_count (int): Количество налоговых номеров в фильтре.
        tax_numbers (list[FilterTaxNumber]): Связанные налоговые номера фильтра.

    Связи:
        tax_numbers (relationship): Связь "один-ко-многим" с моделью FilterTaxNumber.
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(1000), nullable=False, unique=True)
    filename = Column(String(1000), nullable=False)
    created = Column(DateTime, default=datetime.utcnow)
    tax_numbers_count = Column(Integer, nullable=False)

    tax_numbers = relationship('FilterTaxNumber', back_populates='filter', cascade="all, delete")


class FilterTaxNumber(Base):
    """
    Модель налогового номера в фильтре.

    Атрибуты:
        id (int): Уникальный идентификатор налогового номера.
        filter_id (int): Идентификатор фильтра, к которому относится налоговый номер.
        tax_number (str): Налоговый номер.
        filter (Filter): Связанный фильтр.

    Связи:
        filter (relationship): Связь "многие-к-одному" с моделью Filter.
    """
    id = Column(Integer, primary_key=True, index=True)
    filter_id = Column(Integer, ForeignKey('filter.id'), nullable=False)
    tax_number = Column(Text, nullable=False)

    filter = relationship('Filter', back_populates='tax_numbers')