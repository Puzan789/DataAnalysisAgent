from sqlalchemy import text
from src.database.state import get_global_db_state


async def get_database_overview() -> dict:
    """Get database overview: table count, total rows, database size."""
    db_state = get_global_db_state()
    async with db_state.postgres.get_session() as session:
        tables_q = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        result = await session.execute(tables_q)
        tables = [row[0] for row in result.fetchall()]

        table_stats = []
        total_rows = 0
        for table in tables:
            count_q = text(f'SELECT COUNT(*) FROM "{table}"')
            count = (await session.execute(count_q)).scalar()
            total_rows += count
            table_stats.append({"table_name": table, "row_count": count})

        size_q = text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = (await session.execute(size_q)).scalar()

        return {
            "table_count": len(tables),
            "total_rows": total_rows,
            "database_size": db_size,
            "tables": table_stats,
        }


async def get_all_tables() -> list[dict]:
    """List all tables with row counts."""
    db_state = get_global_db_state()
    async with db_state.postgres.get_session() as session:
        q = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        result = await session.execute(q)
        tables = []
        for row in result.fetchall():
            table_name = row[0]
            count_q = text(f'SELECT COUNT(*) FROM "{table_name}"')
            count = (await session.execute(count_q)).scalar()
            tables.append({"table_name": table_name, "row_count": count})
        return tables


async def get_table_schema(table_name: str) -> dict:
    """Get full schema for a table: columns, types, constraints, foreign keys."""
    db_state = get_global_db_state()
    async with db_state.postgres.get_session() as session:
        cols_q = text("""
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                c.numeric_precision
            FROM information_schema.columns c
            WHERE c.table_schema = 'public' AND c.table_name = :table
            ORDER BY c.ordinal_position
        """)
        result = await session.execute(cols_q, {"table": table_name})
        columns = []
        for row in result.fetchall():
            columns.append({
                "column_name": row[0],
                "data_type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
                "max_length": row[4],
                "numeric_precision": row[5],
            })

        pk_q = text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = 'public'
                AND tc.table_name = :table
                AND tc.constraint_type = 'PRIMARY KEY'
        """)
        pk_result = await session.execute(pk_q, {"table": table_name})
        primary_keys = [row[0] for row in pk_result.fetchall()]

        fk_q = text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_schema = 'public'
                AND tc.table_name = :table
                AND tc.constraint_type = 'FOREIGN KEY'
        """)
        fk_result = await session.execute(fk_q, {"table": table_name})
        foreign_keys = []
        for row in fk_result.fetchall():
            foreign_keys.append({
                "column": row[0],
                "references_table": row[1],
                "references_column": row[2],
            })

        count_q = text(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = (await session.execute(count_q)).scalar()

        for col in columns:
            col["is_primary_key"] = col["column_name"] in primary_keys

        return {
            "table_name": table_name,
            "row_count": row_count,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
        }


async def get_table_data(table_name: str, page: int, page_size: int) -> dict:
    """Get paginated data from a table."""
    db_state = get_global_db_state()
    offset = (page - 1) * page_size

    async with db_state.postgres.get_session() as session:
        count_q = text(f'SELECT COUNT(*) FROM "{table_name}"')
        total = (await session.execute(count_q)).scalar()

        data_q = text(f'SELECT * FROM "{table_name}" LIMIT :limit OFFSET :offset')
        result = await session.execute(data_q, {"limit": page_size, "offset": offset})
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result.fetchall()]

        return {
            "table_name": table_name,
            "columns": columns,
            "rows": rows,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_rows": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }


async def get_all_relationships() -> list[dict]:
    """Get all foreign key relationships in the database."""
    db_state = get_global_db_state()
    async with db_state.postgres.get_session() as session:
        q = text("""
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_schema = 'public'
                AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name
        """)
        result = await session.execute(q)
        relationships = []
        for row in result.fetchall():
            relationships.append({
                "source_table": row[0],
                "source_column": row[1],
                "target_table": row[2],
                "target_column": row[3],
            })
        return relationships
