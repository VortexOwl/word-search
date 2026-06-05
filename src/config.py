# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    data_folder: str = 'data'
    file_ru_words: str = 'russian_nouns.txt'
    encoding_ru_words = 'utf-8'
    report_folder: str = 'docs'
    report_file: str = 'words'
    path_data_folder: Path = Path.cwd() / data_folder
    path_file_ru_words: Path = path_data_folder / file_ru_words
    path_report_folder: Path = Path.cwd() / report_folder
    path_report_file: Path = path_report_folder / report_file