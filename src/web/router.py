# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from enum import Enum
from pathlib import Path
from pydantic import Field
from typing import Annotated

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.utilities import Utilities as uts
from src.words.config import Config, LetterFilterModel
from src.words.word_search import WordSearch

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from fastapi import FastAPI, Form, Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response, PlainTextResponse, FileResponse, RedirectResponse
from uvicorn import run as uvicorn_run


web = FastAPI(
    title="📜 Words search API", 
    swagger_ui_parameters = {
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
        "filter": True,
        "displayRequestDuration": True
    }
)


cfg = Config()


class IsYesOrNo(str, Enum):
    YES = "✔️ Да"
    NO = "❌ Нет"


class SearchQuery(LetterFilterModel):
    """
    Модель параметров поиска для веб-формы.
    """
    word_length: Annotated[int, Field(ge=2)] = 3
    letters_excluded: str = ""
    letters_included: str = ""
    letters_excluded_pos: list[str] = Field(default_factory = list)
    letters_fixed_pos: list[
        Annotated[str, Field()]
        ] = Field(default_factory = list)
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
    async def _search_query_form(
        cls, 
        is_web_save_file: Annotated[
            IsYesOrNo,
            Query(
                alias="saving file",
                description = "💾 Сохранить файл.", 
                examples = [IsYesOrNo.NO]
            )
        ],
        word_length: Annotated[
            int,
            Query(
                alias="word length",
                description = "📙 Количество символов слова.", 
                examples = [cfg.lfm.word_length]
            )
        ] = cfg.lfm.word_length,
        letters_included: Annotated[
            str, 
            Query(
                alias = "included",
                description = "✔️ Символы, которые гарантированно есть в слове.", 
                examples = [cfg.lfm.letters_included]
            )
        ] = cfg.lfm.letters_included,
        letters_excluded: Annotated[
            str, 
            Query(
                alias = "excluded",
                description = "❌ Символы, которых гарантированно нет в слове.", 
                examples = [cfg.lfm.letters_excluded]
            )
        ] = cfg.lfm.letters_excluded,
        letters_fixed_pos: Annotated[
            list[str], 
            Query(
                alias = "fixed position",
                description = "📗 Символы искомого слова, которые присутствуют в данных позициях.  \n📗 Если символ позиции неизвестен, укажите пробел.",
                examples = [[cfg.lfm.letters_fixed_pos[0]]]
            )
        ] = [cfg.lfm.letters_fixed_pos[0]],
        letters_excluded_pos: Annotated[
            list[str], 
            Query(
                alias = "excluded position",
                description = "📕 Символы искомого слова, которые отсутствуют в данных позициях.  \n📕 Если символ позиции неизвестен, укажите пробел.", 
                examples = [[cfg.lfm.letters_excluded_pos[0]]]
            )
        ] = [cfg.lfm.letters_excluded_pos[0]]
    ):
        """
        Собирает и обрабатывает параметры поиска из веб-формы.
        Преобразует данные формы в экземпляр модели `SearchQuery`.
        """
        
        letters_excluded = cls._clear_spaces(check_clear=letters_excluded)
        letters_included = cls._clear_spaces(check_clear=letters_included)
        letters_excluded_pos = cls._clear_spaces(check_clear=letters_excluded_pos)
        letters_fixed_pos = cls._clear_spaces(check_clear=letters_fixed_pos)
        
        cls._validate_single_char_pos(
            check_list = letters_fixed_pos, 
            max_length = 1, 
            alias = "📗 Символы искомого слова, которые присутствуют в данных позициях"
        )
        
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
        status_code = 307
    )


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
    found_words: str
    report_path: Path
    if search_query.is_web_save_file == IsYesOrNo.YES:
        search_query.is_save_file = True
    
    found_words, quantity_words, report_path = WordSearch.run_search(lfm = search_query)
    
    if not found_words:
        content = f"Количество слов: {quantity_words}"
        found_words = "Совпадений не обнаружено."
        return PlainTextResponse(content = content)

    if search_query.is_save_file:
        return FileResponse(
            path = report_path,
            filename = report_path.name,
            media_type = "text/plain",
            headers={
                "Quantity-Found-Words": str(quantity_words)
            }
        )

    content = f"Количество слов: {quantity_words}\n\n{found_words}"
    return PlainTextResponse(content = content)


@web.post(
    '/clear-report-folder',
    description = "Безопасно очищает папку для отчетов от файлов.",
    tags = ["⚙️ Конфигурация"],
    summary = "Очистить от файлов директорию для формирования отчётов"
)
async def clear_report_folder() -> dict:
    """
    Безопасно очищает папку от файлов.
    Возвращает сводку по успешным удалениям и ошибкам.
    """
    return await WordSearch.clear_report_files()


def web_start() -> None:
    """
    Запускает веб-приложение FastAPI с использованием сервера Uvicorn.
    Читает параметры хоста и порта из конфигурации приложения.
    """
    uvicorn_run(
        f"{__name__}:web", host = cfg.host, port = cfg.port, reload = cfg.is_unicorn_reload
    )


if __name__ == "__main__":
    web_start()