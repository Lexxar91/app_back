from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.encoders import jsonable_encoder


class CRUDBase:
    """
    Базовый класс для CRUD (Create, Read, Update, Delete) операций с объектами базы данных.
    :param model: SQLAlchemy модель, с которой будет выполняться CRUD.
    """

    def __init__(self, model):
        self.model = model

    async def get_all_objects(self, session: AsyncSession):
        all_objects = await session.execute(select(self.model))
        return all_objects.scalars().all()

    async def get_object(self, obj_id: int, session: AsyncSession):
        db_obj = await session.execute(select(self.model).where(self.model.id == obj_id))
        return db_obj.scalars().first()

    async def create_object(self, obj_in, session: AsyncSession):
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update_object(self, db_obj, obj_in, session: AsyncSession):
        obj_data = jsonable_encoder(db_obj)
        update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete_object(self, db_obj, session: AsyncSession):
        await session.delete(db_obj)
        await session.commit()
        return db_obj


crud = CRUDBase(model=None)

