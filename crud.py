from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from model import EmailLog
from schema import EmailLogCreate


class EmailLogCRUD:
    async def create(self, db: AsyncSession, log_data: EmailLogCreate):
        
        log = EmailLog(**log_data.dict())
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    async def get_multi(self, db: AsyncSession):
       
        statement = select(EmailLog)
        result = await db.execute(statement)
        return result.scalars().all()

    async def get(self, db: AsyncSession, id: int):
       
        statement = select(EmailLog).where(EmailLog.id == id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()



crud_email_logs = EmailLogCRUD()
