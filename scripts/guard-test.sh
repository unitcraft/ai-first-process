#!/usr/bin/env bash
#
# guard-test.sh — тест на стража.
#
# ЗАЧЕМ. У стража есть цена: ложное срабатывание опаснее отсутствия правила, потому что
# врущего стража отключают вместе с правилом. Поэтому проверяется и то, что он ловит
# нарушение, и то, что он МОЛЧИТ на чистом тексте. Это требование tooling.md, и оно уже
# окупилось: первая версия проверки 7 не находила ни одного заголовка (кириллический
# литерал сравнивался побайтово без use utf8), а проверка 6 по той же причине молчала бы
# на нарушении — то есть страж выглядел бы работающим и не работал.
#
# ЗАПУСК: scripts/guard-test.sh
# Код возврата: 0 — все случаи прошли, 1 — есть провалившиеся.

set -uo pipefail
KOREN="$(git rev-parse --show-toplevel)" || exit 1
cd "$KOREN" || exit 1

VREM="$(mktemp -d)"
trap 'rm -rf "$VREM"; rm -f "$KOREN/.denylist.test"' EXIT

PROSHLO=0
PROVALENO=0

# proverit <имя случая> <ожидаемый маркер|ЧИСТО> <файл...>
proverit() {
  local imya="$1" ozhidaem="$2"; shift 2
  local vyvod kod
  vyvod=$(GUARD_FILES="$*" bash scripts/guard.sh 2>&1); kod=$?
  if [ "$ozhidaem" = "ЧИСТО" ]; then
    if [ "$kod" -eq 0 ]; then PROSHLO=$((PROSHLO+1)); printf '  ✓ %s\n' "$imya"
    else PROVALENO=$((PROVALENO+1)); printf '  ✗ %s — страж сработал на чистом тексте:\n%s\n' "$imya" "$vyvod"; fi
  else
    if [ "$kod" -ne 0 ] && printf '%s' "$vyvod" | grep -q "$ozhidaem"; then
      PROSHLO=$((PROSHLO+1)); printf '  ✓ %s\n' "$imya"
    else
      PROVALENO=$((PROVALENO+1)); printf '  ✗ %s — ожидался маркер «%s», код %d, вывод:\n%s\n' "$imya" "$ozhidaem" "$kod" "$vyvod"
    fi
  fi
}

echo "Тест стража"

# --- молчание на чистом ---------------------------------------------------------
printf '# Заголовок\n\nОбычный текст со ссылкой [сюда](chisto.md) и словом секреты в прозе.\n' > "$VREM/chisto.md"
proverit "молчит на чистом тексте" ЧИСТО "$VREM/chisto.md"

# --- 1. управляющий байт --------------------------------------------------------
printf '# Заголовок\n\nтекст\x0bс управляющим байтом\n' > "$VREM/ctl.md"
proverit "ловит управляющий байт" "1. Управляющие байты" "$VREM/ctl.md"

# --- 2. абсолютные пути ---------------------------------------------------------
printf '# Заголовок\n\nПуть D:\\Sources\\proekt в тексте.\n' > "$VREM/put1.md"
proverit "ловит путь Windows" "2. Абсолютные пути" "$VREM/put1.md"
printf '# Заголовок\n\nПуть /mnt/d/rabota в тексте.\n' > "$VREM/put2.md"
proverit "ловит путь WSL" "2. Абсолютные пути" "$VREM/put2.md"
printf '# Заголовок\n\nОтносительный путь scripts/guard.sh законен.\n' > "$VREM/put3.md"
proverit "молчит на относительном пути" ЧИСТО "$VREM/put3.md"

# --- 3. секреты -----------------------------------------------------------------
printf '# Заголовок\n\ntoken = abcd1234efgh5678\n' > "$VREM/sek1.md"
proverit "ловит присвоение токена" "3. Похоже на секрет" "$VREM/sek1.md"
printf '# Заголовок\n\nСекреты живут в хранилище, в конфигурации только ссылки.\n' > "$VREM/sek2.md"
proverit "молчит на слове «секреты» в прозе" ЧИСТО "$VREM/sek2.md"

# --- 4. чужие имена -------------------------------------------------------------
printf 'ЧужойПроект\n' > "$KOREN/.denylist"
printf '# Заголовок\n\nЗдесь упомянут чужойпроект в другом регистре.\n' > "$VREM/imya.md"
proverit "ловит чужое имя без учёта регистра" "4. Чужие имена" "$VREM/imya.md"
rm -f "$KOREN/.denylist"
# Отдельным случаем, а не через proverit: уведомление о пропуске — не нарушение,
# и код возврата обязан остаться нулевым. Проверяется и текст, и код разом.
vyvod=$(GUARD_FILES="$VREM/chisto.md" bash scripts/guard.sh 2>&1); kod=$?
if [ "$kod" -eq 0 ] && printf '%s' "$vyvod" | grep -q "списка .denylist нет"; then
  PROSHLO=$((PROSHLO+1)); echo "  ✓ без списка говорит о пропуске вслух и не роняет проверку"
else
  PROVALENO=$((PROVALENO+1)); printf '  ✗ пропуск проверки на имена не объявлен, код %d, вывод:\n%s\n' "$kod" "$vyvod"
fi

# --- 5. битые ссылки ------------------------------------------------------------
printf '# Заголовок\n\nСсылка [туда](net-takogo-fajla.md).\n' > "$VREM/ssylka.md"
proverit "ловит битую ссылку" "5. Битые ссылки" "$VREM/ssylka.md"

# --- 6. терминология ------------------------------------------------------------
printf '# Заголовок\n\nРабота проходит G3 и дальше.\n' > "$VREM/term1.md"
proverit "ловит старый токен G3" "6. Терминология" "$VREM/term1.md"
printf '# Заголовок\n\nНа воротах КТ2 работа принимается.\n' > "$VREM/term2.md"
proverit "ловит слово «ворота» в косвенном падеже" "6. Терминология" "$VREM/term2.md"
printf '# Заголовок\n\nЗаголовок столбца Ворота с заглавной.\n' > "$VREM/term3.md"
proverit "ловит «Ворота» с заглавной — то, что пропустил grep -i" "6. Терминология" "$VREM/term3.md"
printf '# Заголовок\n\nНа точке КТ2 работа принимается.\n' > "$VREM/term4.md"
proverit "молчит на верной терминологии" ЧИСТО "$VREM/term4.md"
printf '# Заголовок\n\nЗапрещены Ворота и G3. <!-- страж: цитата -->\n' > "$VREM/term5.md"
proverit "пропускает строку с пометкой «страж: цитата»" ЧИСТО "$VREM/term5.md"
printf '# Заголовок\n\nПометка ниже, а нарушение выше: Ворота\n<!-- страж: цитата -->\n' > "$VREM/term6.md"
proverit "оговорка действует на строку, а не на соседние" "6. Терминология" "$VREM/term6.md"

# --- 7 и 8. форма шаблонов и реестр ---------------------------------------------
mkdir -p "$VREM/tpl"
printf '# Пустой шаблон\n\nБез обязательных разделов.\n' > "$VREM/tpl/pustoy.md"
printf '| Артефакт | Точка | Шаблон |\n| Пустой | 1 | [pustoy.md](pustoy.md) |\n' > "$VREM/tpl/README.md"
vyvod=$(GUARD_FILES="$VREM/chisto.md" GUARD_TEMPLATES_DIR="$VREM/tpl" bash scripts/guard.sh 2>&1); kod=$?
if [ "$kod" -ne 0 ] && printf '%s' "$vyvod" | grep -q "7. Форма шаблонов"; then
  PROSHLO=$((PROSHLO+1)); echo "  ✓ ловит шаблон без обязательных разделов"
else
  PROVALENO=$((PROVALENO+1)); printf '  ✗ шаблон без разделов не пойман, вывод:\n%s\n' "$vyvod"
fi

printf '# Шаблон\n\n## Требования\n## Шаблон\n## Критерий передачи\n## Критерий приёмки\n' > "$VREM/tpl/pustoy.md"
printf '| Артефакт | Точка | Шаблон |\n| Нет файла | 1 | [net-fajla.md](net-fajla.md) |\n' > "$VREM/tpl/README.md"
vyvod=$(GUARD_FILES="$VREM/chisto.md" GUARD_TEMPLATES_DIR="$VREM/tpl" bash scripts/guard.sh 2>&1); kod=$?
if [ "$kod" -ne 0 ] && printf '%s' "$vyvod" | grep -q "8. Реестр шаблонов"; then
  PROSHLO=$((PROSHLO+1)); echo "  ✓ ловит расхождение реестра и файлов в обе стороны"
else
  PROVALENO=$((PROVALENO+1)); printf '  ✗ расхождение реестра не поймано, вывод:\n%s\n' "$vyvod"
fi

# --- сам репозиторий ------------------------------------------------------------
vyvod=$(bash scripts/guard.sh 2>&1); kod=$?
if [ "$kod" -eq 0 ]; then
  PROSHLO=$((PROSHLO+1)); echo "  ✓ молчит на самом репозитории"
else
  PROVALENO=$((PROVALENO+1)); printf '  ✗ страж ругается на репозиторий:\n%s\n' "$vyvod"
fi

echo
echo "Прошло: $PROSHLO, провалено: $PROVALENO."
[ "$PROVALENO" -eq 0 ] || exit 1
exit 0
