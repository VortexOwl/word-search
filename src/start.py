# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from asyncio import run as async_run

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from utilities.basic_utilities_project import add_workdir_in_PATH

add_workdir_in_PATH()
from src.app.word_search_v3 import ApplicationService as app

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#

app_report = app.ReportService()
app_clear = app.ClearReportService()


def start() -> None:
    """
    Точка входа:
    Выполняет поиск слов по заданным пользователем ограничениям.
    """
    app_report.create_report(is_interactive=True)


def start_basic() -> None:
    """
    Точка входа:
    Запускает поиск слов по ограничениям из конфигурации без интерактивного ввода.

    Результат сохраняется в файл отчёта.
    """
    app_report.create_report()


def start_clear() -> None:
    """
    Точка входа:
    Запускает асинхронное очищение от файлов директории для формирования отчётов.
    """
    async_run(app_clear.clear_report_files())


if __name__ == "__main__":
    start()
