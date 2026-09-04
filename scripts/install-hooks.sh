#!/usr/bin/env bash
#
# install-hooks.sh — поставить git-хук, который зовёт стража перед коммитом.
#
# ЗАЧЕМ ОТДЕЛЬНЫЙ СКРИПТ. Каталог .git/hooks не версионируется, поэтому после клонирования
# репозитория хука в нём нет — и страж перестаёт быть обязательным ровно тогда, когда за
# репозиторий садится новый человек, то есть в самый нужный момент. Скрипт запускается
# после каждого нового клона; напоминание об этом стоит в CLAUDE.md.
#
# core.hooksPath намеренно не занимаем: глобальный путь перекрыл бы .git/hooks всем
# репозиториям на машине и решал бы за них.
#
# ЗАПУСК: scripts/install-hooks.sh
# Код возврата: 0 — поставлен или уже стоял, 1 — не удалось.

set -uo pipefail
KOREN="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "не репозиторий git"; exit 1; }
cd "$KOREN" || exit 1

HUK=".git/hooks/pre-commit"
METKA="# ai-first-process guard hook"

if [ -f "$HUK" ] && grep -q "$METKA" "$HUK"; then
  echo "Хук уже стоит: $HUK"
  exit 0
fi

# Родной хук, если он есть, не глушим: переносим рядом и зовём после нашей проверки.
if [ -f "$HUK" ]; then
  mv "$HUK" "$HUK.local"
  echo "Прежний хук сохранён как $HUK.local и будет вызван после проверки."
fi

cat > "$HUK" <<'HOOKEOF'
#!/usr/bin/env bash
# ai-first-process guard hook
# Ставится scripts/install-hooks.sh. Обойти можно только --no-verify, и это не выход:
# непереносимый текст, попавший в историю, оттуда не удаляется.
set -uo pipefail
KOREN="$(git rev-parse --show-toplevel)"
bash "$KOREN/scripts/guard.sh" || {
  echo ""
  echo "pre-commit: страж нашёл нарушения — коммит отменён. Разобрать вывод выше."
  exit 1
}
[ -x "$KOREN/.git/hooks/pre-commit.local" ] && "$KOREN/.git/hooks/pre-commit.local"
exit 0
HOOKEOF

chmod +x "$HUK"
echo "Хук поставлен: $HUK"
echo "Проверка: bash scripts/guard.sh"
echo "Тест на стражей: python scripts/guard-test.py"
exit 0
