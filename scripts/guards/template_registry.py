# -*- coding: utf-8 -*-
"""Реестр шаблонов и файлы должны совпадать — в обе стороны.

ЗАЧЕМ. Расхождение ломается в обе стороны и по-разному: шаблон без строки в реестре не
найдут (он есть, но о нём никто не знает), строка без файла — обещание впустую (о нём
знают, но его нет). Проверять одну сторону бесполезно: пропущенной окажется другая.
"""
import re

from .common import Narushenie

NAZVANIE = "Реестр шаблонов"
SSYLKA = re.compile(r"\(([a-z0-9-]+\.md)\)")


def proverit(ctx):
    katalog = ctx.katalog_shablonov
    reestr = katalog / "README.md"
    if not reestr.is_file():
        return [Narushenie(str(reestr.name), "реестра шаблонов нет")]

    text = reestr.read_text(encoding="utf-8", errors="replace")
    v_reestre = set(SSYLKA.findall(text))
    na_diske = {p.name for p in katalog.glob("*.md") if p.name != "README.md"}

    nashli = []
    for imya in sorted(na_diske - v_reestre):
        nashli.append(Narushenie(imya, "файл есть, строки в реестре нет"))
    for imya in sorted(v_reestre - na_diske):
        nashli.append(Narushenie(imya, "строка в реестре есть, файла нет"))
    return nashli
