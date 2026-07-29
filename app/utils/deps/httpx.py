from typing import Annotated
from fastapi import Request, Depends
from app.utils.clients.httpx_client import httpx


async def get_httpx_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.httpx_client


async def get_proxy_httpx_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.httpx_proxy_client


Client = Annotated[httpx.AsyncClient, Depends(get_httpx_client)]
ProxyClient = Annotated[httpx.AsyncClient, Depends(get_proxy_httpx_client)]
