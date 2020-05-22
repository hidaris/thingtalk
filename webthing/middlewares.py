import jwt
import asyncio
import functools
import inspect
import typing

from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import RedirectResponse, Response
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, BaseUser, AuthCredentials,
    UnauthenticatedUser)
from starlette.websockets import WebSocket, WebSocketDisconnect


def has_required_scope(conn: HTTPConnection, scopes: typing.Sequence[str]) -> bool:
    for scope in scopes:
        if scope not in conn.auth.scopes:
            return False
    return True


def requires(
    scopes: typing.Union[str, typing.Sequence[str]],
    status_code: int = 403,
    redirect: str = None,
) -> typing.Callable:
    scopes_list = [scopes] if isinstance(scopes, str) else list(scopes)

    def decorator(func: typing.Callable) -> typing.Callable:
        type = None
        sig = inspect.signature(func)
        for idx, parameter in enumerate(sig.parameters.values()):
            if parameter.name == "request" or parameter.name == "websocket":
                type = parameter.name
                break
        else:
            raise Exception(
                f'No "request" or "websocket" argument on function "{func}"'
            )

        if type == "websocket":
            # Handle websocket functions. (Always async)
            @functools.wraps(func)
            async def websocket_wrapper(
                *args: typing.Any, **kwargs: typing.Any
            ) -> None:
                websocket = kwargs.get("websocket", args[idx])
                assert isinstance(websocket, WebSocket)

                if websocket.app.state.require_auth and not has_required_scope(websocket, scopes_list):
                    await websocket.close()
                    raise WebSocketDisconnect
                else:
                    await func(*args, **kwargs)

            return websocket_wrapper

        elif asyncio.iscoroutinefunction(func):
            # Handle async request/response functions.
            @functools.wraps(func)
            async def async_wrapper(
                *args: typing.Any, **kwargs: typing.Any
            ) -> Response:
                request = kwargs.get("request", args[idx])
                assert isinstance(request, Request)

                if request.app.state.require_auth and not has_required_scope(request, scopes_list):
                    if redirect is not None:
                        return RedirectResponse(
                            url=request.url_for(redirect), status_code=303
                        )
                    raise HTTPException(status_code=status_code)
                return await func(*args, **kwargs)

            return async_wrapper

        else:
            # Handle sync request/response functions.
            @functools.wraps(func)
            def sync_wrapper(*args: typing.Any, **kwargs: typing.Any) -> Response:
                request = kwargs.get("request", args[idx])
                assert isinstance(request, Request)

                if request.app.state.require_auth and not has_required_scope(request, scopes_list):
                    if redirect is not None:
                        return RedirectResponse(
                            url=request.url_for(redirect), status_code=303
                        )
                    raise HTTPException(status_code=status_code)
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


class JWTUser(BaseUser):
    def __init__(self, username: str, token: str, payload: dict) -> None:
        self.username = username
        self.token = token
        self.payload = payload

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username


class JWTAuthenticationBackend(AuthenticationBackend):

    def __init__(self, secret_key: str, algorithm: str = 'HS256', prefix: str = 'JWT', username_field: str = 'username'):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.prefix = prefix
        self.username_field = username_field

    @classmethod
    def get_token_from_header(cls, authorization: str, prefix: str):
        """
        Parses the Authorization header and returns only the token
        :param authorization:
        :return:
        """
        try:
            scheme, token = authorization.split()
        except ValueError:
            raise AuthenticationError('Could not separate Authorization scheme and token')
        if scheme.lower() != prefix.lower():
            raise AuthenticationError(f'Authorization scheme {scheme} is not supported')
        return token

    async def authenticate(self, request):
        if "Authorization" not in request.headers:
            return None
        auth = request.headers["Authorization"]
        token = self.get_token_from_header(authorization=auth, prefix=self.prefix)
        try:
            payload = jwt.decode(token, key=self.secret_key, algorithms=self.algorithm)
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(str(e))

        return AuthCredentials(["authenticated"]), JWTUser(username=payload[self.username_field], token=token,
                                                           payload=payload)


class JWTWebSocketAuthenticationBackend(AuthenticationBackend):

    def __init__(self, secret_key: str, algorithm: str = 'HS256', query_param_name: str = 'jwt',
                 username_field: str = 'username'):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.query_param_name = query_param_name
        self.username_field = username_field

    async def authenticate(self, request):
        if self.query_param_name not in request.query_params:
            return AuthCredentials(), UnauthenticatedUser()
        token = request.query_params[self.query_param_name]

        try:
            payload = jwt.decode(token, key=self.secret_key, algorithms=self.algorithm)
            print(payload)
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(str(e))

        return AuthCredentials(["authenticated"]), JWTUser(username=payload[self.username_field], token=token,
                                                           payload=payload)
