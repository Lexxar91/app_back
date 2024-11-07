import asyncio
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import Optional

import aiofiles

from fastapi import HTTPException
from openpyxl.workbook import Workbook

from sqlalchemy import select, func, case, literal_column, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import StreamingResponse

from app.celery_worker import celery_app
from app.core.db import AsyncSessionLocal, engine
import logging
from app.models import Patent, Person, Ownership
from app.models.filter import FilterTaxNumber

logger = logging.getLogger(__name__)
async def get_export_patent_file(
        session: AsyncSession,
        filter_id: Optional[int] = None,
        actual: Optional[str] = None,
        kind: Optional[int] = None,

):
    """
    Получает данные о патентах и экспортирует их в файл XLSX.

    Args:
        session (AsyncSession): Сессия для взаимодействия с базой данных.

        filter_id (Optional[int], optional): Идентификатор фильтра. Если указан, будут экспортированы только
            патенты, связанные с этим фильтром. Если не указан, будут экспортированы первые 10000 патентов.

        actual (Optional[str], optional): Фильтр по актуальности патента. Если "Актуально", будут экспортированы
            только актуальные патенты. Если "Неактуально", будут экспортированы только неактуальные патенты.
            Если не указан, актуальность не будет учитываться.

        kind (Optional[int], optional): Фильтр по виду патента. Если указан, будут экспортированы только патенты
            указанного вида (1 - изобретение, 2 - полезная модель, 3 - промышленный образец).

    Returns:
        StreamingResponse: Поток данных с XLSX-файлом, содержащим информацию о патентах.
        """
    author_count_subquery = (
        select(
            Patent.reg_number.label('patent_reg_number'),
            Patent.kind.label('patent_kind'),
            func.coalesce(func.array_length(func.string_to_array(Patent.author_raw, ','), 1), 0).label('author_count')
        ).subquery()
    )

    stmt = (
        select(
            Patent.reg_number,
            case(
                (Patent.kind == 1, literal_column("'изобретение'")),
                (Patent.kind == 2, literal_column("'полезная модель'")),
                (Patent.kind == 3, literal_column("'промышленный образец'")),
                else_=literal_column("'неизвестно'")
            ).label('patent_kind'),
            Patent.reg_date,
            Patent.name,
            Patent.actual,
            Patent.subcategory,
            Patent.region,
            Patent.city,
            author_count_subquery.c.author_count,
            Person.tax_number,
            case(
                (Person.kind == 1, literal_column("'Юрлицо'")),
                (Person.kind == 2, literal_column("'Физлицо/ИП'")),
                else_=literal_column("'неизвестно'")
            ).label('person_kind'),
            Person.category.label("person_category"),
            Person.full_name,
        )
        .select_from(Patent)
        .join(Ownership, and_(Ownership.patent_kind == Patent.kind, Ownership.patent_reg_number == Patent.reg_number))
        .join(Person, Person.tax_number == Ownership.person_tax_number)
        .join(author_count_subquery, and_(
            author_count_subquery.c.patent_reg_number == Patent.reg_number,
            author_count_subquery.c.patent_kind == Patent.kind
        ))
        .order_by(Patent.reg_number)
        .limit(10000)
    )

    if filter_id:
        stmt = stmt.join(FilterTaxNumber, Person.tax_number == FilterTaxNumber.tax_number)
        stmt = stmt.where(FilterTaxNumber.filter_id == filter_id)

    if actual:
        actual_casefold = actual.casefold()
        if actual_casefold == 'актуально':
            stmt = stmt.where(Patent.actual == True)
        elif actual_casefold == "неактуально":
            stmt = stmt.where(Patent.actual == False)
        else:
            raise HTTPException(
                status_code=400,
                detail="Некорректное значение для параметра 'actual'. Ожидается 'актуально' или 'неактуально'."
            )

    if kind:
        stmt = stmt.where(Patent.kind == kind)

    headers = [
        "ИНН", "Вид", "Категория", "Полное наименование", "Регистрационный номер патента",
        "Вид патента", "Дата регистрации", "Название", "Актуальность патента",
        "Индекс класса по МПК", "Индекс подкласса по МПК", "Регион правообладателя",
        "Город правообладателя", "Число авторов"
    ]

    with NamedTemporaryFile(delete=False) as temp_file:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title="Patents")
        ws.append(headers)

        result = await session.execute(stmt)
        for row in result:
            row_data = [
                row.tax_number,
                row.person_kind,
                row.person_category,
                row.full_name,
                row.reg_number,
                row.patent_kind,
                row.reg_date,
                row.name,
                row.actual,
                row.subcategory,
                row.region,
                row.city,
                row.author_count
            ]
            ws.append(row_data)

        wb.save(temp_file.name)

        async with aiofiles.open(temp_file.name, mode="rb") as f:
            content = await f.read()

    return StreamingResponse(
        BytesIO(content),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=patents_export.xlsx"}
    )

@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def export_patents_task(
        self,
        filter_id: Optional[int] = None,
        actual: Optional[str] = None,
        kind: Optional[int] = None
):
    """
    Celery-задача для асинхронного вызова функции экспорта патентов.
    """
    try:
        logger.info("Starting export_patents_task with filter_id=%s, actual=%s, kind=%s", filter_id, actual, kind)

        # Создаем асинхронный код в отдельной функции
        async def run_export_task():
            async with AsyncSessionLocal() as session:
                response =  await get_export_patent_file(session, filter_id, actual, kind)
                print(response)
                return response.body()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_export_task())
        loop.close()

        logger.info("Task completed successfully")
        return result

    except Exception as e:
        logger.error("Error in export_patents_task: %s", str(e))
        raise self.retry(exc=e)



