# -*- coding: utf-8 -*-
"""Чужие имена по локальному списку.

ЗАЧЕМ. Имя заказчика, организации или чужого проекта в примере делает файл непереносимым
и уносит наружу то, что наружу не предназначалось. Ловится по списку, потому что
универсального признака у имени нет.

ПОЧЕМУ СПИСОК НЕ ВЕРСИОНИРУЕТСЯ. Сам список — перечень имён, то есть ровно то, что
запрещено хранить здесь. Он лежит в `.denylist` в корне и стоит в `.gitignore`.

ПОЧЕМУ ОТСУТСТВИЕ СПИСКА ОБЪЯВЛЯЕТСЯ ВСЛУХ. Молчаливый пропуск проверки читается как
«чисто» — это тот же класс, что «пустой вывод не означает такого нет». Поэтому страж
возвращает не нарушение, а уведомление, и оно печатается.
"""
from .common import Narushenie, chitat

NAZVANIE = "Чужие имена"
SPISOK = ".denylist"


def proverit(ctx):
    put = ctx.koren / SPISOK
    if not put.is_file():
        ctx.uvedomit(f"{NAZVANIE}: списка {SPISOK} нет, проверка не выполнялась")
        return []

    tokeny = []
    for s in put.read_text(encoding="utf-8", errors="replace").splitlines():
        s = s.strip()
        if s and not s.startswith("#"):
            tokeny.append(s.lower())
    if not tokeny:
        ctx.uvedomit(f"{NAZVANIE}: список {SPISOK} пуст, проверка не выполнялась")
        return []

    nashli = []
    for f in ctx.fajly:
        for nomer, stroka in chitat(ctx.koren, f):
            nizhniy = stroka.lower()
            for t in tokeny:
                if t in nizhniy:
                    nashli.append(Narushenie(f"{f}:{nomer}", f"чужое имя «{t}»"))
                    break
    return nashli
