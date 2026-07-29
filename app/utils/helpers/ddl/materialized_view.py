from sqlalchemy.schema import DDLElement
from sqlalchemy.sql.compiler import DDLCompiler
from sqlalchemy.ext.compiler import compiles


class CreateMaterializedView(DDLElement):
    inherit_cache = False

    def __init__(self, name: str, selectable, schema: str | None = None, with_data: bool = True):
        self.name = name
        self.schema = schema
        self.selectable = selectable
        self.with_data = with_data


class DropMaterializedView(DDLElement):
    inherit_cache = False

    def __init__(self, name: str, schema: str | None = None, if_exists: bool = True):
        self.name = name
        self.schema = schema
        self.if_exists = if_exists


class RefreshMaterializedView(DDLElement):
    inherit_cache = False

    def __init__(self, name: str, schema: str | None = None, concurrently: bool = False, with_data: bool = True):
        self.name = name
        self.schema = schema
        self.concurrently = concurrently
        self.with_data = with_data


def _full_name(name: str, schema: str | None) -> str:
    return f"{schema}.{name}" if schema else name


@compiles(CreateMaterializedView, "postgresql")
def compile_create_materialized_view(element: CreateMaterializedView, compiler: DDLCompiler, **kw):
    sql_compiler = compiler.sql_compiler
    query_sql = sql_compiler.process(element.selectable, literal_binds=True)
    view_name = _full_name(element.name, element.schema)
    suffix = "WITH DATA" if element.with_data else "WITH NO DATA"
    return f"CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name} AS {query_sql} {suffix}"


@compiles(DropMaterializedView, "postgresql")
def compile_drop_materialized_view(element: DropMaterializedView, compiler: DDLCompiler, **kw):
    view_name = _full_name(element.name, element.schema)
    if_exists = "IF EXISTS " if element.if_exists else ""
    return f"DROP MATERIALIZED VIEW {if_exists}{view_name}"


@compiles(RefreshMaterializedView, "postgresql")
def compile_refresh_materialized_view(element: RefreshMaterializedView, compiler: DDLCompiler, **kw):
    view_name = _full_name(element.name, element.schema)
    concurrently = "CONCURRENTLY " if element.concurrently else ""
    with_data = "WITH DATA" if element.with_data else "WITH NO DATA"
    return f"REFRESH MATERIALIZED VIEW {concurrently}{view_name} {with_data}"
