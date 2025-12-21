from typing import Any
from sqlalchemy import create_engine, inspect
from loguru import logger
import json


class JsonExtractor:
    """Extract json from the database"""

    def __init__(self, source_type: str, source: str, schema: str = "public"):
        self.source_type = source_type
        self.source = source
        self.schema = schema
        self.engine = None
        self.inspector = None

    @classmethod
    def from_connection_string(cls, connection_string: str, schema: str = "public"):
        """Create an instance from a connection string."""
        if connection_string.startswith("postgresql://"):
            source_type = "postgres"
        elif connection_string.startswith("sqlite:///"):
            source_type = "sqlite"
        elif connection_string.startswith("mysql://"):
            source_type = "mysql"
        else:
            raise ValueError("Unsupported connection string format.")
        return cls(source_type=source_type, source=connection_string, schema=schema)

    async def extract_json(self) -> dict[str, Any]:  # add project_id:str
        """Extract json from postgres database"""
        if self.source_type == "postgres":
            self.engine = create_engine(self.source, pool_size=5)
            data_source = "postgresql"
            use_schema = self.schema
        elif self.source_type == "sqlite":
            sqlite_url = f"sqlite:///{self.source}"
            self.engine = create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
            data_source = "sqlite"
            use_schema = None
        elif self.source_type == "mysql":
            self.engine = create_engine(self.source, pool_size=5)
            data_source = "mysql"
            use_schema = self.schema
        else:
            raise ValueError(f"Unsupported source type: {self.source_type}")

        self.inspector = inspect(self.engine)
        models = self._extract_models(schema=use_schema)
        relationships = self._extract_relationships(schema=use_schema)
        views = self._extract_views(schema=use_schema)
        return {
            "models": models,
            "relationships": relationships,
            "views": views,
            "metrics": [],
            "dataSource": data_source,
        }

    def _extract_models(self, schema: str | None = None) -> list:
        """Extract table as models"""
        models = []
        table_names = self.inspector.get_table_names(schema=schema)
        for table_name in table_names:
            try:
                columns_info = self.inspector.get_columns(table_name, schema=schema)
                pk_constraint = self.inspector.get_pk_constraint(
                    table_name, schema=schema
                )

                primary_keys = pk_constraint.get("constrained_columns", [])
                primary_key = primary_keys[0] if primary_keys else ""

                columns = []
                for col in columns_info:
                    columns.append(
                        {
                            "name": col["name"],
                            "type": self._normalize_type(str(col["type"])),
                            "isNullable": col.get("nullable", True),
                            "isHidden": False,
                        }
                    )

                models.append(
                    {
                        "name": table_name,
                        "refSql": "",
                        "cached": False,
                        "refreshTime": "",
                        "columns": columns,
                        "primaryKey": primary_key,
                        "properties": {},
                    }
                )

                logger.debug(f" Extracted table: {table_name}")

            except Exception as e:
                logger.error(f" Failed to extract table {table_name}: {e}")

        return models

    def _extract_relationships(self, schema: str | None = None) -> list:
        """Extract relationships between tables"""
        relationships = []
        table_names = self.inspector.get_table_names(schema=schema)
        for table_name in table_names:
            try:
                fk_constraints = self.inspector.get_foreign_keys(
                    table_name, schema=schema
                )

                for fk in fk_constraints:
                    if not fk.get("referred_table"):
                        continue

                    relationships.append(
                        {
                            "name": fk.get(
                                "name", f"{table_name}_{fk['referred_table']}_fk"
                            ),
                            "models": [table_name, fk["referred_table"]],
                            "joinType": "many_to_one",
                            "condition": (
                                f"{table_name}.{fk['constrained_columns'][0]} = "
                                f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                            ),
                            "properties": {},
                        }
                    )

            except Exception as e:
                logger.error(f" Failed to extract relationships for {table_name}: {e}")

        return relationships

    def _extract_views(self, schema: str | None = None) -> list:
        """Extract database views"""
        views = []
        try:
            view_names = self.inspector.get_view_names(schema=schema)
            for view_name in view_names:
                views.append({"name": view_name, "statement": "", "properties": {}})
                logger.debug(f" Extracted view: {view_name}")
        except Exception as e:
            logger.error(f" Failed to extract views: {e}")

        return views

    def _normalize_type(self, sql_type: str) -> str:
        """Normalize SQL types to standard format."""
        sql_type = sql_type.upper()

        type_mapping = {
            "INTEGER": "integer",
            "INT": "integer",
            "SMALLINT": "integer",
            "BIGINT": "bigint",
            "SERIAL": "integer",
            "BIGSERIAL": "bigint",
            "VARCHAR": "varchar",
            "CHAR": "varchar",
            "CHARACTER": "varchar",
            "TEXT": "text",
            "STRING": "varchar",
            "BOOLEAN": "boolean",
            "BOOL": "boolean",
            "REAL": "double",
            "DOUBLE": "double",
            "DOUBLE PRECISION": "double",
            "FLOAT": "float",
            "NUMERIC": "numeric",
            "DECIMAL": "decimal",
            "DATE": "date",
            "DATETIME": "timestamp",
            "TIMESTAMP": "timestamp",
            "TIME": "time",
            "BLOB": "bytea",
            "BYTEA": "bytea",
        }

        for db_type, standard_type in type_mapping.items():
            if sql_type.startswith(db_type):
                return standard_type

        return "varchar"

    def close(self):
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed.")


async def extract_json(source, schema: str = "public") -> dict[str, Any]:
    """Extract  json from the database"""
    extractor = JsonExtractor.from_connection_string(source, schema)
    datas = await extractor.extract_json()
    extractor.close()
    return json.dumps(datas, indent=2)
