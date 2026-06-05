# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from pathlib import Path
from pydantic import BaseModel
from re import sub as re_sub, escape as re_escape

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.config import Config
from src.logs import get_smart_logger
from src.basic_utilities.utilities import read_file_line_by_line


class LetterFilterModel(BaseModel):
    word_length: int
    letters_excluded: str
    letters_included: str
    letters_excluded_pos: list[str]
    letters_fixed_pos: list[str]


class WordSearch:
    log = get_smart_logger()
    cfg = Config()

    @classmethod
    def _uniq_chars(cls, letters: str) -> str:
        """
        Возвращает строку уникальных символов в нижнем регистре в порядке первого появления.
        """
        return ''.join(dict.fromkeys(letters.lower()))


    @classmethod
    def get_len_word(cls, def_input:str | None = None) -> int:
        """
        Запрашивает у пользователя длину искомого слова (не менее 2 символов).
        
        Пользователь вводит строку, из которой извлекаются только цифры; все
        остальные символы игнорируются. Ввод повторяется до тех пор, пока
        не будет получено корректное число длиной не менее 2.
        """
        while True:
            cls.log.info(msg = 'Введите количество символов искомого слова (не менее 2).')
            raw: str = def_input if def_input is not None else input()
            cleaned = re_sub(pattern=r'\D', repl='', string=raw)

            if not cleaned:
                cls.log.info(msg = 'Не удалось распознать число. Повторите ввод.')
                continue

            quantity = int(cleaned)
            if quantity < 2:
                cls.log.info(msg = 'Слишком короткое слово. Введите число не менее 2.')
                continue

            cls.log.info(msg = f"Введено число: '{quantity}'.")
            return quantity

    @classmethod
    def get_letters_excluded(cls, def_input: str | None = None) -> str:
        """
        Запрашивает у пользователя символы, которых гарантированно нет в слове.
        Возвращает уникальные русские буквы и дефис в нижнем регистре.
        """
        cls.log.info(msg = 'Введите символы, которые отсутствуют в искомом слове.')
        raw: str = def_input if def_input is not None else input()
        letters_excluded = re_sub(
            pattern=r'[^а-яё-]', 
            repl='', 
            string= cls._uniq_chars(letters=raw)
        )
        cls.log.info(msg = f'Были обнаружены символы: {list(letters_excluded)}.')
        return letters_excluded

    @classmethod
    def get_letters_included(
        cls, 
        letters_excluded: str, 
        def_input:str | None = None
    ) -> str:
        """
        Запрашивает у пользователя символы, которые гарантированно есть в слове.
        Возвращает уникальные русские буквы и дефис в нижнем регистре.
        """
        cls.log.info(msg = 'Введите символы, которые присутствуют в искомом слове.')
        raw: str = def_input if def_input is not None else input()
        if letters_excluded:
            pattern = rf'[{re_escape(letters_excluded)}]|[^а-яё-]'
        else:
            pattern = r'[^а-яё-]'
        letters_included = re_sub(
            pattern=pattern,
            repl='', 
            string= cls._uniq_chars(letters=raw)
        )
        cls.log.info(msg = f'Были обнаружены символы: {list(letters_included)}.')
        return letters_included

    @classmethod
    def get_letters_excluded_pos(
        cls, 
        letters_included: str, 
        word_length: int, 
        def_input:list[str] | None = None
    ) -> list[str]:
        """
        Запрашивает у пользователя, в каких позициях не могут находиться известные символы.
        
        Для каждой позиции слова пользователю предлагается ввести набор символов 
        из множества `letters_included`, которые не могут стоять в этой позиции. 
        Ввод для каждой позиции очищается от повторов и символы
        вне `letters_included` отбрасываются.
        """
        if def_input is not None and len(def_input) != word_length:
            raise ValueError(
                "Количество элементов 'def_input' должно соответствовать 'word_length'."
            )

        letters_excluded_pos: list[str] = []
        
        cls.log.info(msg = 'Введите символы искомого слова, которые отсутствуют в данных позициях.')
        for index in range(word_length):
            cls.log.info(msg = f"Позиция {index+1} ({index*'+'}*{(word_length-index-1)*'+'}):")
            raw: str = def_input[index] if def_input is not None else input()
            letters_excluded_pos_item = re_sub(
                pattern=rf'[^{re_escape(letters_included)}]' , 
                repl='', 
                string= cls._uniq_chars(letters=raw)
            )
            cls.log.info(msg = f'Были обнаружены символы: {list(letters_excluded_pos_item)}.')
            letters_excluded_pos.append(letters_excluded_pos_item)
        return letters_excluded_pos

    @classmethod
    def get_letters_fixed_pos(
        cls, 
        letters_included: str, 
        word_length: int, 
        def_input:list[str] | None = None
    ) -> list[str]:
        """
        Запрашивает у пользователя символы, которые точно стоят в заданных позициях слова.

        Для каждой позиции слова пользователю предлагается ввести строку, 
        содержащую хотя бы один символ из множества `letters_included`.
        Ввод для каждой позиции очищается от повторов и символы
        вне `letters_included` отбрасываются.
        Из полученной строки берётся только первый подходящий символ.
        """
        if def_input is not None and len(def_input) != word_length:
            raise ValueError(
                "Количество элементов 'def_input' должно соответствовать 'word_length'."
            )
        letters_fixed_pos: list[str] = []
        
        cls.log.info(msg = 'Введите символы искомого слова, которые находятся в данных позициях. Будет считан первый подходящий символ для каждой позиции.')
        for index in range(word_length):
            cls.log.info(msg = f"Позиция {index+1} ({index*'+'}*{(word_length-index-1)*'+'}):")
            raw: str = def_input[index] if def_input is not None else input()
            letters_fixed_pos_item = (re_sub(
                pattern=rf'[^{re_escape(letters_included)}]', 
                repl='', 
                string= cls._uniq_chars(letters=raw)
            ))[:1]
            cls.log.info(msg = f'Были обнаружены символы: {list(letters_fixed_pos_item)}.')
            letters_fixed_pos.append(letters_fixed_pos_item)
        return letters_fixed_pos

    @classmethod
    def _letter_pre_filter(cls) -> LetterFilterModel:
        """
        Последовательно запрашивает у пользователя параметры фильтрации слов.

        Последовательность шагов:
            1. Запрашивает длину искомого слова.
            2. Запрашивает символы, которых нет в слове.
            3. Запрашивает символы, которые есть в слове.
            4. Если есть известные символы:
            - запрашивает, в каких позициях они не могут находиться;
            - запрашивает, какие символы фиксированы в конкретных позициях.

        Возвращает:
            Экземпляр `LetterFilterModel` с полностью заполненными параметрами
            фильтра (длиной слова, известными/исключёнными символами и
            ограничениями по позициям).
        """
        word_length = cls.get_len_word()
        letters_excluded = cls.get_letters_excluded()
        letters_included = cls.get_letters_included(
            letters_excluded = letters_excluded
        )
        letters_excluded_pos: list[str] = []
        letters_fixed_pos: list[str] = []

        if letters_included:
            letters_excluded_pos = cls.get_letters_excluded_pos(
                letters_included = letters_included, 
                word_length = word_length
            )
            letters_fixed_pos = cls.get_letters_fixed_pos(
                letters_included = letters_included, 
                word_length = word_length
            )

        return LetterFilterModel(
            word_length = word_length,
            letters_excluded = letters_excluded,
            letters_included = letters_included,
            letters_excluded_pos = letters_excluded_pos,
            letters_fixed_pos = letters_fixed_pos,
        )
        
    @classmethod
    def _match_positions(
        cls, 
        word: str,
        letters_fixed_pos: list[str],
        letters_excluded_pos: list[str]
    ) -> bool:
        """
        Проверяет, удовлетворяет ли слово ограничениям по позициям символов.

        Для каждой позиции слова:
            - если в `letters_fixed_pos[index]` указан символ, 
            то в `word[index]` должна стоять именно этот символ;
            - в `letters_excluded_pos[index]` перечислены символы, которые
            не могут находиться в позиции `index`.

        Возвращает:
            True, если слово удовлетворяет всем ограничениям по позициям, иначе False.

        Исключения:
            ValueError: Если длина `letters_fixed_pos` или `letters_excluded_pos` 
            не совпадает с длиной `word`.
        """
        if not letters_fixed_pos and not letters_excluded_pos:
            return True
        
        if (
            len(letters_fixed_pos) != len(word)
            or len(letters_excluded_pos) != len(word)
        ):
            raise ValueError(
                "letters_fixed_pos и letters_excluded_pos должны соответствовать длине слова."
            )

        for index, letter in enumerate(word):
            forbidden = letters_excluded_pos[index]

            if must_be := letters_fixed_pos[index]:
                if letter != must_be or letter in forbidden:
                    return False
            elif letter in forbidden:
                return False
        return True

    @classmethod
    def _letter_filter(cls) -> list[str]:
        """
        Возвращает список слов, которые:
        - имеют нужную длину;
        - содержат все символы из `letters_included`;
        - не содержат ни одного символа из `letters_excluded`;
        - удовлетворяют ограничениям по позициям (`_match_positions`).
        """
        path_file_ru_words: Path = cls.cfg.path_file_ru_words
        encoding_ru_words = cls.cfg.encoding_ru_words

        lpf = cls._letter_pre_filter()

        set_included: set[str] = set(lpf.letters_included)
        set_excluded: set[str] = set(lpf.letters_excluded)

        words: set[str] = set()
        for line in read_file_line_by_line(
            file_path = path_file_ru_words, 
            encoding = encoding_ru_words
        ):
            if word := line.lower():
                words.add(word)

        return [
            word
            for word in words
            if len(word) == lpf.word_length
            and set_included.issubset(word)
            and set_excluded.isdisjoint(word)
            and cls._match_positions(
                word=word,
                letters_fixed_pos=lpf.letters_fixed_pos,
                letters_excluded_pos=lpf.letters_excluded_pos,
            )
        ]

    @classmethod
    def word_search(cls) -> None:
        """
        Выполняет поиск слов по заданным пользователем ограничениям.

        Логика работы:
            1. Запрашивает у пользователя фильтр (длину слова, перечень символов и
            ограничения по позициям).
            2. Загружает словарь русских слов из файла `path_file_ru_words`,
            приводит его к нижнему регистру и разбивает на уникальные слова.
            3. Отбирает слова, которые:
            - имеют нужную длину;
            - содержат все символы из `letters_included`;
            - не содержат ни одного символа из `letters_excluded`;
            - удовлетворяют ограничениям по позициям (`_match_positions`).
            4. Если найдено хотя бы одно слово:
            - создаёт директорию отчётов (при необходимости);
            - записывает найденные слова в файл отчёта.
        """
        path_report_folder: Path = cls.cfg.path_report_folder
        path_report_file: Path = cls.cfg.path_report_file

        words = cls._letter_filter()

        quantity_words = len(words)

        cls.log.info(msg = 'Начат перебор слов.')
        if quantity_words != 0:
            path_report_folder.mkdir(parents=True, exist_ok = True)
            current_line: str = ""
            lines: list[str] = []
            extra_len: int

            with path_report_file.open('w', encoding = 'utf-8') as words_file:
                for word in words:
                    extra_len = len(word) + (1 if current_line else 0)
                    if len(current_line) + extra_len > 80:
                        lines.append(current_line)
                        current_line = word
                    else:
                        current_line = f"{current_line} {word}" if current_line else word

                if current_line:
                    lines.append(current_line)

                words_file.write('\n'.join(lines))

        cls.log.info(msg = 'Перебор слов завершен.')
        if quantity_words != 0:
            cls.log.info(msg = f'Файл с отобранными словами создан по пути: "{path_report_file}".')
        cls.log.info(msg = f'Найдено слов: {quantity_words}.')
