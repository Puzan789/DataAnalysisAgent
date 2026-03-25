from sqlalchemy import (
    create_engine,
    MetaData,
    text,
    inspect,
)
from sqlalchemy.engine import Inspector
from src.config import settings
from loguru import logger


class SchemaExtractor:
    """Extract schema information from database (sync - used for one-time indexing)."""

    def __init__(self, database_url: str | None = None):
        if database_url:
            self.database_url = database_url
        else:
            self.database_url = (
                f"postgresql://{settings.POSTGRES_USERNAME}:"
                f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
                f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
        self.engine = create_engine(self.database_url)
        self.inspector: Inspector = inspect(self.engine)
        self.metadata = MetaData()

    def extract_all_tables(self, schema: str = "public"):
        """Extract all table names from the database schema"""
        tables = []

        table_names = self.inspector.get_table_names(schema=schema)
        for table_name in table_names:
            try:
                table_info = self.extract_table_info(table_name, schema=schema)
                tables.append(table_info)
            except Exception as e:
                logger.error(f"Error extracting table {table_name}: {e}")
        logger.info(f"Extracted {len(tables)} tables from schema '{schema}'")
        return tables

    def extract_table_info(self, table_name: str, schema: str = "public"):
        """Extract detailed infromation about the specific table"""
        # get columns name
        columns = self.inspector.get_columns(table_name, schema=schema)
        column_name = [column["name"] for column in columns]
        # get primary keys
        pk_constraint = self.inspector.get_pk_constraint(table_name, schema=schema)
        primary_keys = pk_constraint.get("constrained_columns", [])
        # get foreign keys
        foreign_keys = self.inspector.get_foreign_keys(table_name, schema=schema)
        # get indexes
        indexes = self.inspector.get_indexes(table_name, schema=schema)
        # get table comment if available
        try:
            table_comment_dict = self.inspector.get_table_comment(
                table_name, schema=schema
            )
            table_comment = table_comment_dict.get("text", "")
        except NotImplementedError:
            table_comment = ""
        table_info = {
            "schema": schema,  # NOTE:i think we dont want this schema here (kept_here in case we need for filtering)
            "table_name": table_name,
            "columns": column_name,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "table_comment": table_comment,
        }
        return table_info

    def extract_column_details(self, table_name: str, col_name, schema: str = "public"):
        """Extract detailed information about a specific column in a table"""
        columns = self.inspector.get_columns(table_name, schema=schema)
        for col in columns:
            if col["name"] == col_name:
                return {
                    "type": "COLUMN",
                    "table_name": table_name,
                    "column_name": col["name"],
                    "data_type": str(col["type"]),
                    "is_primary_key": col["name"]
                    in self.inspector.get_pk_constraint(table_name, schema=schema).get(
                        "constrained_columns", []
                    ),
                    "comment": col.get("comment", ""),
                }

    def extract_relationship(self, table_name: str, schema: str = "public"):
        """Extract all foreign key  relationship"""
        values = []
        foreign_keys = self.inspector.get_foreign_keys(table_name)
        for fk in foreign_keys:
            constraint = f"FOREIGN KEY ({fk['constrained_columns'][0]}) REFERENCES {fk['referred_table']}({fk['referred_columns'][0]})"
            condition = f"{table_name}.{fk['constrained_columns'][0]} = {fk['referred_table']}.{fk['referred_columns'][0]}"
            fk_data = {
                "type": "FOREIGN_KEY",
                "comment": f'-- {{"condition": "{condition}", "joinType": "MANY_TO_ONE"}}\n  ',
                "constraint": constraint,
                "tables": [table_name, fk["referred_table"]],
            }
            values.append(fk_data)

        return values

    def get_table_row_count(self, table_name: str, schema: str = "public") -> int:
        """Get approximate row count for a table."""
        try:
            query = f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                return result.scalar()
        except Exception as e:
            print("here error occured", e)
            return 0

    def close(self):
        """Close database Connection"""
        self.engine.dispose()
