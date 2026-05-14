from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


SUPPORTED_OPERATORS = {"=", "!=", ">", ">=", "<", "<=", "LIKE", "IN"}
SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}


@dataclass(frozen=True)
class FilterClause:
    column: str
    operator: str
    value: Any


class SQLiteAdapter:
    """SQLite adapter with strict validation before SQL execution."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self) -> list[str]:
        sql = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
        with self.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        table_name = self._validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(
                f'PRAGMA table_info({self._quote_identifier(table_name)})'
            ).fetchall()

        if not rows:
            raise ValidationError(f"Table '{table_name}' has no schema information.")

        return [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": bool(row["pk"]),
            }
            for row in rows
        ]

    def get_database_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {table: self.get_table_schema(table) for table in self.list_tables()}

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[dict[str, Any]]:
        table_name = self._validate_table(table)
        table_columns = self._get_table_columns(table_name)

        if limit <= 0 or limit > 500:
            raise ValidationError("`limit` must be between 1 and 500.")
        if offset < 0:
            raise ValidationError("`offset` must be >= 0.")

        selected_columns = columns or table_columns
        self._validate_columns(table_name, selected_columns)
        select_sql = ", ".join(self._quote_identifier(col) for col in selected_columns)

        where_sql, where_params = self._build_where_clause(table_name, filters or [])

        order_sql = ""
        if order_by is not None:
            self._validate_columns(table_name, [order_by])
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {self._quote_identifier(order_by)} {direction}"

        sql = (
            f"SELECT {select_sql} FROM {self._quote_identifier(table_name)}"
            f"{where_sql}{order_sql} LIMIT ? OFFSET ?"
        )
        params = [*where_params, limit, offset]

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        table_name = self._validate_table(table)
        if not values:
            raise ValidationError("Insert payload must not be empty.")

        columns = list(values.keys())
        self._validate_columns(table_name, columns)

        col_sql = ", ".join(self._quote_identifier(col) for col in columns)
        placeholder_sql = ", ".join("?" for _ in columns)
        sql = (
            f"INSERT INTO {self._quote_identifier(table_name)} ({col_sql}) "
            f"VALUES ({placeholder_sql})"
        )
        params = [values[col] for col in columns]

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            last_id = cursor.lastrowid

        result = dict(values)
        pk_column = self._single_primary_key(table_name)
        if pk_column and pk_column not in result and last_id is not None:
            result[pk_column] = last_id

        return result

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        table_name = self._validate_table(table)
        metric_name = metric.lower().strip()
        if metric_name not in SUPPORTED_METRICS:
            raise ValidationError(
                f"Unsupported metric '{metric}'. Allowed: {sorted(SUPPORTED_METRICS)}."
            )

        group_cols = group_by or []
        self._validate_columns(table_name, group_cols)

        if metric_name == "count":
            metric_expr = (
                f"COUNT({self._quote_identifier(column)})"
                if column
                else "COUNT(*)"
            )
            if column:
                self._validate_columns(table_name, [column])
        else:
            if not column:
                raise ValidationError(
                    f"Metric '{metric_name}' requires a `column` argument."
                )
            self._validate_columns(table_name, [column])
            metric_expr = f"{metric_name.upper()}({self._quote_identifier(column)})"

        select_parts = [self._quote_identifier(c) for c in group_cols]
        select_parts.append(f"{metric_expr} AS value")
        select_sql = ", ".join(select_parts)

        where_sql, where_params = self._build_where_clause(table_name, filters or [])
        group_sql = ""
        if group_cols:
            group_sql = " GROUP BY " + ", ".join(
                self._quote_identifier(c) for c in group_cols
            )

        sql = (
            f"SELECT {select_sql} FROM {self._quote_identifier(table_name)}"
            f"{where_sql}{group_sql}"
        )
        with self.connect() as conn:
            rows = conn.execute(sql, where_params).fetchall()
        return [dict(row) for row in rows]

    def _build_where_clause(
        self, table: str, filters: list[dict[str, Any]]
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []

        validated_filters = [self._validate_filter(table, raw_filter) for raw_filter in filters]
        parts: list[str] = []
        params: list[Any] = []

        for f in validated_filters:
            col_sql = self._quote_identifier(f.column)
            if f.operator == "IN":
                value_list = list(f.value)
                if len(value_list) == 0:
                    raise ValidationError("Operator 'IN' requires at least one value.")
                placeholders = ", ".join("?" for _ in value_list)
                parts.append(f"{col_sql} IN ({placeholders})")
                params.extend(value_list)
            else:
                parts.append(f"{col_sql} {f.operator} ?")
                params.append(f.value)

        return " WHERE " + " AND ".join(parts), params

    def _validate_filter(self, table: str, raw_filter: dict[str, Any]) -> FilterClause:
        if not isinstance(raw_filter, dict):
            raise ValidationError("Each filter must be an object.")

        required = {"column", "op", "value"}
        if not required.issubset(raw_filter):
            raise ValidationError(
                "Each filter must include 'column', 'op', and 'value' keys."
            )

        column = str(raw_filter["column"])
        operator = str(raw_filter["op"]).upper().strip()
        value = raw_filter["value"]

        self._validate_columns(table, [column])
        if operator not in SUPPORTED_OPERATORS:
            raise ValidationError(
                f"Unsupported operator '{operator}'. Allowed: {sorted(SUPPORTED_OPERATORS)}."
            )

        if operator == "IN" and not isinstance(value, (list, tuple)):
            raise ValidationError("Operator 'IN' requires an array value.")

        return FilterClause(column=column, operator=operator, value=value)

    def _validate_table(self, table: str) -> str:
        if not isinstance(table, str) or not table.strip():
            raise ValidationError("Table name must be a non-empty string.")
        candidate = table.strip()
        if candidate not in self.list_tables():
            raise ValidationError(f"Unknown table '{candidate}'.")
        return candidate

    def _validate_columns(self, table: str, columns: list[str]) -> None:
        valid = set(self._get_table_columns(table))
        bad = [col for col in columns if col not in valid]
        if bad:
            raise ValidationError(f"Unknown columns for table '{table}': {bad}.")

    def _get_table_columns(self, table: str) -> list[str]:
        return [col["name"] for col in self.get_table_schema(table)]

    def _single_primary_key(self, table: str) -> str | None:
        pk_columns = [col["name"] for col in self.get_table_schema(table) if col["pk"]]
        return pk_columns[0] if len(pk_columns) == 1 else None

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

