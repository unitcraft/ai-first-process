# -*- coding: utf-8 -*-
"""ОДНА ДВЕРЬ запуска стражей: все исполняются в одном процессе.

ЗАЧЕМ ИМЕННО ОДНА ДВЕРЬ. Старт интерпретатора стоит десятки миллисекунд, а работа
отдельного стража — столько же или меньше. При запуске «процесс на стража» время гейта
складывается в основном из стартов, а не из полезной работы: на четырёх десятках стражей
это секунды чистого запуска, дороже всего, что они считают вместе взятые. Приём взят из
проекта, где это было замерено, и здесь применяется до того, как стражей станет много —
переделывать потом дороже, чем заложить сразу.

ЧТО ЭТО ДАЁТ, КРОМЕ ВРЕМЕНИ. Стражи читают одни и те же файлы: список путей собирается
один раз и передаётся всем. При отдельных процессах каждый собирал бы его заново.

ИЗОЛЯЦИЯ. Стражи не знают друг о друге: у каждого свой модуль и свой возврат. Падение
одного не уносит остальных — исключение перехватывается, страж помечается сломанным, и
прогон продолжается. Это важнее удобства: **поломка стража обязана отличаться от
нарушения правила**, иначе красный результат читается неверно и чинится не то.

ЗАПУСК:
    python scripts/run-guards.py [--verbose]

Проверяемый набор файлов подменяется переменными окружения — это нужно тесту на стражей,
чтобы прогонять их на подставных файлах, не трогая репозиторий:
    GUARD_FILES            — список путей через пробел вместо обхода репозитория
    GUARD_TEMPLATES_DIR    — каталог шаблонов вместо templates/

Код возврата: 0 — чисто, 1 — есть нарушения, 2 — сломан сам страж.
"""
import importlib
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

STRAZHI = [
    "control_chars",
    "absolute_paths",
    "secrets",
    "foreign_names",
    "broken_links",
    "terminology",
    "template_form",
    "template_registry",
]


class Kontekst:
    """Всё, что нужно стражу, собирается один раз и передаётся всем."""

    def __init__(self, koren: Path, fajly, katalog_shablonov: Path):
        self.koren = koren
        self.fajly = fajly
        self.katalog_shablonov = katalog_shablonov
        self.uvedomleniya = []

    def uvedomit(self, tekst: str):
        """Не нарушение, но и не молчание: проверка пропущена, и это надо сказать."""
        self.uvedomleniya.append(tekst)


def nayti_koren() -> Path:
    vyvod = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if vyvod.returncode != 0:
        print("run-guards: не репозиторий git", file=sys.stderr)
        sys.exit(2)
    return Path(vyvod.stdout.strip())


def nastroit_vyvod():
    """Вывод всегда UTF-8, независимо от кодировки консоли.

    ЗАЧЕМ. На Windows python пишет в конвейер в системной кодировке, и русский текст
    приходит нечитаемым. Опасность не в неудобстве: в кракозябрах слово опознаётся по
    длине, а не по смыслу, и отказ читается как успех. Страж, чей вывод нельзя прочитать,
    хуже отсутствующего — он создаёт видимость проверки.
    """
    for potok in (sys.stdout, sys.stderr):
        try:
            potok.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv):
    nastroit_vyvod()
    podrobno = "--verbose" in argv
    koren = nayti_koren()
    sys.path.insert(0, str(koren / "scripts"))

    from guards.common import sobrat_fajly  # noqa: E402  импорт после sys.path

    zadan = os.environ.get("GUARD_FILES", "").strip()
    if zadan:
        fajly = zadan.split()
    else:
        fajly = sobrat_fajly(koren)

    katalog_shablonov = Path(os.environ.get("GUARD_TEMPLATES_DIR", str(koren / "templates")))
    ctx = Kontekst(koren, fajly, katalog_shablonov)

    vsego_narusheniy = 0
    slomannyh = 0
    nachalo = time.perf_counter()

    for imya in STRAZHI:
        t0 = time.perf_counter()
        try:
            modul = importlib.import_module(f"guards.{imya}")
            nashli = modul.proverit(ctx)
        except Exception:
            slomannyh += 1
            print(f"СЛОМАН СТРАЖ {imya}:")
            print(traceback.format_exc())
            continue
        ms = (time.perf_counter() - t0) * 1000
        if nashli:
            vsego_narusheniy += len(nashli)
            print(f"{modul.NAZVANIE}:")
            for n in nashli:
                print(f"  {n}")
        if podrobno:
            print(f"  [{imya}: {len(nashli)} нарушений, {ms:.0f} мс]")

    for u in ctx.uvedomleniya:
        print(u)

    vsego_ms = (time.perf_counter() - nachalo) * 1000

    if slomannyh:
        print(f"\nСломанных стражей: {slomannyh}. Это не нарушение правил, а поломка проверки.")
        return 2
    if vsego_narusheniy:
        print(f"\nНарушений: {vsego_narusheniy}. Файлов проверено: {len(fajly)}, за {vsego_ms:.0f} мс.")
        return 1
    print(f"Чисто. Файлов проверено: {len(fajly)}, стражей {len(STRAZHI)}, за {vsego_ms:.0f} мс.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
