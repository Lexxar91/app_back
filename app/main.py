from hawkcatcher import Hawk

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from prometheus_fastapi_instrumentator import Instrumentator

from sqlalchemy.exc import DatabaseError, OperationalError
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.core.config import settings
from app.api.routers import main_router
import logging

# hawk = Hawk({
#     'token': settings.hawk_project_token,
#     'collector_endpoint': f'https://{settings.hawk_id}.k1.hawk.so',
#
# })


app = FastAPI(title=settings.app_title)
Instrumentator().instrument(app).expose(app)

logger = logging.getLogger(__name__)

try:
    hawk = Hawk(os.getenv('HAWK_PROJECT_TOKEN'))
    logger.info("Hawk initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Hawk: {e}", exc_info=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cors_header(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Глобальный обработчик исключений для перехвата всех необработанных ошибок.

    Args:
        request (Request): Объект запроса FastAPI
        exc (Exception): Перехваченное исключение

    Returns:
        JSONResponse: Ответ с информацией об ошибке и статус-кодом 500
    """
    logger.exception(f"Unexpected error: {exc}")
    hawk.send(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content = {
            "detail": f"An unexpected error occurred: {str(exc)}",
            "type": "internal_server_error"
        }
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """
    Обработчик ошибок базы данных SQLAlchemy.

    Args:
        request (Request): Объект запроса FastAPI
        exc (DatabaseError): Исключение, связанное с ошибкой базы данных

    Returns:
        JSONResponse: Ответ с информацией об ошибке БД и статус-кодом 500
    """
    logger.error(f"Database error: {exc}")
    hawk.send(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Database error occurred: {exc.orig.args[0]}",
            "type": "database_error"
        }
    )

@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    """
    Обработчик операционных ошибок базы данных, таких как проблемы с подключением.

    Args:
        request (Request): Объект запроса FastAPI
        exc (OperationalError): Исключение, связанное с операционными проблемами БД

    Returns:
        JSONResponse: Ответ с сообщением о недоступности БД и статус-кодом 500
    """
    logger.error(f"Database connection error: {exc}")
    hawk.send(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database is temporarily unavailable. Please try again later.",
            "type": "operational_error"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Обработчик ошибок валидации входящих запросов.

    Args:
        request (Request): Объект запроса FastAPI
        exc (RequestValidationError): Исключение с деталями ошибок валидации

    Returns:
        JSONResponse: Ответ со списком ошибок валидации и статус-кодом 422
    """
    logger.warning(f"Request validation error: {exc}")
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
            "body": exc.body
        })
    hawk.send(errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
            "type": "validation_error"
        }
    )

app.include_router(main_router)
