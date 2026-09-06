# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from asyncio import create_task as a_create_task
from asyncio import get_running_loop as a_get_running_loop
from asyncio import sleep as a_sleep
from contextlib import asynccontextmanager
from enum import Enum
from os import getpid as os_getpid
from os import kill as os_kill
from pathlib import Path
from signal import SIGINT as signal_SIGINT
from typing import Annotated
from webbrowser import open as web_open

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from fastapi import Depends, FastAPI, Query, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import (
    FileResponse,
    PlainTextResponse,
    RedirectResponse,
    JSONResponse,
    Response,
)
from pydantic import ValidationError
from uvicorn import run as uvicorn_run

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.logs import SmartLogger, get_smart_logger
from src.words.config import Config, LetterFilterModel, ServerConfig
from src.words.word_search import WordSearch

cfg = Config()
lfm = LetterFilterModel()
log: SmartLogger = get_smart_logger()
log.setLevel(cfg.log_level)


async def open_browser() -> None:
    sc = ServerConfig()
    await a_sleep(1.5)
    loop = a_get_running_loop()
    loop.run_in_executor(None, web_open, f"http://{sc.host}:{sc.port}")


@asynccontextmanager
async def lifespan(web: FastAPI) -> None:
    is_open_webbrowser = cfg.is_open_webbrowser
    is_docker = cfg.is_docker

    log.info(msg = "🚀 Сервер запускается...", pretty = True)
    if is_open_webbrowser and not is_docker:
        a_create_task(open_browser())
    yield

    log.info(msg = "🛑 Сервер останавливается...", pretty = True)
    await a_sleep(1.5)


web = FastAPI(
    title="📜 Words search API", 
    swagger_ui_parameters = {
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
        "filter": True,
        "displayRequestDuration": True
    },
    lifespan = lifespan
)


class IsYesOrNo(str, Enum):
    YES = "✔️ Да"
    NO = "❌ Нет"


class SearchQuery(LetterFilterModel):
    """
    Модель параметров поиска для веб-формы.
    """
    is_save_file: bool = False
    is_web_save_file: IsYesOrNo = IsYesOrNo.NO

    @staticmethod
    def _validate_single_char_pos(
        check_list: list[str], 
        max_length:int,
        alias: str = ""
    ) -> RequestValidationError | None:
        """
        Проверяет, что все элементы списка состоят не более чем из заданного количества символов.
        Формирует и выбрасывает исключение валидации, если хотя бы один элемент превышает ограничение.
        """
        if err_indexes := ", ".join(
            [
                str(index)
                for index, item in enumerate(check_list)
                if len(item) > 1
            ]
        ):
            err_details = [
            {
                "type": "list[str]",
                "loc": (
                    "body", 
                    alias, 
                    err_indexes
                ),
                "msg": f"String should have at most {max_length} character",
                "input": check_list,
                "ctx": {"max_length": max_length}
            }
            ]
            raise RequestValidationError(errors=err_details)
        return
    
    @staticmethod
    def _clear_spaces(check_clear: list[str] | str) -> list[str] | str:
        """
        Убирает пробелы из строк списка.
        """
        if isinstance(check_clear, str):
            return "".join(check_clear.split())
        return [item.replace(" ", "") for item in check_clear]

    @classmethod
    async def _search_query_form(cls, is_web_save_file: Annotated[
            IsYesOrNo,
            Query(
                alias="saving file",
                description = "💾 Сохранить файл.", 
                examples = [IsYesOrNo.NO]
            )
        ], word_length: Annotated[
            int,
            Query(
                alias="word length",
                description = "📙 Количество символов слова.", 
                examples = [SearchQuery().word_length]
            )
        ] = 0, letters_included: Annotated[
            str, 
            Query(
                alias = "included",
                description = "✔️ Символы, которые гарантированно есть в слове.", 
                examples = [SearchQuery().letters_included]
            )
        ] = "", letters_excluded: Annotated[
            str, 
            Query(
                alias = "excluded",
                description = "❌ Символы, которых гарантированно нет в слове.", 
                examples = [SearchQuery().letters_excluded]
            )
        ] = "", letters_fixed_pos: Annotated[
            str, 
            Query(
                alias = "fixed position",
                description = "📗 Символы искомого слова, которые присутствуют в данных позициях.  \n📗 Если символ позиции неизвестен, укажите \"+\".",
                examples = [SearchQuery().letters_fixed_pos]
            )
        ] = "", letters_excluded_pos: Annotated[
            list[str], 
            Query(
                alias = "excluded position",
                description = "📕 Символы искомого слова, которые отсутствуют в данных позициях.  \n📕 Если символ позиции неизвестен, укажите пробел.", 
                examples = [[SearchQuery().letters_excluded_pos[0]]]
            )
        ] = None):
        """
        Собирает и обрабатывает параметры поиска из веб-формы.
        Преобразует данные формы в экземпляр модели `SearchQuery`.
        """
        letters_excluded = cls._clear_spaces(check_clear = letters_excluded)
        letters_included = cls._clear_spaces(check_clear = letters_included)
        letters_excluded_pos = cls._clear_spaces(check_clear = letters_excluded_pos or [""])
        letters_fixed_pos = cls._clear_spaces(check_clear = letters_fixed_pos)

        """
        cls._validate_single_char_pos(
            check_list = letters_fixed_pos, 
            max_length = 1, 
            alias = "📗 Символы искомого слова, которые присутствуют в данных позициях"
        )
        """

        return cls(
            word_length = word_length, 
            letters_excluded = letters_excluded, 
            letters_included = letters_included, 
            letters_excluded_pos = letters_excluded_pos,
            letters_fixed_pos = letters_fixed_pos,
            is_web_save_file = is_web_save_file
        )


@web.get("/", include_in_schema = False)
async def root():
    """
    Перенаправляет корневой маршрут на интерактивную документацию `/docs`.
    """
    return RedirectResponse(
        url = "/docs",
        status_code = status.HTTP_307_TEMPORARY_REDIRECT
    )


@web.get(
    '/shutdown',
    description = "Посылает запрос на остановку веб-сервера.",
    tags = ["⚙️ Конфигурация"],
    summary = "Остановить веб-сервер"
)
async def shutdown():
    os_kill(os_getpid(), signal_SIGINT)
    log.info(msg = "Запрос на остановку сервера отправлен...", pretty = True)
    return PlainTextResponse(
            content = "Запрос на остановку сервера отправлен.",
            status_code = status.HTTP_202_ACCEPTED
        )


@web.post(
    '/clear-report-folder',
    description = "Очищает папку для отчетов от файлов.",
    tags = ["⚙️ Конфигурация"],
    summary = "Очистить от файлов директорию для формирования отчётов"
)
async def clear_report_folder() -> dict:
    """
    Очищает папку от файлов.
    Возвращает сводку по успешным удалениям и ошибкам.
    """
    report = await WordSearch.clear_report_files()
    return JSONResponse(content = report, status_code = status.HTTP_200_OK)


@web.get(
    "/search-word", 
    description = "Получение списка русских существительных, соответствующих заданным параметрам.", 
    tags = ["📑 Поиск и фильтрация слов"], 
    summary = "Фильтрация слов по критериям"
)
async def word_search(
    search_query: Annotated[
        SearchQuery, 
        Depends(SearchQuery._search_query_form)
    ]
) -> Response:
    """
    Обработчик запроса фильтрации слов по заданным в формах критериям.
    """
    try:
        if search_query.is_web_save_file == IsYesOrNo.YES:
            search_query.is_save_file = True

        if search_query.word_length <= 1:
            content = f"Совпадений не обнаружено.\nКоличество найденных слов: 0"
            return PlainTextResponse(
                content = content, 
                status_code = status.HTTP_404_NOT_FOUND
            )

        found_words, quantity_words, report_path = WordSearch.run_search(lfm = search_query)

        if not found_words:
            content = f"Совпадений не обнаружено.\nКоличество найденных слов: {quantity_words}"
            return PlainTextResponse(
                content = content,
                status_code = status.HTTP_404_NOT_FOUND
            )

        if search_query.is_save_file:
            return FileResponse(
                path = report_path,
                filename = report_path.name,
                media_type = "text/plain",
                headers = {
                    "Quantity-Found-Words": str(quantity_words)
                },
                status_code = status.HTTP_200_OK
            )

        content = f"Количество найденных слов: {quantity_words}\n\n{found_words}"
        return PlainTextResponse(
            content = content, 
            status_code = status.HTTP_200_OK
        )
    except ValueError as err:
        log.error(msg=f"ValueError: {err}")
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = str(err)
        ) from err

def web_start() -> None:
    """
    Запускает веб-приложение FastAPI с использованием сервера Uvicorn.
    Читает параметры хоста и порта из конфигурации приложения.
    """
    sc = ServerConfig()
    uvicorn_run(
        f"{__name__}:web", 
        host = sc.host, 
        port = sc.port, 
        reload = sc.is_reload
    )


if __name__ == "__main__":
    web_start()