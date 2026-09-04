#!/usr/bin/env bash
#
# guard.sh — точка входа стражей. Вся работа в scripts/run-guards.py, здесь только выбор
# интерпретатора.
#
# ЗАЧЕМ ОТДЕЛЬНАЯ ОБЁРТКА, А НЕ ВЫЗОВ PYTHON НАПРЯМУЮ. Имя интерпретатора не переносимо:
# на Windows рабочим оказывается `python`, а `python3` подменён заглушкой магазина
# приложений, которая печатает предложение установить Python и возвращает успех — то есть
# страж «отработал бы» и ничего не проверил. На Linux обычно наоборот: есть `python3`, а
# `python` может отсутствовать. Выбор делается здесь, один раз, а не в каждом вызывающем.
#
# ЗАПУСК: bash scripts/guard.sh [--verbose]
# Код возврата: 0 — чисто, 1 — нарушения, 2 — сломан страж или нет интерпретатора.

set -uo pipefail
KOREN="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "guard: не репозиторий git"; exit 2; }

# Заглушку магазина приложений отсеиваем проверкой самого запуска, а не наличия файла:
# `command -v python3` её находит, и только вызов показывает, что это не Python.
PYTHON=""
for k in python3 python py; do
  if command -v "$k" >/dev/null 2>&1 && "$k" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
    PYTHON="$k"; break
  fi
done
[ -n "$PYTHON" ] || { echo "guard: не найден рабочий интерпретатор Python (пробовал python3, python, py)"; exit 2; }

exec "$PYTHON" "$KOREN/scripts/run-guards.py" "$@"
