# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from pathlib import Path
from typing import Iterator


def read_file_line_by_line(file_path: Path, encoding='utf-8') -> Iterator[str]:
    with file_path.open('r', encoding=encoding) as file:
        for line in file:
            yield line.strip()