from enum import unique

from sqlalchemy import Column, Integer, Date, String, Boolean, SmallInteger
from sqlalchemy.orm import relationship

from app.core.db import Base


class Person(Base):
    """
    Модель Person.

    Атрибуты:
       kind (int): Тип лица.
       tax_number (str): Налоговый номер лица. Уникальный и индексируемый столбец. Первичный ключ.
       full_name (str): Полное имя лица.
       short_name (str): Сокращенное имя лица.
       legal_address (str): Юридический адрес лица.
       fact_address (str): Фактический адрес лица.
       reg_date (Date): Дата регистрации лица.
       active (bool): Флаг активности лица, по умолчанию True.
       category (str): Категория лица.
       okopf (str | None): Код ОКОПФ
       okvad (str | None): Код ОКВЭД
       region (str | None): Регион регистрации
       uk (int): Признак участника кластера (1 - участник, 0 - нет)
       support_type (str | None): Тип поддержки
       ownerships (list[Ownership]): Связь с моделью Ownership, с каскадным удалением.
    """
    kind = Column(Integer, nullable=False)
    tax_number = Column(String, unique=True, index=True, primary_key=True)
    full_name = Column(String)
    short_name = Column(String)
    legal_address = Column(String)
    fact_address = Column(String)
    reg_date = Column(Date)
    active = Column(Boolean, default=True)
    category = Column(String)
    okopf = Column(String)
    okvad = Column(String)
    region = Column(String)
    ogrn = Column(String, unique=True, nullable=False, comment="ОГРН организации")
    uk = Column(SmallInteger, nullable=False, comment="Участник кластера(uk=1-участник, uk=0-нет)")
    support_type = Column(String)

    ownerships = relationship('Ownership', back_populates='person', cascade="all, delete-orphan")