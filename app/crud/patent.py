from typing import Dict, Any, Optional

from sqlalchemy import case, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.crud_base import CRUDBase
from app.models import Ownership, Person
from app.models.filter import FilterTaxNumber
from app.models.patent import Patent

from app.app_types.responses_types.response import PatentListResponse, PatentHolder, PatentStatsResponse


class CRUDPatent(CRUDBase):
    """
    Класс для выполнения CRUD операций с патентами.

    Attributes:
        model: Модель Patent, с которой работает CRUD.
    """

    def __init__(self):
        super().__init__(Patent)

    async def get_patents_list(
            self,
            session: AsyncSession,
            page: int,
            pagesize: int,
            kind: Optional[int] = None,
            actual: Optional[bool] = None
    ) -> PatentListResponse:
        """
        Получает постраничный список патентов с информацией о владельцах.

        Args:
            session: Асинхронная сессия базы данных.
            page: Номер страницы для пагинации (начиная с 1).
            pagesize: Количество элементов на странице.
            kind: Опциональный фильтр по типу патента.
            actual: Опциональный фильтр по актуальности патента.

        Returns:
            PatentListResponse: Словарь, содержащий:
                - total: общее количество патентов
                - items: список патентов с информацией о владельцах

        """
        skip = (page - 1) * pagesize
        stmt = (
            select(Patent)
            .outerjoin(Ownership,
                       (Ownership.patent_kind == Patent.kind) & (Ownership.patent_reg_number == Patent.reg_number))
            .outerjoin(Person, Person.tax_number == Ownership.person_tax_number)
            .options(selectinload(Patent.ownerships).selectinload(Ownership.person))
            .group_by(Patent.kind, Patent.reg_number)
            .order_by(Patent.actual.desc())
            .offset(skip)
            .limit(pagesize)
        )
        if kind is not None:
            stmt = stmt.where(Patent.kind == kind)
        if actual is not None:
            stmt = stmt.where(Patent.actual == actual)

        result = await session.execute(stmt)
        patents = result.all()

        patents_list = []
        for patent in patents:
            patent_holders = [
                PatentHolder(
                    tax_number=ownership.person.tax_number,
                    full_name=ownership.person.full_name,
                )
                for ownership in patent[0].ownerships
            ]
            patents_list.append({
                **patent[0].__dict__,
                "patent_holders": patent_holders,
            })

        total = await session.execute(
            select(func.count()).select_from(Patent))

        return PatentListResponse(
            total=total.scalar(),
            items=patents_list,
        )

    async def get_patent(
            self,
            session: AsyncSession,
            patent_kind: int,
            patent_reg_number: int
    ) -> Dict[str, Any]:
        """
        Получает детальную информацию о патенте по его идентификатору и типу.

        Args:
            session: Асинхронная сессия базы данных.
            patent_kind: Тип патента (1 - изобретение, 2 - полезная модель, 3 - промышленный образец).
            patent_reg_number: Регистрационный номер патента.

        Returns:
            Dict[str, Any]: Словарь с информацией о патенте, содержащий:
                - все поля модели Patent
                - owner_raw: строка с именами владельцев, разделенными запятыми
                - patent_holders: список словарей с информацией о владельцах

      """
        stmt = (
            select(
                Patent,
                func.string_agg(Person.short_name, ', ').label("owner_raw"),
                func.coalesce(
                    func.array_length(func.string_to_array(Patent.author_raw, ', '), 1).label('author_count'),
                    0
                )
            )
            .outerjoin(Ownership,
                       (Ownership.patent_kind == Patent.kind) & (Ownership.patent_reg_number == Patent.reg_number))
            .outerjoin(Person, Person.tax_number == Ownership.person_tax_number)
            .options(selectinload(Patent.ownerships).selectinload(Ownership.person))
            .group_by(Patent.kind, Patent.reg_number)
            .where((Patent.kind == patent_kind) & (Patent.reg_number == patent_reg_number))
        )
        result = await session.execute(stmt)
        patent, owner_raw, author_count = result.one()

        patent_holders = [
            PatentHolder(
                tax_number=ownership.person.tax_number,
                full_name=ownership.person.full_name,
            )
            for ownership in patent.ownerships
        ]

        return {
            **patent.__dict__,
            "owner_raw": owner_raw,
            "patent_holders": patent_holders,
        }

    async def get_stats(
            self,
            session: AsyncSession,
            filter_id: Optional[int] = None
    ) -> PatentStatsResponse:
        """
        Получает статистику по патентам с возможностью фильтрации по списку ИНН.

        Args:
            session: Асинхронная сессия базы данных.
            filter_id: Опциональный идентификатор фильтра по списку ИНН.

        Returns:
            PatentStatsResponse: Словарь со статистикой, содержащий:
                - total_patents: общее количество патентов
                - total_ru_patents: количество российских патентов
                - total_with_holders: количество патентов с указанными владельцами
                - total_ru_with_holders: количество российских патентов с указанными владельцами
                - with_holders_percent: процент патентов с указанными владельцами
                - ru_with_holders_percent: процент российских патентов с указанными владельцами
                - by_author_count: распределение по количеству авторов
                - by_patent_kind: распределение по типам патентов
        """
        stats: Dict[str, Any] = {}

        total_patents_stmt = (
            select(func.count()).select_from(Patent)
        )
        if filter_id is not None:
            total_patents_stmt = (
                total_patents_stmt
                .join(Ownership)
                .join(
                    FilterTaxNumber,
                    Ownership.person_tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        total_patents_res = await session.execute(total_patents_stmt)
        stats["total_patents"] = total_patents_res.scalar()

        total_patents_ru_stmt = (
            select(func.count()).select_from(Patent).filter_by(country_code="RU")
        )
        if filter_id is not None:
            total_patents_ru_stmt = (
                total_patents_ru_stmt
                .join(Ownership)
                .join(
                    FilterTaxNumber,
                    Ownership.person_tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        total_patents_ru_res = await session.execute(total_patents_ru_stmt)
        stats["total_ru_patents"] = total_patents_ru_res.scalar()

        total_with_holders_stmt = (
            select(func.count(func.distinct(Patent.kind, Patent.reg_number)))
            .select_from(Patent)
            .join(Ownership)
        )
        if filter_id is not None:
            total_with_holders_stmt = (
                total_with_holders_stmt
                .join(
                    FilterTaxNumber,
                    Ownership.person_tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        total_with_holders_res = await session.execute(total_with_holders_stmt)
        stats["total_with_holders"] = total_with_holders_res.scalar()

        total_ru_with_holders_stmt = (
            select(func.count(func.distinct(Patent.kind, Patent.reg_number)))
            .select_from(Patent)
            .filter_by(country_code="RU")
            .join(Ownership)
        )
        if filter_id is not None:
            total_ru_with_holders_stmt = (
                total_ru_with_holders_stmt
                .join(
                    FilterTaxNumber,
                    Ownership.person_tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        total_ru_with_holders_res = await session.execute(total_ru_with_holders_stmt)
        stats["total_ru_with_holders"] = total_ru_with_holders_res.scalar()

        stats["with_holders_percent"] = int(round(
            100 * stats["total_with_holders"] / stats["total_patents"]))
        stats["ru_with_holders_percent"] = int(round(
            100 * stats["total_ru_with_holders"] / stats["total_ru_patents"]))

        by_author_count_stmt = (
            select(
                case(
                    (Patent.author_count == 0, "0"),
                    (Patent.author_count == 1, "1"),
                    (Patent.author_count <= 5, "2–5"),
                    else_="5+"
                ).label("author_count_group"),
                func.count()
            )
            .select_from(Patent)
            .group_by("author_count_group")
        )
        if filter_id is not None:
            by_author_count_stmt = (
                by_author_count_stmt
                .join(Ownership)
                .join(
                    FilterTaxNumber,
                    Ownership.person_tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        by_author_count_res = await session.execute(by_author_count_stmt)
        stats["by_author_count"] = {
            row[0]: row[1]
            for row in by_author_count_res.all()
        }

        by_patent_kind_stmt = (
            select(Patent.kind, func.count())
            .select_from(Patent)
            .group_by(Patent.kind)
        )
        if filter_id is not None:
            by_patent_kind_stmt = (
                by_patent_kind_stmt
                .join(Ownership)
                .join(
                    FilterTaxNumber,
                    Ownership.person_tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        by_patent_kind_res = await session.execute(by_patent_kind_stmt)
        stats["by_patent_kind"] = {
            res[0]: res[1]
            for res in by_patent_kind_res.all()
        }

        return PatentStatsResponse(**stats)

    async def get_patents_list_with_filter(
            self,
            session: AsyncSession,
            page: int,
            pagesize: int,
            filter_id: int
    ) -> PatentListResponse:
        """
        Получает постраничный список патентов, отфильтрованный по списку ИНН владельцев.

        Args:
            session: Асинхронная сессия базы данных.
            page: Номер страницы для пагинации (начиная с 1).
            pagesize: Количество элементов на странице.
            filter_id: Идентификатор фильтра со списком ИНН.

        Returns:
            PatentListResponse: Словарь, содержащий:
                - total: общее количество патентов, соответствующих фильтру
                - items: список отфильтрованных патентов с информацией о владельцах

        """
        skip = (page - 1) * pagesize

        # Получаем список ИНН из фильтра
        tax_numbers_stmt = select(FilterTaxNumber.tax_number).where(FilterTaxNumber.filter_id == filter_id)
        tax_numbers_result = await session.execute(tax_numbers_stmt)
        tax_numbers = [row[0] for row in tax_numbers_result.all()]

        # Формируем запрос на получение патентов
        stmt = (
            select(Patent)
            .outerjoin(Ownership,
                       (Ownership.patent_kind == Patent.kind) & (Ownership.patent_reg_number == Patent.reg_number))
            .outerjoin(Person, Person.tax_number == Ownership.person_tax_number)
            .where(Person.tax_number.in_(tax_numbers))
            .options(selectinload(Patent.ownerships).selectinload(Ownership.person))
            .group_by(Patent.kind, Patent.reg_number)
            .offset(skip)
            .limit(pagesize)
        )

        result = await session.execute(stmt)
        patents = result.all()

        patents_list = []
        for patent in patents:
            patent_holders = [
                PatentHolder(
                    tax_number=ownership.person.tax_number,
                    full_name=ownership.person.full_name,
                )
                for ownership in patent[0].ownerships
            ]

            patents_list.append({
                **patent[0].__dict__,
                "patent_holders": patent_holders,
            })

        total = await session.execute(
            select(func.count())
            .select_from(Patent)
            .outerjoin(Ownership)
            .where(Ownership.person_tax_number.in_(tax_numbers)))

        return PatentListResponse(
            total=total.scalar(),
            items=patents_list,
        )


patent_crud = CRUDPatent()
