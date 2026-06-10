# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel, Field


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
    letters_excluded_pos: list[str] = Field(default_factory=list)
    letters_fixed_pos: list[str] = Field(default_factory=list)
    is_save_file: bool = True


@dataclass
class Config:
    """
    Конфигурация приложения.

    Содержит настройки веб-сервера, пути к файлам словаря и отчёта,
    параметры кодировки и базовую модель фильтрации LetterFilterModel.
    """
    host: str = "127.0.0.1"
    port: int = 8000
    is_unicorn_reload = True

    data_folder: str = "data"
    file_ru_words: str = "russian_nouns.txt"
    encoding_ru_words = "utf-8"
    report_folder: str = "docs"
    report_file: str = "Found words.txt"
    path_data_folder: Path = Path.cwd() / data_folder
    path_file_ru_words: Path = path_data_folder / file_ru_words
    path_report_folder: Path = Path.cwd() / report_folder
    path_report_file: Path = path_report_folder / report_file
    
    pattern_ru_letters: str = r'[^а-яё-]'
    
    lfm: LetterFilterModel = field(default_factory=lambda: LetterFilterModel(
        word_length = 5,
        letters_excluded = "лт",
        letters_included = "аб",
        letters_excluded_pos = ["а", "", "б", "", ""],
        letters_fixed_pos = ["б", "а", "", "", ""],
        is_save_file = True
    ))
    
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