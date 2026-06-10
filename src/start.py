# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from asyncio import run as async_run

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from utilities.basic_utilities_project import add_workdir_in_PATH
add_workdir_in_PATH()
from src.words.word_search import WordSearch


def start() -> None:
    """
    Точка входа: 
    Выполняет поиск слов по заданным пользователем ограничениям.
    """
    WordSearch.run_search(is_input = True)
    

def start_basic() -> None:
    """
    Точка входа: 
    Запускает поиск слов по ограничениям из конфигурации без интерактивного ввода.

    Результат сохраняется в файл отчёта.
    """
    WordSearch.run_search()


def start_clear() -> None:
    """
    Точка входа: 
    Запускает асинхронное очищение от файлов директории для формирования отчётов.
    """
    async_run(WordSearch.clear_report_files())


if __name__ == "__main__":
    start()
