# -*- coding: utf-8 -*-
"""Битые относительные ссылки между документами.

ЗАЧЕМ. Документы связаны плотно: карта норм, реестр шаблонов, ссылки из шаблонов на
контрольные точки. Переименование файла ломает ссылки молча — markdown не жалуется, и
читатель узнаёт об этом, только кликнув. Проверка дешёвая и ловит целый класс.

ГРАНИЦА. Проверяются только относительные ссылки на `.md`. Внешние адреса не трогаются:
их проверка требует сети, а сеть делает страж недетерминированным — он начал бы краснеть
от чужой недоступности.
"""
import re

from .common import Narushenie, chitat

NAZVANIE = "Битые ссылки"
SSYLKA = re.compile(r"\]\(((?:\.\.?/)?[A-Za-z0-9_./-]+\.md)(?:#[^)]*)?\)")


def proverit(ctx):
    nashli = []
    for f in ctx.fajly:
        katalog = (ctx.koren / f).parent
        for nomer, stroka in chitat(ctx.koren, f):
            for m in SSYLKA.finditer(stroka):
                cel = m.group(1)
                if not (katalog / cel).exists():
                    nashli.append(Narushenie(f"{f}:{nomer}", f"ссылка в никуда: {cel}"))
    return nashli
