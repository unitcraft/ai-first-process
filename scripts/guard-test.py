# -*- coding: utf-8 -*-
"""Тест на стражей: срабатывание И молчание.

ЗАЧЕМ. У стража есть цена: ложное срабатывание опаснее отсутствия правила, потому что
врущего стража отключают вместе с правилом, которое он защищал. Поэтому каждый случай
проверяется с двух сторон — ловит ли он нарушение и молчит ли на чистом тексте.

ЭТО УЖЕ ОКУПИЛОСЬ. На первой, ещё не питоновской версии тест нашёл три дефекта в самих
стражах, и один из них — молчание на нарушении, то есть страж выглядел работающим и не
работал. Такое не находится чтением кода.

ПОЧЕМУ ТОЖЕ ОДНА ДВЕРЬ. Стражи вызываются функциями в этом же процессе, а не запуском
раннера на каждый случай: два десятка случаев по процессу на случай — это секунды старта
интерпретатора против миллисекунд полезной работы.

ЗАПУСК: python scripts/guard-test.py
Код возврата: 0 — все случаи прошли, 1 — есть провалившиеся.
"""
import importlib
import subprocess
import sys
import tempfile
from pathlib import Path

KOREN = Path(subprocess.run(
    ["git", "rev-parse", "--show-toplevel"],
    capture_output=True, text=True, encoding="utf-8",
).stdout.strip())
sys.path.insert(0, str(KOREN / "scripts"))

PROSHLO = 0
PROVALENO = 0


class KontekstTesta:
    def __init__(self, koren, fajly, katalog_shablonov=None):
        self.koren = Path(koren)
        self.fajly = fajly
        self.katalog_shablonov = Path(katalog_shablonov) if katalog_shablonov else self.koren / "templates"
        self.uvedomleniya = []

    def uvedomit(self, tekst):
        self.uvedomleniya.append(tekst)


def sluchay(imya, strazh, ctx, zhdem_narusheniy: bool, zhdem_v_tekste=None):
    """zhdem_narusheniy=False — проверка молчания, самая ценная половина теста."""
    global PROSHLO, PROVALENO
    modul = importlib.import_module(f"guards.{strazh}")
    try:
        nashli = modul.proverit(ctx)
    except Exception as e:  # поломка стража — это провал случая, а не падение теста
        PROVALENO += 1
        print(f"  ✗ {imya} — страж упал: {e}")
        return
    est = len(nashli) > 0
    if est != zhdem_narusheniy:
        PROVALENO += 1
        chego = "нарушение" if zhdem_narusheniy else "молчание"
        print(f"  ✗ {imya} — ожидалось {chego}, получено {len(nashli)} нарушений")
        for n in nashli:
            print(f"      {n}")
        return
    if zhdem_v_tekste and not any(zhdem_v_tekste in str(n) for n in nashli):
        PROVALENO += 1
        print(f"  ✗ {imya} — нет ожидаемого текста «{zhdem_v_tekste}» в: {[str(n) for n in nashli]}")
        return
    PROSHLO += 1
    print(f"  ✓ {imya}")


def zapisat(katalog: Path, imya: str, tekst: str) -> str:
    (katalog / imya).write_text(tekst, encoding="utf-8", newline="\n")
    return str(katalog / imya)


def main():
    global PROSHLO, PROVALENO
    print("Тест стражей")
    vrem = Path(tempfile.mkdtemp())

    # --- управляющие байты ---
    f = zapisat(vrem, "ctl.md", "# Заголовок\n\nтекст\x0bс байтом\n")
    sluchay("ловит управляющий байт", "control_chars", KontekstTesta(vrem, ["ctl.md"]), True, "0x0B")
    f = zapisat(vrem, "chisto.md", "# Заголовок\n\nОбычный текст про секреты и токены в прозе.\n")
    sluchay("молчит на чистом тексте", "control_chars", KontekstTesta(vrem, ["chisto.md"]), False)

    # --- абсолютные пути ---
    zapisat(vrem, "put1.md", "# З\n\nПуть C:\\Rabota\\proekt в тексте.\n")
    sluchay("ловит путь Windows", "absolute_paths", KontekstTesta(vrem, ["put1.md"]), True)
    zapisat(vrem, "put2.md", "# З\n\nПуть /mnt/d/rabota в тексте.\n")
    sluchay("ловит путь WSL", "absolute_paths", KontekstTesta(vrem, ["put2.md"]), True)
    zapisat(vrem, "put3.md", "# З\n\nОтносительный путь scripts/guard.sh законен.\n")
    sluchay("молчит на относительном пути", "absolute_paths", KontekstTesta(vrem, ["put3.md"]), False)

    # --- секреты ---
    zapisat(vrem, "sek1.md", "# З\n\ntoken = abcd1234efgh5678\n")
    sluchay("ловит присвоение токена", "secrets", KontekstTesta(vrem, ["sek1.md"]), True)
    zapisat(vrem, "sek2.md", "# З\n\nСекреты живут в хранилище, в конфигурации только ссылки.\n")
    sluchay("молчит на слове «секреты» в прозе", "secrets", KontekstTesta(vrem, ["sek2.md"]), False)

    # --- чужие имена ---
    (vrem / ".denylist").write_text("ЧужойПроект\n", encoding="utf-8", newline="\n")
    zapisat(vrem, "imya.md", "# З\n\nЗдесь упомянут чужойпроект в другом регистре.\n")
    sluchay("ловит чужое имя без учёта регистра", "foreign_names", KontekstTesta(vrem, ["imya.md"]), True)
    (vrem / ".denylist").unlink()
    ctx = KontekstTesta(vrem, ["chisto.md"])
    importlib.import_module("guards.foreign_names").proverit(ctx)
    if ctx.uvedomleniya and "нет" in ctx.uvedomleniya[0]:
        PROSHLO += 1
        print("  ✓ без списка объявляет пропуск вслух, а не молчит")
    else:
        PROVALENO += 1
        print(f"  ✗ пропуск проверки на имена не объявлен: {ctx.uvedomleniya}")

    # --- битые ссылки ---
    zapisat(vrem, "ssylka.md", "# З\n\nСсылка [туда](net-takogo.md).\n")
    sluchay("ловит битую ссылку", "broken_links", KontekstTesta(vrem, ["ssylka.md"]), True)
    zapisat(vrem, "ssylka2.md", "# З\n\nСсылка [сюда](chisto.md) и якорь [туда](chisto.md#razdel).\n")
    sluchay("молчит на живой ссылке и на якоре", "broken_links", KontekstTesta(vrem, ["ssylka2.md"]), False)

    # --- терминология ---
    zapisat(vrem, "term1.md", "# З\n\nРабота проходит G3 и дальше.\n")
    sluchay("ловит прежний буквенный токен", "terminology", KontekstTesta(vrem, ["term1.md"]), True)
    zapisat(vrem, "term2.md", "# З\n\nНа воротах КТ2 работа принимается.\n")
    sluchay("ловит прежнее слово в косвенном падеже", "terminology", KontekstTesta(vrem, ["term2.md"]), True)
    zapisat(vrem, "term3.md", "# З\n\nЗаголовок столбца Ворота с заглавной.\n")
    sluchay("ловит его же с заглавной — то, что пропускал grep -i", "terminology",
            KontekstTesta(vrem, ["term3.md"]), True)
    zapisat(vrem, "term4.md", "# З\n\nНа точке КТ2 работа принимается.\n")
    sluchay("молчит на верной терминологии", "terminology", KontekstTesta(vrem, ["term4.md"]), False)
    zapisat(vrem, "term5.md", "# З\n\nЗапрещены Ворота и G3. <!-- страж: цитата -->\n")
    sluchay("пропускает строку с пометкой «страж: цитата»", "terminology",
            KontekstTesta(vrem, ["term5.md"]), False)
    zapisat(vrem, "term6.md", "# З\n\nНарушение здесь: Ворота\n<!-- страж: цитата -->\n")
    sluchay("оговорка действует на строку, а не на соседние", "terminology",
            KontekstTesta(vrem, ["term6.md"]), True)

    # --- форма шаблонов и реестр ---
    tpl = vrem / "tpl"
    tpl.mkdir(exist_ok=True)
    zapisat(tpl, "pustoy.md", "# Пустой\n\nБез обязательных разделов.\n")
    zapisat(tpl, "README.md", "| Артефакт | Точка | Шаблон |\n| Пустой | 1 | [pustoy.md](pustoy.md) |\n")
    sluchay("ловит шаблон без обязательных разделов", "template_form",
            KontekstTesta(vrem, [], tpl), True)
    zapisat(tpl, "pustoy.md",
            "# Шаблон\n\n## Требования к содержанию\n\n## Шаблон\n\n## Критерий передачи\n\n## Критерий приёмки\n")
    sluchay("молчит на шаблоне со всеми разделами", "template_form",
            KontekstTesta(vrem, [], tpl), False)
    sluchay("молчит, когда реестр и файлы совпадают", "template_registry",
            KontekstTesta(vrem, [], tpl), False)
    zapisat(tpl, "README.md", "| Артефакт | Точка | Шаблон |\n| Нет файла | 1 | [net-fajla.md](net-fajla.md) |\n")
    sluchay("ловит расхождение реестра и файлов в обе стороны", "template_registry",
            KontekstTesta(vrem, [], tpl), True)

    # --- сам репозиторий: стражи обязаны на нём молчать ---
    kod = subprocess.run([sys.executable, str(KOREN / "scripts" / "run-guards.py")],
                         capture_output=True, text=True, encoding="utf-8")
    if kod.returncode == 0:
        PROSHLO += 1
        print("  ✓ молчат на самом репозитории")
    else:
        PROVALENO += 1
        print(f"  ✗ страж ругается на репозиторий:\n{kod.stdout}{kod.stderr}")

    print(f"\nПрошло: {PROSHLO}, провалено: {PROVALENO}.")
    return 1 if PROVALENO else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
