"""Token usage of the map agent, for its hard caps (shared by all workers)."""

from datetime import date
from uuid import UUID

from sqlalchemy import BigInteger, Date, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class AgentUsage(Base):
    __tablename__ = "agent_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
