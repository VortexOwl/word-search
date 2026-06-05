# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from basic_utilities.base_config_project import add_workdir_in_PATH
add_workdir_in_PATH()
from src.word_search import WordSearch


def start() -> None:
    """
    Точка входа: Выполняет поиск слов по заданным пользователем ограничениям.
    """
    WordSearch().word_search()
    

if __name__ == "__main__":
    start()
