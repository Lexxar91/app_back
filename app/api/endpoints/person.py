from aiocache import cached, Cache
from fastapi import APIRouter, Depends, HTTPException
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

import logging

from app.api.validators import check_person_exists
from app.core.config import settings
from app.core.db import get_async_session
from app.crud.person import person_crud
from app.models import Person
from app.schemas.person import (
    PersonsList,
    PersonAdditionalFields,
    PersonCreate,
    PersonDB,
    PersonUpdate, PersonsAllStats, PersonsMskStats,
)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

router = APIRouter()


@router.get(
    "/persons",
    response_model=PersonsList,
    status_code=HTTPStatus.OK
)
@cached(
    ttl=settings.cache_ttl,
    cache=Cache.MEMORY,
    key_builder=lambda *args, **kwargs: (
            f"persons:{kwargs.get('page')}:{kwargs.get('pagesize')}:"
            f"{kwargs.get('kind')}:{kwargs.get('active')}:{kwargs.get('category')}")
)
async def patents_stats(
        session: AsyncSession = Depends(get_async_session),
        # page: int = 1,
        # pagesize: int = 10,
        # kind: Optional[int] = None,
        # active: Optional[bool] = None,
        # category: Optional[int] = None
) -> PersonsList:

    """
    Получение статистики по патентам в разрезе различных категорий.

    Возвращает статистику распределения патентов по следующим категориям:
    * Топ-5 кодов ОКОПФ (Организационно-правовая форма) + прочие
    * Топ-5 кодов ОКВЭД (Вид экономической деятельности) + прочие
    * Топ-5 подкатегорий МПК (Международная патентная классификация) + прочие
    """
    persons = await person_crud.get_patents_stats(session)
    return persons



@router.get(
    "/persons/all_stats",
    response_model=PersonsAllStats,
    status_code=HTTPStatus.OK
)
# @cached(
#     ttl=settings.cache_ttl,
#     cache=Cache.MEMORY,
#     key_builder=lambda *args, **kwargs: (
#             f"persons_stats:{kwargs.get('filter_id')}:")
# )
async def get_persons_all_stats(
        filter_id: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
) -> PersonsAllStats:
    """
    Получение общей статистики по всем лицам.

    Parameters:
        filter_id (int, опционально): Идентификатор фильтра для списка ИНН.
    """
    logger.debug(
        f"Fetching persons_stats with filter_id={filter_id}")

    stats = await person_crud.get_all_stats(session, filter_id)
    return stats


@router.get(
    "/persons/msk_stats",
    response_model=PersonsMskStats,
    status_code=HTTPStatus.OK
)
async def get_persons_msk_stats(
        filter_id: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
) -> PersonsMskStats:
    """
    Получение статистики по лицам, зарегистрированным в Москве.

    Args:
        filter_id (Optional[int]): опциональный идентификатор загруженного фильтра по списку ИНН.
         session (AsyncSession): асинхронная сессия базы данных.

    Returns:
        PersonsStats: словарь со статистикой.
    """
    logger.debug(
        f"Fetching persons_stats with filter_id={filter_id}")

    stats = await person_crud.get_msk_stats(session, filter_id)
    return stats


@router.post(
    "/persons",
    response_model=PersonDB,
    status_code=HTTPStatus.CREATED
)
async def create_person(
        person: PersonCreate,
        session: AsyncSession = Depends(get_async_session)
) -> PersonDB:
    """
   Создание новой записи о лице.

   Parameters:
       person (PersonCreate): Объект с данными о лице, содержащий следующие поля:
           * kind (int): Вид лица (1 - Юридическое лицо, 2 - ИП, 3 - Физическое лицо)
           * tax_number (str): ИНН
           * full_name (str, опционально): Полное наименование
           * short_name (str, опционально): Сокращенное наименование
           * legal_address (str, опционально): Юридический адрес
           * fact_address (str, опционально): Фактический адрес
           * reg_date (date, опционально): Дата регистрации
           * active (bool): Статус активности
           * okopf (str, опционально): Код ОКОПФ
           * okvad (str, опционально): Код ОКВЭД
           * region (str, опционально): Регион регистрации
           * uk (int): Признак участника кластера (1 - участник, 0 - не участник)
           * support_type (str, опционально): Тип поддержки

   Returns:
       PersonDB: Созданный объект лица
   """

    new_person = await person_crud.create_object(person, session)
    return new_person



@router.get(
    "/persons/{person_tax_number}",
    response_model=PersonAdditionalFields,
    status_code=HTTPStatus.OK
)
async def get_person(
        person_tax_number: str,
        session: AsyncSession = Depends(get_async_session)
) -> PersonAdditionalFields:
    """
    Получение подробной информации о лице по ИНН.

    Parameters:
        person_tax_number (str): ИНН лица

    Returns:
        Объект PersonAdditionalFields, содержащий:
            * Все базовые поля лица
            * category (str): Категория лица
            * patents (list): Список связанных патентов с их видами и регистрационными номерами
            * patent_count (int): Общее количество патентов
    """

    person = await person_crud.get_person(session, person_tax_number)
    return person




@router.patch(
    '/persons/{person_tax_number}',
    response_model=PersonDB,
    status_code=HTTPStatus.OK
)
async def update_person(
        person_tax_number: str,
        obj_in: PersonUpdate,
        session: AsyncSession = Depends(get_async_session)
) -> PersonDB:
    """
    Обновление информации о существующем лице.

    Args:
        person_tax_number (str): идентификационный номер персоны.
        obj_in (PersonUpdate): данные для обновления персоны.
        session (AsyncSession): асинхронная сессия базы данных.

    Returns:
        PersonDB: обновленная персона.
    """

    person = await check_person_exists(Person, person_tax_number, session)
    updated_person = await person_crud.update_object(person, obj_in, session)
    return updated_person




@router.delete('/persons/{person_tax_number}', status_code=HTTPStatus.NO_CONTENT)
async def delete_person(
        person_tax_number: str,
        session: AsyncSession = Depends(get_async_session)
) -> None:
    """
    Удаление лица по ИНН.

    Args:
        person_tax_number(int): идентификационный номер персоны.
        session (AsyncSession): асинхронная сессия базы данных.
    """

    person = await check_person_exists(Person, person_tax_number, session)
    await person_crud.delete_object(person, session)


