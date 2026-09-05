# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from dataclasses import field
from os import getenv
from pathlib import Path

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from pydantic import BaseModel, Field, SettingsConfigDict, model_validator
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """
    Конфигурация uvicorn.
    """
    host: str = "127.0.0.1"
    port: int = 8000
    is_reload: bool = True

    model_config = SettingsConfigDict(env_prefix = "API_")

    @model_validator(mode = "before")
    @classmethod
    def detect_docker_env(cls, data: dict) -> dict:
        if Path("/.dockerenv").exists():
            if "host" not in data:
                data["host"] = "0.0.0.0"
            if "is_reload" not in data:
                data["is_reload"] = False
                
        return data


class LetterFilterModel(BaseModel):
    """
    Модель параметров фильтрации слов.

    Атрибуты:
        word_length: длина искомого слова.
        letters_excluded: символы, которые гарантированно отсутствуют в слове.
        letters_included: символы, которые гарантированно присутствуют в слове.
        letters_excluded_pos: для каждой позиции — символы, которые не могут
            находиться в этой позиции.
        letters_fixed_pos: для каждой позиции — символ, который должен находиться
            в этой позиции, либо пустая строка, если позиция не фиксирована.
        is_save_file: булевское значение True/False, отвечающее на вопрос 
        сохранять ли результат фильтрации в текстовый файл.
    """
    word_length: int = 5
    letters_excluded: str = ""
    letters_included: str = ""
    letters_excluded_pos: list[str] = Field(default_factory = list)
    letters_fixed_pos: list[str] = Field(default_factory = list)
    is_save_file: bool = True


class Config(BaseSettings):
    """
    Конфигурация приложения.

    Содержит настройки веб-сервера, пути к файлам словаря и отчёта,
    параметры кодировки и базовую модель фильтрации LetterFilterModel.
    """
    model_config = SettingsConfigDict(env_prefix="APP_")

    log_level: int = 10
    is_open_webbrowser: bool = True
    data_folder: str = 'data'
    encoding_ru_words:str = 'utf-8'
    file_ru_words: str = 'russian_nouns.txt'
    pattern_ru_letters: str = r'[^а-яё-]'
    report_folder: str = 'docs'
    report_file: str = 'Found words.txt'
    
    lfm: LetterFilterModel = field(default_factory = lambda: LetterFilterModel(
        word_length = 5,
        letters_excluded = "лт",
        letters_included = "аб",
        letters_excluded_pos = ["а", "", "б", "", ""],
        letters_fixed_pos = ["б", "а", "", "", ""],
        is_save_file = True
    ))

    @property
    def path_data_folder(self) -> Path:
        return Path.cwd() / self.data_folder
    
    @property
    def path_file_ru_words(self) -> Path:
        return self.path_data_folder / self.file_ru_words

    @property
    def path_report_folder(self) -> Path:
        return Path.cwd() / self.report_folder

    @property
    def path_report_file(self) -> Path:
        return self.path_report_folder / self.report_file
    
    @property
    def is_docker(self) -> bool:
        return Path('/.dockerenv').exists()
    
    def __post_init__(self):
        """
        Инициализирует производные поля конфигурации после создания экземпляра.

        Приводит списки `letters_excluded_pos` и `letters_fixed_pos`
        к длине `word_length`, обрезая лишние и заполняя недостающие позиции 
        пустыми строками.
        """
        if len(self.lfm.letters_excluded_pos) != self.lfm.word_length:
            self.lfm.letters_excluded_pos = (
                self.lfm.letters_excluded_pos[: self.lfm.word_length]
                + [""] * max(0, self.lfm.word_length - len(self.lfm.letters_excluded_pos))
            )

        if len(self.lfm.letters_fixed_pos) != self.lfm.word_length:
            self.lfm.letters_fixed_pos = (
                self.lfm.letters_fixed_pos[: self.lfm.word_length]
                + [""] * max(0, self.lfm.word_length - len(self.lfm.letters_fixed_pos))
            )