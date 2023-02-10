from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, declarative_base
from typing_extensions import Annotated

from starlite import Starlite, dto, get
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from starlite.status_codes import HTTP_404_NOT_FOUND
from starlite.exceptions import HTTPException
from starlite.dto.sqlalchemy import SQLAlchemyFactory

sqlalchemy_plugin = SQLAlchemyPlugin()

Base = declarative_base()


class Company(Base):  # pyright: ignore
    __tablename__ = "company"

    id: Mapped[int] = Column(Integer, primary_key=True)  # pyright: ignore
    name: Mapped[str] = Column(String)  # pyright: ignore
    worth: Mapped[float] = Column(Float)  # pyright: ignore
    secret: Mapped[str] = Column(String)  # pyright: ignore


ReadCompanyDTO = SQLAlchemyFactory[Annotated[Company, dto.Config(exclude={"secret"})]]

companies: list[Company] = [
    Company(id=1, name="My Firm", worth=1000000.0, secret="secret"),
    Company(id=2, name="My New Firm", worth=1000.0, secret="abc123"),
]


@get("/{company_id: int}")
def get_company(company_id: int) -> ReadCompanyDTO:
    try:
        return ReadCompanyDTO.from_model(companies[company_id - 1])
    except IndexError:
        raise HTTPException(
            detail="Company not found",
            status_code=HTTP_404_NOT_FOUND,
        )


@get()
def get_companies() -> list[ReadCompanyDTO]:
    return [ReadCompanyDTO.from_model(company) for company in companies]


app = Starlite(
    route_handlers=[get_company, get_companies],
    plugins=[sqlalchemy_plugin],
    openapi_config=None,
)
