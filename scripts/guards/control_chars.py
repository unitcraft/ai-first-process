# -*- coding: utf-8 -*-
"""Управляющие байты в тексте.

ЗАЧЕМ. Управляющий байт делает строку невидимой для поиска: строка в файле есть, глазом
читается, а грепом не находится. Дефект, который ищут часами, потому что ищут не то.
Попадают они туда не руками — их вставляют инструменты при неудачной обработке
экранирования.
"""
from .common import Narushenie, chitat

NAZVANIE = "Управляющие байты"
ZAPRESHENY = set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20))


def proverit(ctx):
    nashli = []
    for f in ctx.fajly:
        for nomer, stroka in chitat(ctx.koren, f):
            plohie = {c for c in stroka if ord(c) in ZAPRESHENY}
            if plohie:
                kody = ", ".join(f"0x{ord(c):02X}" for c in sorted(plohie))
                nashli.append(Narushenie(f"{f}:{nomer}", f"управляющие байты {kody}"))
    return nashli
