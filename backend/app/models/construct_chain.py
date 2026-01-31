import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import GUID


class ConstructChain(Base):
    __tablename__ = "construct_chain"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    construct_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("construct.id", ondelete="CASCADE"), nullable=False
    )
    chain_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("chain.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
