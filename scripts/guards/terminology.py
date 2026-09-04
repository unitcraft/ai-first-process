# -*- coding: utf-8 -*-
"""Терминология контрольных точек.

ЗАЧЕМ. Термин переименован решением: контрольные точки КТ1..КТ8. Прежнее слово и прежние
буквенные токены запрещены — не из вкуса, а чтобы переименование не отползло обратно при
следующей правке. Это храповик над терминологией: один раз договорились, машина держит.

ПОЧЕМУ ЭТО НЕ ЛОВИТСЯ ГРЕПОМ. В окружении с пустым LANG `grep -i` не сворачивает регистр
кириллицы: слово с заглавной не находится по строчному написанию. Именно так заголовок
столбца пережил сквозную замену, а проверка молчала. Здесь сравнение идёт над строками
Python, где регистр сворачивается правильно для любого алфавита.
"""
import re

from .common import Narushenie, chitat, s_ogovorkoy

NAZVANIE = "Терминология"

STARYY_TOKEN = re.compile(r"\bG[0-7]\b")
STAROE_SLOVO = re.compile(r"ворот", re.IGNORECASE)


def proverit(ctx):
    nashli = []
    for f in ctx.fajly:
        for nomer, stroka in chitat(ctx.koren, f):
            if s_ogovorkoy(stroka):
                continue
            if STARYY_TOKEN.search(stroka):
                nashli.append(Narushenie(f"{f}:{nomer}", "прежний буквенный токен вместо КТ"))
            if STAROE_SLOVO.search(stroka):
                nashli.append(Narushenie(f"{f}:{nomer}", "прежнее слово вместо «контрольная точка»"))
    return nashli
