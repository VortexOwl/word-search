# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from abc import ABC, abstractmethod
from pathlib import Path
from re import escape as re_escape
from re import sub as re_sub

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.config import Config, LetterFilterModel
from src.logs import SmartLogger, get_smart_logger
from src.utilities import Utilities as uts

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class FilterBuilder(ABC):
    """Абстрактный интерфейс строителей параметров фильтрации."""

    @abstractmethod
    def build(self) -> LetterFilterModel:
        """
        Создаёт модель фильтра из доступного источника данных.

        Returns:
            Заполненная модель параметров фильтрации.
        """
        raise NotImplementedError


class InputFilterBuilder(FilterBuilder):
    """
    Собирает параметры фильтра из интерактивного пользовательского ввода.

    Внутренние методы класса последовательно получают отдельные параметры
    фильтра. Полностью собранная модель возвращается методом ``build()``.
    """

    def __init__(self, cfg: Config, lfm: LetterFilterModel, log: SmartLogger):
        """Инициализирует строитель фильтра пользовательского ввода.

        Args:
            cfg: Конфигурация приложения.
            lfm: Начальные параметры фильтра. Модель копируется перед
                использованием и не изменяется напрямую вызывающим кодом.
            log: Логгер для сообщений пользователю.
        """

        self._cfg = cfg.copy()
        self._lfm = lfm.copy()
        self._log = log
        self._lfm.letters_fixed_pos: list[str] = (
            [""]
            if isinstance(self._lfm.letters_fixed_pos, str)
            else self._lfm.letters_fixed_pos
        )

    @staticmethod
    def _normalize_unique_chars(letters: str) -> str:
        """
        Возвращает строку уникальных символов в нижнем регистре.
        Порядок первого появления символов сохраняется.

        Args:
            letters: Исходная строка символов.

        Returns:
            Строка уникальных символов в нижнем регистре.
        """
        return "".join(dict.fromkeys(letters.lower()))

    def _input_len_word(self, provided_input: str | None = None) -> None:
        """
        Получает и сохраняет длину искомого слова.

        При интерактивном вводе повторяет запрос, пока не будет
        введено целое число не менее двух. При переданном
        ``provided_input`` некорректное значение приводит к ``ValueError``.

        Args:
            provided_input: Значение для автоматизированного сценария
                или теста. Если не передано, значение читается из консоли.

        Raises:
            ValueError: Если переданное значение некорректно или меньше двух.
        """
        while True:
            self._log.info(
                msg="Введите количество символов искомого слова (не менее 2).",
                pretty=True,
            )
            raw: str = provided_input if provided_input is not None else input()
            cleaned = re_sub(pattern=r"\D", repl="", string=raw)

            if not cleaned:
                if provided_input is not None:
                    self._log.error(
                        msg="В `provided_input` указано некорректное значение числа."
                    )
                    raise ValueError(
                        "В `provided_input` указано некорректное значение числа."
                    )
                self._log.warning(
                    msg="Не удалось распознать число. Повторите ввод.",
                    pretty=True,
                )
                continue

            quantity = int(cleaned)
            if quantity < 2:
                if provided_input is not None:
                    self._log.error(
                        msg="В `provided_input` указано слишком малое значение числа."
                    )
                    raise ValueError(
                        "В `provided_input` указано слишком малое значение числа."
                    )
                self._log.warning(
                    msg="Слишком короткое слово. Введите число не менее 2.",
                    pretty=True,
                )
                continue

            self._log.info(msg=f"Введено число: '{quantity}'.", pretty=True)
            self._lfm.word_length = quantity
            return

    def _input_letters_excluded(self, provided_input: str | None = None) -> None:
        """
        Получает символы, которых гарантированно нет в искомом слове.

        Введённые символы приводятся к нижнему регистру, очищаются
        в соответствии с шаблоном конфигурации и сохраняются в поле
        ``letters_excluded`` текущей модели фильтра.

        Args:
            provided_input: Значение для автоматизированного сценария
                или теста. Если не передано, значение читается из консоли.
        """
        self._log.info(msg="Введите символы, которых нет в искомом слове.", pretty=True)
        raw: str = provided_input if provided_input is not None else input()
        letters_excluded = re_sub(
            pattern=self._cfg.pattern_ru_letters,
            repl="",
            string=self._normalize_unique_chars(letters=raw),
        )
        self._log.info(
            msg=f"Были обнаружены символы: {list(letters_excluded)}.",
            pretty=True,
        )
        self._lfm.letters_excluded = letters_excluded

    def _input_letters_included(self, provided_input: str | None = None) -> None:
        """
        Получает символы, которые гарантированно присутствуют в слове.

        Символы, уже указанные в ``letters_excluded``, удаляются.
        Оставшиеся символы нормализуются и сохраняются в поле
        ``letters_included`` текущей модели фильтра.

        Args:
            provided_input: Значение для автоматизированного сценария
                или теста. Если не передано, значение читается из консоли.
        """

        self._log.info(
            msg="Введите символы, которые присутствуют в искомом слове.",
            pretty=True,
        )
        raw: str = provided_input if provided_input is not None else input()
        if self._lfm.letters_excluded:
            pattern = rf"[{re_escape(self._lfm.letters_excluded)}]|{self._cfg.pattern_ru_letters}"
        else:
            pattern = self._cfg.pattern_ru_letters
        letters_included = re_sub(
            pattern=pattern, repl="", string=self._normalize_unique_chars(letters=raw)
        )
        self._log.info(
            msg=f"Были обнаружены символы: {list(letters_included)}.",
            pretty=True,
        )
        self._lfm.letters_included = letters_included

    def _validate_bounds(self, provided_input: list[str] | None = None) -> None:
        """
        Проверяет количество позиционных ограничений.

        Args:
            provided_input: Ограничения для отдельных позиций. Если значение
                не передано, проверка количества не выполняется.

        Raises:
            ValueError: Если количество переданных ограничений не совпадает
                с длиной слова.
        """

        if provided_input is not None and len(provided_input) != self._lfm.word_length:
            raise ValueError(
                "Количество ограничений позиций должно совпадать с длиной слова."
            )

    def _input_letters_excluded_pos(
        self,
        provided_input: list[str] | None = None,
    ) -> None:
        """
        Получает запрещённые символы для каждой позиции слова.

        Для каждой позиции вводится набор символов из ``letters_included``,
        которые не могут находиться на этой позиции. Повторы удаляются,
        а символы, отсутствующие в ``letters_included``, отбрасываются.

        Результат сохраняется в поле ``letters_excluded_pos`` текущей
        модели фильтра.

        Args:
            provided_input: Список предварительно заданных значений,
                обычно используемый в тестах. Количество элементов должно
                совпадать с длиной слова.

        Raises:
            ValueError: Если количество переданных значений не совпадает
                с длиной слова.
        """

        self._validate_bounds(provided_input=provided_input)
        letters_excluded_pos: list[str] = []

        self._log.info(
            msg="Введите символы искомого слова, которых нет в данных позициях.",
            pretty=True,
        )
        for index in range(self._lfm.word_length):
            self._log.info(
                msg=f"Позиция {index + 1} ({index * '+'}*{(self._lfm.word_length - index - 1) * '+'}):",
                pretty=True,
            )
            raw: str = provided_input[index] if provided_input is not None else input()
            letters_excluded_pos_item = re_sub(
                pattern=rf"[^{re_escape(self._lfm.letters_included)}]",
                repl="",
                string=self._normalize_unique_chars(letters=raw),
            )
            self._log.info(
                msg=f"Были обнаружены символы: {list(letters_excluded_pos_item)}.",
                pretty=True,
            )
            letters_excluded_pos.append(letters_excluded_pos_item)

        self._lfm.letters_excluded_pos = letters_excluded_pos

    def _input_letters_fixed_pos(
        self,
        provided_input: list[str] | None = None,
    ) -> None:
        """
        Получает фиксированный символ для каждой позиции слова.

        Для каждой позиции обрабатывается строка из ``letters_included``.
        Повторы удаляются, недопустимые символы отбрасываются, после чего
        сохраняется только первый подходящий символ.

        Если подходящий символ отсутствует, для позиции сохраняется пустая
        строка, обозначающая отсутствие фиксированного ограничения.

        Результат сохраняется в поле ``letters_fixed_pos`` текущей модели
        в формате ``list[str]``.

        Args:
            provided_input: Список предварительно заданных значений,
                обычно используемый в тестах. Количество элементов должно
                совпадать с длиной слова.

        Raises:
            ValueError: Если количество переданных значений не совпадает
                с длиной слова.
        """
        self._validate_bounds(provided_input=provided_input)
        letters_fixed_pos: list[str] = []

        self._log.info(
            msg=(
                "Введите символы искомого слова, которые находятся в данных позициях. "
                "Будет считан первый подходящий символ для каждой позиции."
            ),
            pretty=True,
        )
        for index in range(self._lfm.word_length):
            self._log.info(
                msg=f"Позиция {index + 1} ({index * '+'}*{(self._lfm.word_length - index - 1) * '+'}):",
                pretty=True,
            )
            raw: str = provided_input[index] if provided_input is not None else input()
            letters_fixed_pos_item = (
                re_sub(
                    pattern=rf"[^{re_escape(self._lfm.letters_included)}]",
                    repl="",
                    string=self._normalize_unique_chars(letters=raw),
                )
            )[:1]
            self._log.info(
                msg=f"Были обнаружены символы: {list(letters_fixed_pos_item)}.",
                pretty=True,
            )
            letters_fixed_pos.append(letters_fixed_pos_item)
        self._lfm.letters_fixed_pos = letters_fixed_pos

    def build(self) -> LetterFilterModel:
        """
        Собирает модель фильтра из интерактивного ввода.

        Метод последовательно получает общие и позиционные ограничения,
        а также параметры сохранения и вывода результата. Состояние модели,
        переданной конструктору, не изменяется.

        Returns:
            Заполненная модель фильтра.

        Raises:
            ValueError: Если переданное тестовое значение имеет некорректный
                формат.
        """

        self._input_len_word()
        self._input_letters_excluded()
        self._input_letters_included()

        if self._lfm.letters_included:
            self._input_letters_excluded_pos()
            self._input_letters_fixed_pos()
        else:
            self._lfm.letters_excluded_pos = [""] * self._lfm.word_length
            self._lfm.letters_fixed_pos = [""] * self._lfm.word_length

        return LetterFilterModel(
            word_length=self._lfm.word_length,
            letters_excluded=self._lfm.letters_excluded,
            letters_included=self._lfm.letters_included,
            letters_excluded_pos=self._lfm.letters_excluded_pos,
            letters_fixed_pos=self._lfm.letters_fixed_pos,
            is_save_file=self._lfm.is_save_file,
        )


class ReceivedFilterBuilder(FilterBuilder):
    """
    Нормализует модель фильтра, полученную из внешнего источника.

    Внешняя модель может содержать позиционные ограничения в формате
    ``list[str]`` или ``str``. Builder приводит их к длине искомого слова
    и удаляет недопустимые символы.
    """

    def __init__(self, lfm: LetterFilterModel, log: SmartLogger):
        """Инициализирует строитель фильтра из внешней модели.

        Args:
            lfm: Модель фильтра, полученная от внешнего источника.
                Исходная модель копируется и не изменяется.
            log: Логгер приложения.
        """
        self._lfm = lfm.copy()
        self._log = log

    @staticmethod
    def _normalize_position_constraints(
        constraints: list[str] | str, allowed_letters: str
    ) -> list[str] | str:
        """
        Нормализует позиционные ограничения.

        Для строкового формата недопустимые символы заменяются на ``+``.
        Символ ``+`` обозначает свободную позицию. Для списочного формата
        недопустимые символы удаляются из каждого элемента.

        Args:
            constraints: Ограничения в формате строки или списка строк.
            allowed_letters: Буквы, разрешённые в позиционных ограничениях.

        Returns:
            Нормализованные ограничения в том же формате, что и
            ``constraints``.
        """
        if isinstance(constraints, str):
            correct = set(f"{allowed_letters}+")
            return "".join(char if char in correct else "+" for char in constraints)
        else:
            invalid_symbols = "".join(set("".join(constraints)) - set(allowed_letters))
            table_excluded = str.maketrans("", "", invalid_symbols)
            return [elem.translate(table_excluded) for elem in constraints]

    def build(self) -> LetterFilterModel:
        """
        Нормализует внешнюю модель фильтра.

        Позиционные ограничения, которые короче длины слова, дополняются.
        Для строкового ``letters_fixed_pos`` свободные позиции обозначаются
        символом ``+``.

        Returns:
            Нормализованная модель фильтра.

        Raises:
            ValueError: Если позиционное ограничение длиннее слова.
        """
        len_letters_excluded_pos: int = len(self._lfm.letters_excluded_pos)
        len_letters_fixed_pos: int = len(self._lfm.letters_fixed_pos)

        if (
            self._lfm.word_length < len_letters_excluded_pos
            or self._lfm.word_length < len_letters_fixed_pos
        ):
            raise ValueError(
                "letters_fixed_pos и letters_excluded_pos должны соответствовать длине слова."
            )

        if self._lfm.word_length > len_letters_excluded_pos:
            for _ in range(self._lfm.word_length - len_letters_excluded_pos):
                self._lfm.letters_excluded_pos.append("")

        if self._lfm.word_length > len_letters_fixed_pos:
            self._lfm.letters_fixed_pos = f"{self._lfm.letters_fixed_pos}{(self._lfm.word_length - len_letters_fixed_pos) * '+'}"

        table_excluded = str.maketrans("", "", self._lfm.letters_excluded)
        self._lfm.letters_included = self._lfm.letters_included.translate(
            table_excluded
        )

        self._lfm.letters_excluded_pos = self._normalize_position_constraints(
            constraints=self._lfm.letters_excluded_pos,
            allowed_letters=self._lfm.letters_included,
        )

        self._lfm.letters_fixed_pos = self._normalize_position_constraints(
            constraints=self._lfm.letters_fixed_pos,
            allowed_letters=self._lfm.letters_included,
        )

        return self._lfm


class WordSearchService:
    """Ищет слова в словаре по параметрам фильтрации."""

    def __init__(self, cfg: Config, lfm: LetterFilterModel, log: SmartLogger):
        """
        Инициализирует сервис поиска слов.

        Args:
            cfg: Конфигурация приложения, включая путь к словарю.
            lfm: Модель параметров фильтрации.
            log: Логгер приложения.
        """
        self._cfg = cfg
        self._lfm = lfm
        self._log = log

    @staticmethod
    def _matches_position_constraints(
        word: str, letters_fixed_pos: list[str] | str, letters_excluded_pos: list[str]
    ) -> bool:
        """
        Проверяет соответствие слова позиционным ограничениям.

        Для каждой позиции проверяется, что:

        - фиксированный символ совпадает с символом слова;
        - символ слова отсутствует среди запрещённых для этой позиции.

        В строковом формате ``letters_fixed_pos`` символ ``+`` означает,
        что позиция не имеет фиксированного ограничения.

        Args:
            word: Проверяемое слово.
            letters_fixed_pos: Фиксированные символы в формате строки
                или списка строк.
            letters_excluded_pos: Запрещённые символы для каждой позиции.

        Returns:
            ``True``, если слово соответствует всем ограничениям,
            иначе ``False``.
        """
        if not letters_fixed_pos and not letters_excluded_pos:
            return True

        for index, letter in enumerate(word):
            required = letters_fixed_pos[index]
            forbidden = letters_excluded_pos[index]

            if required and required != "+" and letter != required:
                return False

            if letter in forbidden:
                return False

        return True

    def search_words(self) -> list[str]:
        """
        Находит слова в словаре по заданной модели фильтра.

        Каждая строка словаря приводится к нижнему регистру и проверяется
        по длине, обязательным и запрещённым символам, а также по
        позиционным ограничениям.

        Returns:
            Отсортированный список уникальных найденных слов.
        """
        path_file_ru_words: Path = self._cfg.path_file_ru_words
        encoding_ru_words: str = self._cfg.encoding_ru_words

        set_included: set[str] = set(self._lfm.letters_included)
        set_excluded: set[str] = set(self._lfm.letters_excluded)
        words: set[str] = set()

        for line in uts.read_file_line_by_line(
            file_path=path_file_ru_words, encoding=encoding_ru_words
        ):
            if (word := line.lower()) and (
                len(word) == self._lfm.word_length
                and set_included.issubset(word)
                and set_excluded.isdisjoint(word)
                and self._matches_position_constraints(
                    word=word,
                    letters_fixed_pos=self._lfm.letters_fixed_pos,
                    letters_excluded_pos=self._lfm.letters_excluded_pos,
                )
            ):
                words.add(word)

        return sorted(words)


class FilterBuilderFactory:
    """
    Фабрика строителей фильтра.

    В зависимости от режима работы фабрика возвращает строитель
    для интерактивного ввода или для внешней модели фильтра.
    """

    def __init__(self, cfg: Config, lfm: LetterFilterModel, log: SmartLogger):
        """
        Инициализирует фабрику строителей фильтра.

        Args:
            cfg: Конфигурация приложения.
            lfm: Модель фильтра для внешнего источника данных.
            log: Логгер приложения.
        """
        self._cfg = cfg
        self._lfm = lfm
        self._log = log

    def create_builder(
        self,
        is_interactive: bool,
    ) -> FilterBuilder:
        """
        Создаёт строитель фильтра для выбранного режима.

        Args:
            is_interactive: Если ``True``, используется интерактивный ввод.
                Если ``False``, используется внешняя модель фильтра.

        Returns:
            Строитель, соответствующий выбранному режиму.
        """
        if is_interactive:
            return InputFilterBuilder(cfg=self._cfg, lfm=self._lfm, log=self._log)

        return ReceivedFilterBuilder(lfm=self._lfm, log=self._log)

    def build_filter(self, is_interactive: bool) -> LetterFilterModel:
        """
        Создаёт модель фильтра из выбранного источника данных.

        Args:
            is_interactive: Если ``True``, параметры получают из консоли.
                Если ``False``, используется внешняя модель фильтра.

        Returns:
            Заполненная модель для интерактивного режима или нормализованная
            модель для внешнего режима.
        """

        data_object = self.create_builder(is_interactive=is_interactive)

        return data_object.build()


class ApplicationService:
    """Группирует прикладные сервисы работы с результатами поиска."""

    class ClearReportService:
        """Очищает директорию для хранения отчетов от файлов."""

        def __init__(self, cfg: Config | None = None):
            """
            Инициализирует сервис удаления отчётов.

            Args:
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация по умолчанию.
            """
            self._cfg = cfg if cfg is not None else Config()

        async def clear_report_files(self) -> dict[str, int | tuple[str]]:
            """
            Удаляет файлы из каталога отчётов.

            Returns:
                Словарь со статистикой удаления: количеством успешно
                удалённых файлов и количеством ошибок.
            """
            return await uts.clearing_folder(clear_folder=self._cfg.report_folder)

    class ReportService:
        """Формирует отчёты по результатам поиска слов."""

        def __init__(
            self,
            cfg: Config | None = None,
            lfm: LetterFilterModel | None = None,
            log: SmartLogger | None = None,
        ) -> None:
            """
            Инициализирует сервис формирования отчётов.

            Args:
                cfg: Конфигурация приложения.
                lfm: Модель фильтра по умолчанию.
                log: Логгер приложения.
            """

            self._cfg = cfg if cfg is not None else Config()
            self._lfm = lfm if lfm is not None else LetterFilterModel()
            self._log = log if log is not None else get_smart_logger()

        @staticmethod
        def _format_word_lines(cfg: Config, words: list[str]) -> str:
            """
            Форматирует список слов в строки ограниченной длины.

            Слова разделяются пробелами. При превышении лимита
            ``cfg.report_line_limit`` начинается новая строка.

            Args:
                cfg: Конфигурация с ограничением длины строки.
                words: Список слов для форматирования.

            Returns:
                Многострочная строка с найденными словами. Для пустого списка
                возвращается пустая строка.
            """

            current_line: str = ""
            lines: list[str] = []
            extra_len: int

            for word in words:
                extra_len = len(word) + (1 if current_line else 0)
                if len(current_line) + extra_len > cfg.report_line_limit:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = f"{current_line} {word}" if current_line else word

            if current_line:
                lines.append(current_line)

            return "\n".join(lines)

        def _save_report_file(
            self, cfg: Config, log: SmartLogger, report_text: str
        ) -> Path:
            """
            Сохраняет текст отчёта в файл.

            Каталог отчётов создаётся автоматически, если он отсутствует.
            После успешной записи в лог отправляется информационное сообщение.

            Args:
                cfg: Конфигурация с путями к каталогу и файлу отчёта.
                log: Логгер приложения.
                report_text: Подготовленный текст отчёта.

            Returns:
                Путь к созданному файлу отчёта.
            """
            path_report_folder: Path = cfg.path_report_folder
            path_report_file: Path = cfg.path_report_file

            path_report_folder.mkdir(parents=True, exist_ok=True)

            with path_report_file.open("w", encoding="utf-8") as words_file:
                words_file.write(report_text)

            log.info(
                msg=(
                    f"Файл с отобранными словами создан по пути: "
                    f'"{path_report_file.relative_to(Path.cwd())}".'
                ),
                pretty=True,
            )
            return path_report_file

        def create_report(
            self,
            is_interactive: bool = False,
            cfg: Config | None = None,
            lfm: LetterFilterModel | None = None,
            log: SmartLogger | None = None,
        ) -> tuple[str, int, Path | None]:
            """
            Формирует отчёт по результатам поиска слов.

            Args:
                is_interactive: Если ``True``, параметры фильтра получают
                    из интерактивного ввода.
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация экземпляра.
                lfm: Модель фильтра для внешнего режима. Если не передана,
                    используется модель экземпляра.
                log: Логгер приложения. Если не передан,
                    используется логгер экземпляра.

            Returns:
                Кортеж из трёх значений:

                - текста отчёта;
                - количества найденных слов;
                - пути к сохранённому файлу или ``None``.

                Если слова не найдены, файл не создаётся.
            """
            if cfg is None:
                cfg = self._cfg.copy()
            if lfm is None:
                lfm = self._lfm.copy()
            if log is None:
                log = self._log

            log.info(msg="Начат перебор слов.", pretty=True)
            filter_builder_factory = FilterBuilderFactory(cfg=cfg, lfm=lfm, log=log)
            lfm = filter_builder_factory.build_filter(is_interactive=is_interactive)
            ws = WordSearchService(cfg=cfg, lfm=lfm, log=log)
            words = ws.search_words()
            log.info(msg="Перебор слов завершен.", pretty=True)

            quantity_words = len(words)
            log.info(msg=f"Найдено слов: {quantity_words}.", pretty=True)

            word_lines: str = self._format_word_lines(cfg=cfg, words=words)

            if quantity_words != 0 and lfm.is_save_file:
                path_report_file: Path = self._save_report_file(
                    cfg=cfg, log=log, report_text=word_lines
                )
                return word_lines, quantity_words, path_report_file

            return word_lines, quantity_words, None
