# -*- coding: utf-8 -*-
"""Форма шаблонов артефактов.

ЗАЧЕМ. Реестр шаблонов обещает читателю, что в каждом файле есть требования, сам шаблон и
ДВА критерия — передачи и приёмки. Шаблон без критериев не отвечает на главный вопрос
«чем это принимают», и передача возвращается к «мне кажется, готово». Обещание реестра
проверяется, а не подразумевается.

ГРАНИЦА. Проверяется наличие разделов, а не их содержание: содержание — предмет чтения
человеком, и страж, полезший в него, начал бы давать ложные срабатывания.
"""
from .common import Narushenie

NAZVANIE = "Форма шаблонов"
OBYAZATELNYE = ("Требования", "Шаблон", "Критерий передачи", "Критерий приёмки")


def proverit(ctx):
    katalog = ctx.katalog_shablonov
    if not katalog.is_dir():
        return []
    nashli = []
    for put in sorted(katalog.glob("*.md")):
        if put.name == "README.md":
            continue
        text = put.read_text(encoding="utf-8", errors="replace")
        est = set()
        for stroka in text.splitlines():
            if stroka.startswith("## "):
                zagolovok = stroka[3:].strip()
                for o in OBYAZATELNYE:
                    if zagolovok.startswith(o):
                        est.add(o)
        nekhvatka = [o for o in OBYAZATELNYE if o not in est]
        if nekhvatka:
            otn = put.relative_to(ctx.koren) if ctx.koren in put.parents else put.name
            nashli.append(Narushenie(str(otn), "нет разделов: " + ", ".join(nekhvatka)))
    return nashli
