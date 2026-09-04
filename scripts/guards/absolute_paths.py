# -*- coding: utf-8 -*-
"""Абсолютные и машинно-специфичные пути.

ЗАЧЕМ. Репозиторий держит одно обещание — материал переносится в любой проект как есть.
Путь с чьей-то машины ломает обещание дважды: у читателя такого пути нет, и заодно он
выдаёт владельца машины. Относительные пути внутри репозитория законны и не трогаются.
"""
import re

from .common import Narushenie, chitat, s_ogovorkoy

NAZVANIE = "Абсолютные пути"

OBRAZCY = [
    (re.compile(r"[A-Za-z]:[\\/][A-Za-z0-9_.\\/-]+"), "путь Windows"),
    (re.compile(r"/mnt/[a-z]/"), "путь WSL"),
    (re.compile(r"\\\\wsl[^\s]*"), "сетевой путь WSL"),
    (re.compile(r"/home/[a-z][a-z0-9_-]*"), "домашний каталог Linux"),
    (re.compile(r"/Users/[A-Za-z]"), "домашний каталог macOS"),
]


def proverit(ctx):
    nashli = []
    for f in ctx.fajly:
        for nomer, stroka in chitat(ctx.koren, f):
            if s_ogovorkoy(stroka):
                continue
            for obrazec, imya in OBRAZCY:
                m = obrazec.search(stroka)
                if m:
                    nashli.append(Narushenie(f"{f}:{nomer}", f"{imya}: {m.group(0)}"))
                    break
    return nashli
