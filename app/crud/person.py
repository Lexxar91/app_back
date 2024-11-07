from typing import Any, Dict, Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.app_types.responses_types.response import FromPersonPatentStatsResponse
from app.crud.crud_base import CRUDBase
from app.models import Ownership, Patent
from app.models.filter import FilterTaxNumber
from app.models.person import Person


class CRUDPerson(CRUDBase):
    def __init__(self):
        super().__init__(Person)

    async def get_patents_stats(self, session: AsyncSession) -> FromPersonPatentStatsResponse:
        """
        Получает статистику по патентам:
        - Топ-5 ОКОПФ по количеству патентов + сумма остальных
        - Топ-5 ОКВЭД по количеству патентов + сумма остальных
        - Топ-5 МПК (subcategory) по количеству патентов + сумма остальных

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.

        Returns:
            Dict[str, List[Dict[str, Any]]]: Статистика по трем категориям
        """

        async def get_top_5_and_others(query) -> list[dict[str, Any]]:
            """Вспомогательная функция для получения топ-5 и суммы остальных"""
            result = await session.execute(query)

            all_data = result.all()

            if not all_data:
                return []

            top_5 = all_data[:5]

            others_sum = sum(count for _, count in all_data[5:])

            result_list = [
                {"name": name, "count": count}
                for name, count in top_5
            ]

            if others_sum > 0:
                result_list.append({"name": "Остальные", "count": others_sum})

            return result_list


        okopf_stmt = (
            select(Person.okopf, func.count(Ownership.patent_reg_number).label('patent_count'))
            .join(Ownership, Person.tax_number == Ownership.person_tax_number)
            .group_by(Person.okopf)
            .order_by(func.count(Ownership.patent_reg_number).desc())
        )


        okvad_stmt = (
            select(Person.okvad, func.count(Ownership.patent_reg_number).label('patent_count'))
            .join(Ownership, Person.tax_number == Ownership.person_tax_number)
            .group_by(Person.okvad)
            .order_by(func.count(Ownership.patent_reg_number).desc())
        )

        # Запрос по МПК (subcategory)
        mpk_stmt = (
            select(Patent.subcategory, func.count(Patent.reg_number).label('patent_count'))
            .join(Ownership,
                  (Patent.kind == Ownership.patent_kind) &
                  (Patent.reg_number == Ownership.patent_reg_number))
            .filter(Patent.kind.in_([1, 2]))
            .group_by(Patent.subcategory)
            .order_by(func.count(Patent.reg_number).desc())
        )


        stats = {
            "okopf_stats": await get_top_5_and_others(okopf_stmt),
            "okvad_stats": await get_top_5_and_others(okvad_stmt),
            "mpk_stats": await get_top_5_and_others(mpk_stmt)
        }

        return FromPersonPatentStatsResponse(**stats)

    async def get_all_stats(
            self, session: AsyncSession, filter_id: Optional[int] = None
    ) -> dict:
        """
        Статистика по персонам.

        Args:
        session (AsyncSession): асинхронная сессия базы данных.
        filter_id (Optional[int]): опциональный идентификатор загруженного фильтра по списку ИНН.

        Returns:
            dict: словарь со статистикой.
        """
        stats = {}

        total_persons_stmt = (
            select(func.count()).select_from(Person)
        )
        if filter_id is not None:
            total_persons_stmt = (
                total_persons_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        total_persons_res = await session.execute(total_persons_stmt)
        stats["total_persons"] = total_persons_res.scalar()

        by_kind_stmt = (
            select(Person.kind, func.count())
            .select_from(Person)
            .group_by(Person.kind)
        )
        if filter_id is not None:
            by_kind_stmt = (
                by_kind_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        by_kind_res = await session.execute(by_kind_stmt)
        stats["by_kind"] = {
            res[0]: res[1]
            for res in by_kind_res.all()
        }

        by_category_stmt = (
            select(Person.category, func.count())
            .select_from(Person)
            .group_by(Person.category)
        )
        if filter_id is not None:
            by_category_stmt = (
                by_category_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        by_category_res = await session.execute(by_category_stmt)
        stats["by_category"] = {
            res[0]: res[1]
            for res in by_category_res.all()
        }

        return stats

    async def get_msk_stats(
        self, session: AsyncSession, filter_id: Optional[int] = None
    ) -> dict:
        """
        Статистика по персонам (Москва).

        Args:
        session (AsyncSession): асинхронная сессия базы данных.
        filter_id (Optional[int]): опциональный идентификатор загруженного фильтра по списку ИНН.

        Returns:
            dict: словарь со статистикой.
        """
        stats = {}

        total_persons_msk_stmt = (
            select(func.count()).filter(Person.region.ilike('%москва%'))
        )
        if filter_id is not None:
            total_persons_msk_stmt = (
                total_persons_msk_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        total_persons_res = await session.execute(total_persons_msk_stmt)
        stats["total_persons"] = total_persons_res.scalar()

        by_kind_msk_stmt = (
            select(Person.kind, func.count().label("count"))
            .select_from(Person).filter(Person.region.ilike('%москва%'))
            .group_by(Person.kind)
        )
        if filter_id is not None:
            by_kind_msk_stmt = (
                by_kind_msk_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        by_kind_res = await session.execute(by_kind_msk_stmt)
        stats["by_kind"] = {
            res[0]: res[1]
            for res in by_kind_res.all()
        }

        by_category_msk_stmt = (
            select(Person.category, func.count())
            .select_from(Person).filter(Person.region.ilike('%москва%'))
            .group_by(Person.category)
        )
        if filter_id is not None:
            by_category_msk_stmt = (
                by_category_msk_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )
        by_category_res = await session.execute(by_category_msk_stmt)
        stats["by_category"] = {
            res[0]: res[1]
            for res in by_category_res.all()
        }

        by_percent_msk_cluster_stmt = (
            select(
                func.count().filter(Person.uk == 1).label("cluster_count"),
                func.count().label("total_count")
            )
            .select_from(Person)
            .filter(Person.region.ilike('%москва%'))

        )


        if filter_id is not None:
            by_percent_msk_cluster_stmt = (
                by_percent_msk_cluster_stmt
                .join(
                    FilterTaxNumber,
                    Person.tax_number == FilterTaxNumber.tax_number
                )
                .filter_by(filter_id=filter_id)
            )

        moscow_cluster_res = await session.execute(by_percent_msk_cluster_stmt)
        cluster_data = moscow_cluster_res.first()

        if cluster_data.cluster_count and cluster_data.total_count > 0:
            cluster_percentage = (cluster_data.cluster_count / cluster_data.total_count) * 100
            stats["moscow_cluster_percentage"] = round(cluster_percentage, 2)
        else:
            stats["moscow_cluster_percentage"] = 0

        by_percent_msk_support_type_stmt = (
            select(
                func.count().filter(Person.support_type.isnot(None)).label("count"),
                func.count().label("total_count")
        )
        .select_from(Person)
        .filter(Person.region.ilike('%москва%'))
        )

        moscow_support_type_res = await session.execute(by_percent_msk_support_type_stmt)

        support_type_data = moscow_support_type_res.first()

        count = support_type_data.count
        total_count = support_type_data.total_count

        support_type_percentage = (count / total_count) * 100
        stats["moscow_support_type_percentage"] = round(support_type_percentage, 2)

        return stats


    async def get_person(self, session: AsyncSession, person_tax_number: str) -> dict[str, Any]:
        """
        Получает персону по идентификатору с дополнительной информацией.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
            person_tax_number (str): Идентификатор персоны.

        Returns:
            Dict[str, Any]: Словарь с информацией о персоне, включая список патентов и количество патентов.
        """
        stmt = (
            select(Person, func.count(Ownership.patent_reg_number).label("patent_count"))
            .outerjoin(Ownership, Ownership.person_tax_number == Person.tax_number)
            .options(selectinload(Person.ownerships).selectinload(Ownership.patent))
            .group_by(Person.tax_number)
            .where(Person.tax_number == person_tax_number)
        )
        result = await session.execute(stmt)
        person, patent_count = result.unique().one_or_none()

        patents = [
            {
                "kind": ownership.patent_kind,
                "reg_number": ownership.patent_reg_number
            }
            for ownership in person.ownerships
        ]

        return {
            **person.__dict__,
            "category": person.category,
            "patents": patents,
            "patent_count": len(patents),
        }


person_crud = CRUDPerson()
