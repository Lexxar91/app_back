import asyncio
import logging
from http import HTTPStatus
from io import BytesIO
from typing import Optional

from aiocache import cached, Cache
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.validators import check_patent_exists
from app.core.config import settings
from app.core.db import get_async_session
from app.crud.patent import patent_crud
from app.crud.patents_export import get_export_patent_file, export_patents_task
from app.models import Patent
from app.patent_parser.parser import create_upload_file
from app.schemas.patent import (
    PatentAdditionalFields,
    PatentCreate,
    PatentDB,
    PatentUpdate,
    PatentsList,
    PatentsStats,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

router = APIRouter()


@router.get(
    '/patents',
    response_model=PatentsList,
    status_code=status.HTTP_200_OK
)
# @cached(
#     ttl=settings.cache_ttl,
#     cache=Cache.MEMORY,
#     key_builder=lambda *args, **kwargs: (
#             f"patents:{kwargs.get('page')}:{kwargs.get('pagesize')}:"
#             f"{kwargs.get('filter_id')}:{kwargs.get('kind')}:{kwargs.get('actual')}"
#     )
# )
async def list_patents(
        page: int = 1,
        pagesize: int = 10,
        filter_id: Optional[int] = None,
        kind: Optional[int] = None,
        actual: Optional[bool] = None,
        session: AsyncSession = Depends(get_async_session),
):
    """
    Получить список патентов с пагинацией и возможностью фильтрации.

    Parameters:
    - **page** (int, optional): Номер страницы для пагинации. По умолчанию 1.
    - **pagesize** (int, optional): Количество патентов на странице. По умолчанию 10.
    - **filter_id** (int, optional): ID фильтра для фильтрации по списку ИНН владельцев.
    - **kind** (int, optional): Тип патента для фильтрации:
        * 1 - Изобретение
        * 2 - Полезная модель
        * 3 - Промышленный образец
    - **actual** (bool, optional): Фильтр по актуальности патента:
        * true - только действующие патенты
        * false - только недействующие патенты

    Returns:
    - **PatentsList**: Объект, содержащий:
        * total (int): Общее количество патентов
        * items (List[Patent]): Список патентов с информацией о владельцах
    """
    logger.debug(
        f"Fetching patents with page={page}, pagesize={pagesize}, filter_id={filter_id}, kind={kind}, actual={actual}")

    if filter_id:
        patents_with_filter = await patent_crud.get_patents_list_with_filter(session, page, pagesize, filter_id)
        return patents_with_filter

    patents = await patent_crud.get_patents_list(session, page, pagesize, kind, actual)

    return patents




@router.get(
    '/patents/stats',
    response_model=PatentsStats,
    status_code=status.HTTP_200_OK
)
@cached(
    ttl=settings.cache_ttl,
    cache=Cache.MEMORY,
    key_builder=lambda *args, **kwargs: f"patents_stats:{kwargs.get('filter_id')}"
)
async def get_patents_stats(
        filter_id: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
) -> PatentsStats:
    """
   Получить статистику по патентам.

   Parameters:
   - **filter_id** (int, optional): ID фильтра для получения статистики по конкретным ИНН.
       ID фильтров начинаются с 4 и выше.

   Returns:
   - **PatentsStats**: Объект со статистикой, содержащий:
       * total_patents (int): Общее количество патентов
       * total_ru_patents (int): Количество российских патентов
       * total_with_holders (int): Количество патентов с указанными владельцами
       * total_ru_with_holders (int): Количество российских патентов с владельцами
       * with_holders_percent (int): Процент патентов с указанными владельцами
       * ru_with_holders_percent (int): Процент российских патентов с владельцами
       * by_author_count (Dict): Распределение по количеству авторов
       * by_patent_kind (Dict): Распределение по типам патентов
    """
    logger.debug(
        f"Fetching patents_stats with filter_id={filter_id}")

    stats = await patent_crud.get_stats(session, filter_id)
    return stats


@router.post(
    '/patents',
    response_model=PatentDB,
    status_code=status.HTTP_201_CREATED
)
async def create_patent(
        patent: PatentCreate,
        session: AsyncSession = Depends(get_async_session)
) -> PatentDB:
    """
   Создать новый патент.

   Parameters:
   - **patent** (PatentCreate): Объект с данными для создания патента, содержащий:
       * reg_number (int): Регистрационный номер патента
       * reg_date (date): Дата регистрации
       * kind (int): Тип патента (1 - Изобретение, 2 - Полезная модель, 3 - Промышленный образец)
       * name (str): Название патента
       * author_raw (str, optional): Список авторов
       * owner_raw (str, optional): Список владельцев
       * country_code (str, optional): Код страны правообладателя
       * ... другие опциональные поля

   Returns:
   - **PatentDB**: Созданный патент
   """
    new_patent = await patent_crud.create_object(patent, session)
    return new_patent



@router.get(
   '/patents/{patent_kind}/{patent_reg_number}',
   response_model=PatentAdditionalFields,
   status_code=status.HTTP_200_OK
)
async def get_patent(
       patent_kind: int,
       patent_reg_number: int,
       session: AsyncSession = Depends(get_async_session)
) -> PatentAdditionalFields:
    """
    Получить детальную информацию о патенте.

    Parameters:
    - **patent_kind** (int): Тип патента:
        * 1 - Изобретение
        * 2 - Полезная модель
        * 3 - Промышленный образец
    - **patent_reg_number** (int): Регистрационный номер патента

    Returns:
    - **PatentAdditionalFields**: Детальная информация о патенте, включая:
        * Все стандартные поля патента
        * owner_raw (str): Список владельцев одной строкой
        * patent_holders (List[PatentHolder]): Структурированный список владельцев
    """

    patent = await patent_crud.get_patent(session, patent_kind, patent_reg_number)
    return patent


@router.patch(
    '/patents/{patent_kind}/{patent_reg_number}',
    response_model=PatentDB,
    status_code=status.HTTP_200_OK
)
async def update_patent(
        patent_kind: int,
        patent_reg_number: int,
        obj_in: PatentUpdate,
        session: AsyncSession = Depends(get_async_session)
) -> PatentDB:
    """
    Обновить существующий патент.

    Args:
       patent_kind (int): вид патента.
       patent_reg_number (int): регистрационный номер патента.
       obj_in (PatentUpdate): данные для обновления патента.
       session (AsyncSession): асинхронная сессия базы данных.

    Returns:
       PatentDB: обновленный патент.
    """

    patent = await check_patent_exists(Patent, patent_kind, patent_reg_number, session)
    updated_patent = await patent_crud.update_object(patent, obj_in, session)
    return updated_patent


@router.delete(
    '/patents/{patent_kind}/{patent_reg_number}',
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_patent(
        patent_kind: int,
        patent_reg_number: int,
        session: AsyncSession = Depends(get_async_session)
) -> None:
    """
    Обновить существующий патент.

    Parameters:
    - **patent_kind** (int): Тип патента:
        * 1 - Изобретение
        * 2 - Полезная модель
        * 3 - Промышленный образец
    - **patent_reg_number** (int): Регистрационный номер патента
    - **obj_in** (PatentUpdate): Объект с данными для обновления:
        * name (str, optional): Новое название патента
        * actual (bool, optional): Статус актуальности
        * author_raw (str, optional): Обновленный список авторов
        * ... другие опциональные поля

    Returns:
    - **PatentDB**: Обновленный патент
    """

    patent = await check_patent_exists(Patent, patent_kind, patent_reg_number, session)
    await patent_crud.delete_object(patent, session)



@router.post(
    "/uploadfile/",
    status_code=HTTPStatus.OK
)
async def send_patent_file(file: UploadFile):
    """
    Загрузить Excel-файл с данными о патентах.

    Parameters:
    - **file** (UploadFile): Excel-файл с данными о патентах.
        Файл должен соответствовать установленному шаблону.

    Returns:
    - **Dict[str, str]**: Результат обработки файла:
        * message (str): Сообщение о результате загрузки
        * filename (str): Имя обработанного файла
    """

    return await create_upload_file(file)


@router.get(
    "/patents/export",
    response_class=StreamingResponse
)
async def export_patents(
        filter_id: Optional[int] = None,
        actual: Optional[str] = None,
        kind: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
):
    """
     Экспортировать данные о патентах в формате XLSX.

     Parameters:
     - **filter_id** (int, optional): ID фильтра для экспорта патентов по списку ИНН.
         ID фильтров начинаются с 4 и выше.
     - **actual** (str, optional): Фильтр по актуальности:
         * "Актуально" - только действующие патенты
         * "Неактуально" - только недействующие патенты
     - **kind** (int, optional): Тип патента для фильтрации:
         * 1 - Изобретение
         * 2 - Полезная модель
         * 3 - Промышленный образец

     Returns:
     - **StreamingResponse**: Поток с XLSX-файлом

     Note:
     - Без фильтров экспортируются первые 10000 патентов


     """
    task = export_patents_task.delay(filter_id, actual, kind)

    try:
        result = task.get(timeout=120)  # Синхронное ожидание с тайм-аутом
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при экспорте данных: " + str(e))

    # Убедитесь, что `result` является потоком данных
    return StreamingResponse(
        BytesIO(result),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=patents_export.xlsx"}
    )


    #return await get_export_patent_file(session, filter_id, actual, kind)


