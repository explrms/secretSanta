import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Callable, Any, Union

from aiogram.types import BotCommand
from fastapi import FastAPI
from fastapi import Request
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from config import FAST_API_VERSION, WEBHOOK_URL
from tg.loader import bot
from db.db_config import engine, sessionmanager, config
from tg.index import bot_router

logging.basicConfig(level=logging.INFO)

sessionmanager.init(config.DB_CONFIG)


def strip_strings(data: Union[dict, list, str]) -> Union[dict, list, str]:
    """
    Функция удаляет из строковых параметров тела запроса пробелы и переносы строк.
    :param data: тело запроса
    :return: модифицироварнное тело запроса
    """
    if isinstance(data, dict):
        return {k: strip_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [strip_strings(item) for item in data]
    elif isinstance(data, str):
        return data.strip(" \t\n\r")
    return data


class StripMiddleware(BaseHTTPMiddleware):
    """
    Middleware, который обрабатывает JSON поля входящих POST, PUT, PATCH запросов, с целью
    исключить пробельные символы по бокам строковых параметров.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]):
        async def parse_json(body: bytes) -> dict:
            json_body = json.loads(body)
            return strip_strings(json_body)

        try:
            if (
                    request.method in ["POST", "PUT", "PATCH"]
                    and not "/admin" in request.url.path
            ):
                body = await request.body()
                if body:
                    modified_body = await parse_json(body)
                    request._body = json.dumps(modified_body).encode("utf-8")
        except:
            pass
        response = await call_next(request)
        return response


def init_app(init_db=True):
    lifespan = None

    if init_db:
        sessionmanager.init(config.DB_CONFIG)

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            if WEBHOOK_URL:
                try:
                    #await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
                    await bot.set_my_commands(
                        commands=[
                            BotCommand(command="/start", description="Главное меню"),
                        ]
                    )
                except:
                    pass
                #print("webhook is set!")
            yield
            if sessionmanager._engine is not None:
                await sessionmanager.close()

    # Создать папку static, files, если они не существуют
    folders_to_create = ["static", "files"]
    for folder in folders_to_create:
        if not os.path.exists(folder):
            os.makedirs(folder)

    app = FastAPI(
        title="SecretSanta Backend",
        lifespan=lifespan,
        version=FAST_API_VERSION,
        docs_url=None,
        redoc_url=None,
        description="Тут пока нет описания, но оно когда-нибудь будет",
        summary="И это тоже будет скоро",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
    app.add_middleware(StripMiddleware)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    app.include_router(bot_router)

    return app


app = init_app(init_db=True)


class StatusResponse(BaseModel):
    status: str = Field(..., description="Статус сервера")


@app.get(
    "/",
    description="Проверяет что сервер онлайн и может возвращать ответы.",
    summary=" - Проверка доступности сервиса",
    responses={200: {"model": StatusResponse, "description": "Статус сервера"}},
    response_description="Статус сервера",
    tags=["Статистика"],
)
async def health_check():
    return {"status": "ok"}


# @app.get("/docs", include_in_schema=False)
# async def custom_swagger_ui_html():
#     return get_swagger_ui_html(
#         openapi_url=app.openapi_url,
#         title=app.title + " - Swagger UI",
#         oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
#         swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
#         swagger_css_url="/static/material-swagger.css",
#     )
#
#
# @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
# async def swagger_ui_redirect():
#     return get_swagger_ui_oauth2_redirect_html()
#
#
# @app.get("/redoc", include_in_schema=False)
# async def redoc_html():
#     return get_redoc_html(
#         openapi_url=app.openapi_url,
#         title=app.title + " - ReDoc",
#         redoc_js_url="https://unpkg.com/redoc@next/bundles/redoc.standalone.js",
#     )
