from datetime import date, datetime, time, timedelta
from decimal import Decimal
from inspect import isclass
from ipaddress import IPv4Network, IPv6Network
from typing import TYPE_CHECKING, Dict, List, Tuple, Union
from uuid import UUID

from pydantic import BaseConfig, BaseModel, conint, constr, create_model
from pydantic_factories import ModelFactory
from pydantic_openapi_schema.utils.utils import OpenAPI310PydanticSchema

from starlite.di import Provide
from starlite.exceptions import (
    ImproperlyConfiguredException,
    MissingDependencyException,
)
from starlite.plugins.base import InitPluginProtocol
from starlite.plugins.pydantic import FromPydantic

from ..utils import remap_field

try:
    from sqlalchemy import inspect
    from sqlalchemy import types as sqlalchemy_type
    from sqlalchemy.dialects import mssql, mysql, oracle, postgresql, sqlite
    from sqlalchemy.exc import NoInspectionAvailable
    from sqlalchemy.orm import DeclarativeMeta, InstanceState, Mapper
    from sqlalchemy.sql.type_api import TypeEngine
except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e


if TYPE_CHECKING:
    from typing import Any, Callable, Mapping

    from pydantic_openapi_schema.v3_1_0 import Schema
    from typing_extensions import TypeGuard

    from starlite.app import Starlite
    from starlite.plugins.sql_alchemy.config import SQLAlchemyConfig

    from .types import SQLAlchemyBinaryType


class SQLAlchemyPlugin(InitPluginProtocol, FromPydantic[DeclarativeMeta]):
    """A Plugin for SQLAlchemy."""

    __slots__ = ("_model_namespace_map", "_config")

    def __init__(self, config: "SQLAlchemyConfig | None" = None) -> None:
        """Initialize ``SQLAlchemyPlugin``.

        Support (de)serialization and OpenAPI generation for SQLAlchemy
        ORM types.

        Args:
            config: Optional :class:`SQLAlchemyConfig <starlite.plugins.sql_alchemy.SQLAlchemyConfig>` instance. If
                passed, the plugin will establish a DB connection and hook handlers and dependencies.
        """
        self._model_namespace_map: "dict[str, type[BaseModel]]" = {}
        self._config = config

    def on_app_init(self, app: "Starlite") -> None:
        """If config has been passed to the plugin, it will initialize SQLAlchemy and add the dependencies as expected.

        Executed on the application's init process.

        Args:
            app: The :class:`Starlite <starlite.app.Starlite>` application instance.

        Returns:
            None
        """
        if self._config is not None:
            app.dependencies[self._config.dependency_key] = Provide(self._config.create_db_session_dependency)
            app.before_send.append(self._config.before_send_handler)  # type: ignore[arg-type]
            app.on_shutdown.append(self._config.on_shutdown)
            self._config.config_sql_alchemy_logging(app.logging_config)
            self._config.update_app_state(state=app.state)

    @staticmethod
    def is_plugin_supported_type(value: "Any") -> "TypeGuard[DeclarativeMeta]":
        """:class:`typing.TypeGuard` testing whether values are subclasses of SQLAlchemy's ``DeclarativeMeta`` class.

        Args:
            value: An arbitrary type to test.

        Returns:
            A boolean typeguard.
        """
        try:
            inspected = inspect(value)
        except NoInspectionAvailable:
            return False
        return isinstance(inspected, (Mapper, InstanceState))

    @staticmethod
    def handle_string_type(column_type: "sqlalchemy_type.String | SQLAlchemyBinaryType") -> "type":
        """Handle the SQLAlchemy String types, including Blob and Binary types.

        Args:
            column_type: The type of the SQLColumn.

        Returns:
            An appropriate string type
        """
        if column_type.length is not None:
            return constr(max_length=column_type.length)
        return str

    @staticmethod
    def handle_numeric_type(column_type: sqlalchemy_type.Numeric) -> "type":
        """Handle the SQLAlchemy non-int Numeric types.

        Args:
            column_type: The type of the SQLColumn.

        Returns:
            An appropriate numerical type
        """
        if column_type.asdecimal:
            return Decimal
        return float

    def handle_list_type(self, column_type: sqlalchemy_type.ARRAY) -> "Any":
        """Handle the SQLAlchemy Array type.

        Args:
            column_type: The type of the SQLColumn.

        Returns:
            An appropriate list type
        """
        list_type: "Any" = self.get_pydantic_type(column_type=column_type.item_type)

        dimensions = column_type.dimensions or 1
        while dimensions > 0:
            list_type = List[list_type]
            dimensions -= 1
        return list_type

    def handle_tuple_type(self, column_type: sqlalchemy_type.TupleType) -> "Any":
        """Handle the SQLAlchemy Tuple type.

        Args:
            column_type: The type of the SQLColumn.

        Returns:
            An appropriate tuple type
        """
        types = [self.get_pydantic_type(column_type=t) for t in column_type.types]
        return Tuple[tuple(types)]

    @staticmethod
    def handle_enum(column_type: "sqlalchemy_type.Enum | mysql.ENUM | postgresql.ENUM") -> "Any":
        """Handle the SQLAlchemy Enum types.

        Args:
            column_type: The type of the SQLColumn.

        Returns:
            An appropriate enum type
        """
        return column_type.enum_class  # type:ignore[union-attr]

    @property
    def providers_map(self) -> "dict[type[TypeEngine], Callable[[TypeEngine | type[TypeEngine]], Any]]":
        """Map of SQLAlchemy column types to provider functions.

        This method is separated to allow for easy overriding in
        subclasses.

        Returns
            A dictionary mapping SQLAlchemy types to callables.
        """
        return {
            sqlalchemy_type.ARRAY: self.handle_list_type,
            sqlalchemy_type.BIGINT: lambda x: int,
            sqlalchemy_type.BINARY: self.handle_string_type,
            sqlalchemy_type.BLOB: self.handle_string_type,
            sqlalchemy_type.BOOLEAN: lambda x: bool,
            sqlalchemy_type.BigInteger: lambda x: int,
            sqlalchemy_type.Boolean: lambda x: bool,
            sqlalchemy_type.CHAR: self.handle_string_type,
            sqlalchemy_type.CLOB: self.handle_string_type,
            sqlalchemy_type.DATE: lambda x: date,
            sqlalchemy_type.DATETIME: lambda x: datetime,
            sqlalchemy_type.DECIMAL: self.handle_numeric_type,
            sqlalchemy_type.Date: lambda x: date,
            sqlalchemy_type.DateTime: lambda x: datetime,
            sqlalchemy_type.Enum: self.handle_enum,
            sqlalchemy_type.FLOAT: self.handle_numeric_type,
            sqlalchemy_type.Float: self.handle_numeric_type,
            sqlalchemy_type.INT: lambda x: int,
            sqlalchemy_type.INTEGER: lambda x: int,
            sqlalchemy_type.Integer: lambda x: int,
            sqlalchemy_type.Interval: lambda x: timedelta,
            sqlalchemy_type.JSON: lambda x: Union[dict, list],
            sqlalchemy_type.LargeBinary: self.handle_string_type,
            sqlalchemy_type.NCHAR: self.handle_string_type,
            sqlalchemy_type.NUMERIC: self.handle_numeric_type,
            sqlalchemy_type.NVARCHAR: self.handle_string_type,
            sqlalchemy_type.Numeric: self.handle_numeric_type,
            sqlalchemy_type.REAL: self.handle_numeric_type,
            sqlalchemy_type.SMALLINT: lambda x: int,
            sqlalchemy_type.SmallInteger: lambda x: int,
            sqlalchemy_type.String: self.handle_string_type,
            sqlalchemy_type.TEXT: self.handle_string_type,
            sqlalchemy_type.TIME: lambda x: time,
            sqlalchemy_type.TIMESTAMP: lambda x: datetime,
            sqlalchemy_type.Text: self.handle_string_type,
            sqlalchemy_type.Time: lambda x: time,
            sqlalchemy_type.TupleType: self.handle_tuple_type,  # pyright: ignore
            sqlalchemy_type.Unicode: self.handle_string_type,
            sqlalchemy_type.UnicodeText: self.handle_string_type,
            sqlalchemy_type.VARBINARY: self.handle_string_type,
            sqlalchemy_type.VARCHAR: self.handle_string_type,
            # mssql
            mssql.BIT: lambda x: bool,
            mssql.DATETIME2: lambda x: datetime,
            mssql.DATETIMEOFFSET: lambda x: datetime,
            mssql.IMAGE: self.handle_string_type,
            mssql.MONEY: lambda x: Decimal,
            mssql.NTEXT: self.handle_string_type,
            mssql.REAL: self.handle_numeric_type,
            mssql.SMALLDATETIME: lambda x: datetime,
            mssql.SMALLMONEY: lambda x: Decimal,
            mssql.SQL_VARIANT: lambda x: str,
            mssql.TIME: lambda x: time,
            mssql.TINYINT: lambda x: int,
            mssql.UNIQUEIDENTIFIER: lambda x: str,
            mssql.VARBINARY: self.handle_string_type,
            mssql.XML: self.handle_string_type,
            # mysql
            mysql.BIGINT: lambda x: int,
            mysql.BIT: lambda x: bool,
            mysql.CHAR: self.handle_string_type,
            mysql.DATETIME: lambda x: datetime,
            mysql.DECIMAL: self.handle_numeric_type,
            mysql.DOUBLE: self.handle_numeric_type,
            mysql.ENUM: self.handle_enum,
            mysql.FLOAT: self.handle_numeric_type,
            mysql.INTEGER: lambda x: int,
            mysql.JSON: lambda x: Union[dict, list],
            mysql.LONGBLOB: self.handle_string_type,
            mysql.LONGTEXT: self.handle_string_type,
            mysql.MEDIUMBLOB: self.handle_string_type,
            mysql.MEDIUMINT: lambda x: int,
            mysql.MEDIUMTEXT: self.handle_string_type,
            mysql.NCHAR: self.handle_string_type,
            mysql.NUMERIC: self.handle_numeric_type,
            mysql.NVARCHAR: self.handle_string_type,
            mysql.REAL: self.handle_numeric_type,
            mysql.SET: lambda x: set,
            mysql.SMALLINT: lambda x: int,
            mysql.TEXT: self.handle_string_type,
            mysql.TIME: lambda x: time,
            mysql.TIMESTAMP: lambda x: datetime,
            mysql.TINYBLOB: self.handle_string_type,
            mysql.TINYINT: lambda x: int,
            mysql.TINYTEXT: self.handle_string_type,
            mysql.VARCHAR: self.handle_string_type,
            mysql.YEAR: lambda x: conint(ge=1901, le=2155),
            # oracle
            oracle.BFILE: self.handle_string_type,
            oracle.BINARY_DOUBLE: self.handle_numeric_type,
            oracle.BINARY_FLOAT: self.handle_numeric_type,
            oracle.DATE: lambda x: datetime,  # supports time
            oracle.DOUBLE_PRECISION: self.handle_numeric_type,
            oracle.INTERVAL: lambda x: timedelta,
            oracle.LONG: self.handle_string_type,
            oracle.NCLOB: self.handle_string_type,
            oracle.NUMBER: self.handle_numeric_type,
            oracle.RAW: self.handle_string_type,
            oracle.VARCHAR2: self.handle_string_type,
            oracle.VARCHAR: self.handle_string_type,
            # postgresql
            postgresql.ARRAY: self.handle_list_type,
            postgresql.BIT: lambda x: bool,
            postgresql.BYTEA: self.handle_string_type,
            postgresql.CIDR: lambda x: Union[IPv4Network, IPv6Network],
            postgresql.DATERANGE: lambda x: Tuple[date, date],
            postgresql.DOUBLE_PRECISION: self.handle_numeric_type,
            postgresql.ENUM: self.handle_enum,
            postgresql.HSTORE: lambda x: Dict[str, str],
            postgresql.INET: lambda x: Union[IPv4Network, IPv6Network],
            postgresql.INT4RANGE: lambda x: Tuple[int, int],
            postgresql.INT8RANGE: lambda x: Tuple[int, int],
            postgresql.INTERVAL: lambda x: timedelta,
            postgresql.JSON: lambda x: Union[dict, list],
            postgresql.JSONB: lambda x: Union[dict, list],
            postgresql.MACADDR: lambda x: constr(regex=r"^([A-F0-9]{2}:){5}[A-F0-9]{2}$"),
            postgresql.MONEY: lambda x: Decimal,
            postgresql.NUMRANGE: lambda x: Tuple[Union[int, float], Union[int, float]],
            postgresql.TIME: lambda x: time,
            postgresql.TIMESTAMP: lambda x: datetime,
            postgresql.TSRANGE: lambda x: Tuple[datetime, datetime],
            postgresql.TSTZRANGE: lambda x: Tuple[datetime, datetime],
            postgresql.UUID: lambda x: UUID,
            # sqlite
            sqlite.DATE: lambda x: date,
            sqlite.DATETIME: lambda x: datetime,
            sqlite.JSON: lambda x: Union[dict, list],
            sqlite.TIME: lambda x: time,
        }

    def get_pydantic_type(self, column_type: "Any") -> "Any":
        """Given a 'Column.type' value, return a type supported by pydantic.

        Args:
            column_type: The type of the SQLColumn.

        Returns:
             A pydantic supported type.
        """

        column_type_class = column_type if isclass(column_type) else column_type.__class__
        if issubclass(column_type_class, TypeEngine):
            try:
                provider = self.providers_map[column_type_class]
                return provider(column_type)
            except KeyError as exc:
                raise ImproperlyConfiguredException(
                    "Unsupported Column type, please extend the provider table."
                ) from exc
        return type(column_type)

    @staticmethod
    def parse_model(model_class: "type[DeclarativeMeta]") -> Mapper:
        """Validate that the passed in model_class is an SQLAlchemy declarative model, and return a ``Mapper`` of it.

        Args:
            model_class: An SQLAlchemy declarative class.

        Returns:
            A SQLAlchemy ``Mapper``.
        """
        try:
            inspected = inspect(model_class)
        except NoInspectionAvailable:
            pass
        else:
            if isinstance(inspected, Mapper):
                return inspected
        raise ImproperlyConfiguredException(
            "Unsupported 'model_class' kwarg: only subclasses of the SQLAlchemy ``DeclarativeMeta`` are supported"
        )

    def to_data_container_class(
        self,
        model_class: "type[DeclarativeMeta]",
        exclude: "set[str] | None" = None,
        field_mappings: "Mapping[str, str | tuple[str, Any]] | None" = None,
        fields: "dict[str, tuple[Any, Any]] | None" = None,
        localns: "dict[str, Any] | None" = None,
        **kwargs: "Any",
    ) -> "type[BaseModel]":
        """Create a data container class corresponding to the given model class.

        :param model_class: The model class that serves as a basis.
        :param exclude: do not include fields of these names in the model.
        :param field_mappings: to rename, and re-type fields.
        :param fields: additional fields to add to the container model.
        :param localns: used for forward-ref resolution.
        :param kwargs: Any kwargs.
        :return: The generated data container class.
        """
        mapper = self.parse_model(model_class=model_class)
        model_name: str = mapper.class_.__qualname__
        exclude = exclude or set()
        field_mappings = field_mappings or {}
        fields = fields or {}
        if model_name not in self._model_namespace_map:
            for field_name, column in mapper.columns.items():
                if field_name in exclude:
                    continue
                if column.default and type(column.default.arg) in ModelFactory.get_provider_map():
                    field_type = (self.get_pydantic_type(column.type), column.default.arg)
                elif not column.nullable:
                    field_type = (self.get_pydantic_type(column.type), ...)
                else:
                    field_type = (self.get_pydantic_type(column.type), None)
                if field_name in field_mappings:
                    field_name, field_type = remap_field(field_mappings, field_name, field_type)
                fields[field_name] = field_type

            class Config(BaseConfig):
                orm_mode = True

            self._model_namespace_map[model_name] = create_model(
                model_name,
                __config__=Config,
                __base__=None,
                __module__=model_class.__module__,
                __validators__={},
                __cls_kwargs__={},
                **fields,
            )
        model = self._model_namespace_map[model_name]
        model.update_forward_refs(**{**(localns or {}), **self._model_namespace_map})
        return model

    def from_data_container_instance(
        self, model_class: "type[DeclarativeMeta]", data_container_instance: BaseModel
    ) -> "Any":
        """Create an instance of a given model_class using the values stored in the given data_container_instance.

        Args:
            model_class: A declarative table class.
            data_container_instance: A pydantic model instance.

        Returns:
            A declarative meta table instance.
        """
        return model_class(**data_container_instance.dict())

    def to_dict(self, model_instance: "DeclarativeMeta") -> "dict[str, Any]":
        """Given a model instance, convert it to a dict of values that can be serialized.

        Args:
            model_instance: An SQLAlchemy declarative table instance.

        Returns:
            A string keyed dict of values.
        """
        model_class = type(model_instance)
        pydantic_model = self._model_namespace_map.get(model_class.__qualname__) or self.to_data_container_class(
            model_class=model_class
        )
        return pydantic_model.from_orm(model_instance).dict()  # type:ignore[pydantic-unexpected]

    def from_dict(self, model_class: "type[DeclarativeMeta]", **kwargs: "Any") -> DeclarativeMeta:
        """Given a dictionary of kwargs, return an instance of the given model_class.

        Args:
            model_class: A declarative table class.
            **kwargs: Kwargs to instantiate the table with.

        Returns:
            An instantiated table instance.
        """
        return model_class(**kwargs)

    def to_openapi_schema(self, model_class: "type[DeclarativeMeta]") -> "Schema":
        """Given a model class, transform it into an OpenAPI schema class.

        :param model_class: A table class.
        :return: An :class:`OpenAPI <pydantic_openapi_schema.v3_1_0.schema.Schema>` instance.
        """
        return OpenAPI310PydanticSchema(schema_class=self.to_data_container_class(model_class=model_class))
