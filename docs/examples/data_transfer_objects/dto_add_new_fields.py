from pydantic import BaseModel

from starlite.dto import DTOFactory


class MyClass(BaseModel):
    first: int
    second: int


dto_factory = DTOFactory()

MyClassDTO = dto_factory("MyClassDTO", MyClass, field_definitions={"third": (str, ...)})
