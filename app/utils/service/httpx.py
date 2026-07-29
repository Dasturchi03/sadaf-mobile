import logging
import httpx
from typing import Literal, Optional, Union
from app.utils.di.httpx_ctx import httpx_client, proxy_httpx_client
from app.utils.exc import RequestFailed


logger = logging.getLogger(__name__)

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
PATCH = 'PATCH'
DELETE = 'DELETE'
OPTIONS = 'OPTIONS'


async def make_request(
    method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    base_url: str,
    endpoint: str,
    auth: Optional[httpx.BasicAuth] = None,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    data: Optional[str] = None,
    json: Optional[dict] = None,
    client: httpx.AsyncClient = None,
    proxy: bool = False,
) -> Union[dict, list]:
    """
    Universal API request sender.
    Returns JSON response (dict) or raises RequestFailed.
    """

    url = base_url.rstrip('/') + '/' + endpoint.lstrip('/')
    logger.info(f"Sending {method} request to {url}")

    if not client:
        client = [httpx_client, proxy_httpx_client][proxy]

    try:
        resp = await client.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            data=data,
            json=json,
            auth=auth,
        )
        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            logger.error(f"Invalid JSON response from {url}")
            raise RequestFailed(detail={
                "status_code": resp.status_code,
                "error": "Invalid JSON response",
                "body": resp.text
            })

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise RequestFailed(detail={
            "status_code": e.response.status_code,
            "response_body": e.response.text
        })

    except httpx.TimeoutException:
        logger.error(f"Request to {url} timed out")
        raise RequestFailed(detail=f"Request to {url} timed out")

    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise RequestFailed(detail=f"Failed to connect to {url}")

    except Exception as err:
        logger.exception(f"Unexpected error during request to {url}")
        raise RequestFailed(detail={
            "message": f"Unexpected error during request to {url}",
            "error": str(err)
        })
