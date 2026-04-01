# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from os import path, mkdir
from re import sub as re_sub, escape as re_escape

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.logs import get_smart_logger
from src.utilities.utilities import creating_necessary_folders


log = get_smart_logger()


def get_quantity_letters() -> int:
    log.info(message='Введите количество букв искомого слова.')
    quantity_letters = re_sub(pattern=r'\D', repl='', string=input())
    if quantity_letters != '' and int(quantity_letters) < 3:
        quantity_letters = ''
    while quantity_letters == '':
        log.info(message='Введено некорректное количество букв слова. Повторите ввод количества букв слова.')
        quantity_letters = re_sub(pattern=r'\D', repl='', string=input())
    log.info(message=f"Введено число: '{quantity_letters}'.")
    return int(quantity_letters)


def get_letters_not_in_word() -> str:
    log.info(message='Введите буквы, которые отсутствуют в искомом слове.')
    letters_not_in_word = re_sub(pattern=r'[^а-яё-]' , repl='', string=''.join(dict.fromkeys(input().lower())))
    log.info(message=f'Введены буквы: {list(letters_not_in_word)}.')
    return letters_not_in_word


def get_letters_in_word(letters_not_in_word: str) -> str:
    log.info(message='Введите буквы, которые присутствуют в искомом слове.')
    letters_in_word = re_sub(pattern=rf'[{re_escape(letters_not_in_word)}]|[^а-яё-]', repl='', string=''.join(dict.fromkeys(input().lower())))
    log.info(message=f'Введены буквы: {list(letters_in_word)}.')
    return letters_in_word


def get_letters_in_word_and_not_in_positions(letters_in_word: str, quantity_letters: int) -> list[str]:
    log.info(message='Введите буквы искомого слова, которые отсутствуют в определенных его позициях.')
    letters_not_in_positions = []
    for index in range(quantity_letters):
        log.info(message=f"Позиция {index+1} ({index*'+'}*{(quantity_letters-index-1)*'+'}):")
        letters_not_in_positions_item = re_sub(pattern=rf'[^{re_escape(letters_in_word)}]' , repl='', string=''.join(dict.fromkeys(input().lower())))
        log.info(message=f'Введены буквы: {list(letters_not_in_positions_item)}.')
        letters_not_in_positions.append(letters_not_in_positions_item)
    return letters_not_in_positions


def get_letters_in_positions_in_word(letters_in_word: str, quantity_letters: int) -> list[str]:
    log.info(message='Введите буквы искомого слова, которые присутствуют в определенных его позициях.')
    letters_in_positions = []
    for index in range(quantity_letters):
        log.info(message=f"Позиция {index+1} ({index*'+'}*{(quantity_letters-index-1)*'+'}):")
        letters_in_positions_item = (re_sub(pattern=rf'[^{re_escape(letters_in_word)}]', repl='', string=''.join(dict.fromkeys(input().lower()))))[:1]
        log.info(message=f'Введены буквы: {list(letters_in_positions_item)}.')
        letters_in_positions.append(letters_in_positions_item)
    return letters_in_positions


def letter_filter() -> tuple[int, str, str, list[str], list[str]]:
    letters_not_in_positions: list[str] = []
    letters_in_positions: list[str] = []
    quantity_letters = get_quantity_letters()
    letters_not_in_word = get_letters_not_in_word()
    letters_in_word = get_letters_in_word(letters_not_in_word=letters_not_in_word)
    if letters_in_word:
        letters_not_in_positions = get_letters_in_word_and_not_in_positions(letters_in_word=letters_in_word, quantity_letters=quantity_letters)
        letters_in_positions = get_letters_in_positions_in_word(letters_in_word=letters_in_word, quantity_letters=quantity_letters)
    return quantity_letters, letters_not_in_word, letters_in_word, letters_not_in_positions, letters_in_positions
    

def word_search():
    quantity_letters, letters_not_in_word, letters_in_word, letters_not_in_positions, letters_in_positions = letter_filter()
    with open('resources/russian.txt', 'r', encoding='cp1251') as ru_words_file:
        russian_words = ru_words_file.read().lower()
    words = set(russian_words.splitlines())

    words = [word for word in words if len(word) == quantity_letters and set(letters_in_word).issubset(word) and set(letters_not_in_word).isdisjoint(word)]
    words = [word for word in words if not any((letter != letters_in_positions[index] or letter in letters_not_in_positions[index]) and letters_in_positions[index] != '' for index, letter in enumerate(word))]
    quantity_words = len(words)

    log.info(message='Начат перебор слов.')
    if quantity_words != 0:
        creating_necessary_folders(path='docs')
        with open('docs/words.txt', 'w') as words_file:
            words_file.write(
                words[0]
                + ''.join(
                    '\n' + word if number % 20 == 0 else f' {word}'
                    for number, word in enumerate(words[1:], start=1)
                )
            )

    log.info(message='Перебор слов завершен.')
    log.info(message='Файл с отобранными словами создан по пути: "docs/words.txt".')
    log.info(message=f'Найдено слов: {quantity_words}.')
