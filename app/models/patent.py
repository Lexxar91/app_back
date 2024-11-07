from sqlalchemy import Column, Integer, Date, String, Boolean, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from app.core.db import Base


class Patent(Base):
    """
    Модель Patent.

    Атрибуты:
       reg_number (int): Регистрационный номер патента. Индексируемый столбец.
       reg_date (Date): Дата регистрации патента.
       appl_date (Date): Дата подачи заявки на патент.
       author_raw (str): Необработанные данные автора.
       owner_raw (str): Необработанные данные владельца.
       address (str): Адрес связанный с патентом.
       name (str): Название патента.
       actual (bool): Флаг актуальности патента, по умолчанию True.
       category (str): Категория патента.
       subcategory (str): Подкатегория патента.
       kind (int): Тип патента. Не может быть пустым.
       country_code (str): Страна правообладателя (двухбуквенный код, например RU).
       region (str): Регион, связанный с патентом.
       city (str): Город, связанный с патентом.
       author_count (int): Количество авторов патента.
       ownerships (list[Ownership]): Связь с моделью Ownership, с каскадным удалением.

    Ограничения:
       __table_args__: PrimaryKeyConstraint, который связывает поля kind и reg_number.
    """
    reg_number = Column(Integer, nullable=False, index=True)
    reg_date = Column(Date)
    appl_date = Column(Date)
    author_raw = Column(String)
    owner_raw = Column(String)
    address = Column(String)
    name = Column(String)
    actual = Column(Boolean, default=True)
    subcategory = Column(String)
    kind = Column(Integer, nullable=False)
    country_code = Column(String(length=10))
    region = Column(String)
    city = Column(String)
    author_count = Column(Integer)
    appl_number = Column(String)
    patent_starting_date = Column(Date, nullable=False)
    publication_url = Column(String(length=255))

    ownerships = relationship('Ownership', back_populates='patent', cascade="all, delete-orphan")

    __table_args__ = (
        PrimaryKeyConstraint('kind', 'reg_number'),
        {},
    )

