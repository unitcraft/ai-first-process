# -*- coding: utf-8 -*-
"""Общее для всех стражей: сбор файлов и форма нарушения.

Отдельным модулем, а не копией в каждом страже, по правилу «один факт — один дом»:
список проверяемых файлов задаётся здесь, и правка его не требует обхода восьми файлов.
"""
import re
import subprocess
from pathlib import Path


class Narushenie:
    """Одно нарушение. Место обязательно: находка без адреса непроверяема."""

    def __init__(self, mesto: str, chto: str):
        self.mesto = mesto
        self.chto = chto

    def __str__(self):
        return f"{self.mesto}: {self.chto}"


def sobrat_fajly(koren: Path, obrazec: str = "*.md"):
    """Отслеживаемые И неотслеживаемые файлы, кроме игнорируемых.

    --others --exclude-standard обязательны: без них новый файл, ещё не добавленный в
    индекс, страж не видит вовсе, а его молчание читается как «чисто». Поймано на
    собственном CLAUDE.md — страж отчитался «29 файлов» при 30 существующих.
    """
    vyvod = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", obrazec],
        cwd=str(koren), capture_output=True, text=True, encoding="utf-8",
    ).stdout
    puti = []
    for s in vyvod.splitlines():
        s = s.strip()
        if s and (koren / s).is_file():
            puti.append(s)
    return sorted(set(puti))


def chitat(koren: Path, otn: str):
    """Строки файла с номерами, начиная с единицы. Битые байты не роняют прогон.

    РАЗБИЕНИЕ ПО "\\n", А НЕ splitlines() — и это не мелочь. splitlines() режет строку ещё и
    по вертикальной табуляции, переводу страницы и разделителям групп, то есть **съедает
    ровно те байты, которые ищет страж управляющих символов**: они исчезают, превратившись
    в границу строк, и проверка молчит на настоящем нарушении. Поймано тестом на стражей,
    чтением кода такое не находится. Побочная польза: номер строки совпадает с номером в
    редакторе, который тоже считает по "\\n".
    """
    try:
        text = (koren / otn).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    stroki = [s[:-1] if s.endswith("\r") else s for s in text.split("\n")]
    return list(enumerate(stroki, 1))


OGOVORKA = re.compile(r"страж: цитата")


def s_ogovorkoy(stroka: str) -> bool:
    """Строка помечена как цитата и из проверки исключена.

    Оговорка действует НА СТРОКУ, а не на файл: документ, объявляющий запрет, обязан
    запрещённое назвать, но исключённый целиком файл перестал бы проверяться и на
    настоящем откате правила.
    """
    return bool(OGOVORKA.search(stroka))
