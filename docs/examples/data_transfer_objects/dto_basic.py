from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, declarative_base

from starlite.dto.sqlalchemy import SQLAlchemyFactory

Base = declarative_base()


class Company(Base):  # pyright: ignore
    __tablename__ = "company"
    id: Mapped[int] = Column(Integer, primary_key=True)  # pyright: ignore
    name: Mapped[str] = Column(String)  # pyright: ignore
    worth: Mapped[float] = Column(Float)  # pyright: ignore


CompanyDTO = SQLAlchemyFactory[Company]
