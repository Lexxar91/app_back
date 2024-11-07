from typing import Sequence

from fastapi import HTTPException
#import openpyxl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.filter import Filter, FilterTaxNumber
from app.schemas.filter import FilterCreate
import pandas as pd


class CRUDFilters:
    def __init__(self):
        self.model = Filter

    async def create_filter(self, session: AsyncSession, filter_data: FilterCreate, file: bytes):
        try:
            async with session.begin():
                df = pd.read_excel(file, engine='openpyxl')
                tax_numbers = df.iloc[:, 0].astype(str).apply(
                    lambda x: '0' + x if len(x) == 9 else '0' + x if len(x) == 11 else x
                ).tolist()

                new_filter = Filter(
                    name=filter_data.name,
                    filename=filter_data.filename,
                    tax_numbers_count=len(tax_numbers)
                )
                session.add(new_filter)
                await session.flush()

                tax_number_records = [FilterTaxNumber(filter_id=new_filter.id, tax_number=tn) for tn in tax_numbers]
                session.add_all(tax_number_records)

                return {
                    "name": new_filter.name,
                    "filename": new_filter.filename,
                    "id": new_filter.id,
                    "created": new_filter.created,
                    "tax_numbers_count": new_filter.tax_numbers_count
                }
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    async def get_filters(self, session: AsyncSession) -> Sequence[Filter]:
        stmt = select(self.model)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_filter(self, session: AsyncSession, filter_id: int) -> Filter:
        stmt = select(self.model).where(self.model.id == filter_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_filter_name(self, session: AsyncSession, filter_id: int, new_name: str) -> Filter:
        db_filter = await self.get_filter(session, filter_id)
        if db_filter:
            db_filter.name = new_name
            await session.commit()
            await session.refresh(db_filter)
        return db_filter

    async def delete_filter(self, session: AsyncSession, filter_id: int):
        db_filter = await self.get_filter(session, filter_id)
        if db_filter:
            await session.delete(db_filter)
            await session.commit()
        return db_filter


filter_crud = CRUDFilters()
