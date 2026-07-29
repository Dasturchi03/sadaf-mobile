from typing import Optional
from fastapi_pagination.config import Config
from fastapi_pagination.bases import AbstractParams
from fastapi_pagination.types import AdditionalData, AsyncItemsTransformer
from fastapi_pagination.ext.sqlalchemy import Selectable, UnwrapMode


class Opts(dict):
    def __init__(self, *args,
                 unique: bool = True,
                 params: Optional[AbstractParams],
                 count_query: Optional[Selectable] = None,
                 subquery_count: bool = True,
                 unwrap_mode: Optional[UnwrapMode] = None,
                 transformer: Optional[AsyncItemsTransformer] = None,
                 additional_data: Optional[AdditionalData] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        kwargs.update(
            {
                'unique': unique,
                'params': params,
                'count_query': count_query,
                'subquery_count': subquery_count,
                'unwrap_mode': unwrap_mode,
                'transformer': transformer,
                'additional_data': additional_data,
                'config': config
            }
        )
        self.unique = unique
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"Opts({dict(self)})"


def add_opts(stmt: Selectable,
             params: Optional[AbstractParams],
             *,
             unique: bool = True,
             count_query: Optional[Selectable] = None,
             subquery_count: bool = True,
             unwrap_mode: Optional[UnwrapMode] = None,
             transformer: Optional[AsyncItemsTransformer] = None,
             additional_data: Optional[AdditionalData] = None,
             config: Optional[Config] = None):
    opts = Opts(
        unique=unique,
        params=params,
        count_query=count_query,
        subquery_count=subquery_count,
        unwrap_mode=unwrap_mode,
        transformer=transformer,
        additional_data=additional_data,
        config=config
    )
    setattr(stmt, '__pagination_opts__', opts)
