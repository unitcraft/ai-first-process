# -*- coding: utf-8 -*-
"""Похожее на секрет.

ЗАЧЕМ. Секрет, попавший в историю git, оттуда не удаляется — только перезаписью истории и
сменой всех значений. Проверка стоит до коммита, потому что после неё уже поздно.

ПОЧЕМУ ИЩЕТСЯ ПРИСВОЕНИЕ, А НЕ СЛОВО. Здесь методология, и слова «секрет», «токен»,
«пароль» встречаются в прозе законно и часто. Ловится значение: имя, знак присвоения и
непробельная строка достаточной длины. Это ровно тот случай, где страж по слову давал бы
ложные срабатывания на каждом втором файле и был бы отключён в первый же день.
"""
import re

from .common import Narushenie, chitat, s_ogovorkoy

NAZVANIE = "Похоже на секрет"

PRISVOENIE = re.compile(
    r"\b(pass(word)?|passwd|token|secret|api[_-]?key)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-./+]{8,}",
    re.IGNORECASE,
)
KLYUCH = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def proverit(ctx):
    nashli = []
    for f in ctx.fajly:
        for nomer, stroka in chitat(ctx.koren, f):
            if s_ogovorkoy(stroka):
                continue
            if KLYUCH.search(stroka):
                nashli.append(Narushenie(f"{f}:{nomer}", "заголовок приватного ключа"))
            elif PRISVOENIE.search(stroka):
                nashli.append(Narushenie(f"{f}:{nomer}", "присвоение значения секрету"))
    return nashli
