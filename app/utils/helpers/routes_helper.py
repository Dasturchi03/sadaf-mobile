"""Decorators for service functions to wrap them with mobile DB connection handling."""

import types
import inspect
import logging
from functools import wraps

import asyncpg

from app.core.db import get_mobile_pool


logger = logging.getLogger(__name__)


def service(func):
    """Synchronous DB services are not supported with asyncpg."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        raise RuntimeError("Use async_service for DB-backed services")
    return wrapper


def async_service(func):
    """Decorator for asynchronous service handlers to provide an asyncpg connection."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        pool = get_mobile_pool()
        async with pool.acquire() as db:
            async with db.transaction():
                kwargs.setdefault('db', db)
                return await func(*args, **kwargs)
    return wrapper


def wrap_func(func):
    "Wrapper function for wrapping service functions on initializate"
    if inspect.iscoroutinefunction(func):
        async def async_wrapped(*args, **kwargs):
            if 'db' in inspect.signature(func).parameters:
                db = kwargs.get('db', None)
                if isinstance(db, asyncpg.Connection):
                    return await func(*args, **kwargs)
                else:
                    pool = get_mobile_pool()
                    async with pool.acquire() as db:
                        async with db.transaction():
                            kwargs.setdefault('db', db)
                            return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return async_wrapped
    else:
        def sync_wrapped(*args, **kwargs):
            if 'db' in inspect.signature(func).parameters:
                raise RuntimeError("Use async functions for DB-backed services")
            else:
                return func(*args, **kwargs)
        return sync_wrapped


def wrap_modules(MODULES: list):
    for mod in MODULES:
        for attr_name in dir(mod):
            if not attr_name.startswith('_'):
                attr = getattr(mod, attr_name)

                if (
                    isinstance(attr, types.FunctionType)
                    and attr.__module__ == mod.__name__
                ):
                    setattr(mod, attr_name, wrap_func(attr))
