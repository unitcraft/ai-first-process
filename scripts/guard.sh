#!/usr/bin/env bash
#
# guard.sh — страж репозитория: проверяет то, что нарушается молча.
#
# ЗАЧЕМ. Репозиторий держит одно обещание — материал переносится в любой проект как есть.
# Обещание ломается тихо: имя заказчика в примере, абсолютный путь с чьей-то машины, битая
# ссылка после переименования файла. Ни одно из этого не видно при чтении диффа, поэтому
# проверяется машиной. Это же требует tooling.md: правило, которое можно нарушить молча,
# оформляется хуком, а не дисциплиной.
#
# ЗАПУСК:
#   scripts/guard.sh            проверить отслеживаемые .md
#   GUARD_FILES="a.md b.md" scripts/guard.sh   проверить перечисленные файлы (для теста стража)
#
# Код возврата: 0 — чисто, 1 — есть нарушения.
#
# ОГОВОРКА. Проверяется содержимое файлов на диске, а не в индексе. Для каталога документов
# разница мала, но она есть: если проиндексировано одно, а на диске другое, страж посмотрит
# на диск. Правило простое — не коммитить частями то, что проверяет страж.
#
# ПОЧЕМУ PERL, А НЕ grep -i. В этом окружении LANG пуст, и grep -i НЕ сворачивает регистр
# кириллицы: «Ворота» не находится по «ворота». Проверено 04.09.2026 — именно так заголовок
# столбца пережил сквозную замену. Все проверки по русскому тексту идут через perl с UTF-8.

set -uo pipefail

KOREN="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "guard: не репозиторий git"; exit 1; }
cd "$KOREN" || exit 1

if [ -n "${GUARD_FILES:-}" ]; then
  # shellcheck disable=SC2206
  FAJLY=($GUARD_FILES)
else
  # --others --exclude-standard добавляет НЕотслеживаемые файлы: без них новый файл,
  # ещё не добавленный в индекс, страж не видел бы вовсе, а его молчание читалось бы
  # как «чисто». Поймано 04.09.2026 на собственном CLAUDE.md.
  mapfile -t FAJLY < <(git ls-files --cached --others --exclude-standard '*.md')
fi

[ ${#FAJLY[@]} -eq 0 ] && { echo "guard: проверять нечего"; exit 0; }

NARUSHENIY=0
skazat() { printf '  %s\n' "$*"; }
narushenie() { NARUSHENIY=$((NARUSHENIY + 1)); skazat "$@"; }

# --- 1. Управляющие байты ------------------------------------------------------
# Делают файл невидимым для поиска: строка есть, а грепом не находится.
for f in "${FAJLY[@]}"; do
  [ -f "$f" ] || continue
  perl -ne 'print "$ARGV:$.\n" if /[\x00-\x08\x0B\x0C\x0E-\x1F]/' "$f" | while read -r m; do
    echo "УПРАВЛЯЮЩИЙ БАЙТ: $m"
  done
done > /tmp/guard-ctl.$$ 2>/dev/null
if [ -s /tmp/guard-ctl.$$ ]; then
  echo "1. Управляющие байты"
  while read -r l; do narushenie "$l"; done < /tmp/guard-ctl.$$
fi
rm -f /tmp/guard-ctl.$$

# --- 2. Абсолютные пути и машинно-специфичное ----------------------------------
# Путь с чьей-то машины делает файл непереносимым и выдаёт владельца.
PUTI=$(perl -ne '
  print "$ARGV:$.: $&\n" if /([A-Za-z]:[\\\/][A-Za-z0-9_.\\\/-]+)|(\/mnt\/[a-z]\/)|(\\\\wsl[^ ]*)|(\/home\/[a-z][a-z0-9_-]*)|(\/Users\/[A-Za-z])/;
' "${FAJLY[@]}" 2>/dev/null)
if [ -n "$PUTI" ]; then
  echo "2. Абсолютные пути"
  while read -r l; do narushenie "$l"; done <<< "$PUTI"
fi

# --- 3. Секреты ----------------------------------------------------------------
# Ищется присвоение значения, а не слово: текст о секретах здесь законен, значение — нет.
SEKRETY=$(perl -ne '
  print "$ARGV:$.\n" if /-----BEGIN [A-Z ]*PRIVATE KEY-----/;
  print "$ARGV:$.\n" if /(?i)\b(pass(word)?|passwd|token|secret|api[_-]?key)\b\s*[:=]\s*["\x27]?[A-Za-z0-9_\-\.\/+]{8,}/;
' "${FAJLY[@]}" 2>/dev/null)
if [ -n "$SEKRETY" ]; then
  echo "3. Похоже на секрет"
  while read -r l; do narushenie "$l"; done <<< "$SEKRETY"
fi

# --- 4. Чужие имена ------------------------------------------------------------
# Список локальный и не версионируется: он сам публикации не подлежит. Нет списка —
# проверка пропускается ВСЛУХ, а не молча: молчаливый пропуск читается как «чисто».
if [ -f .denylist ]; then
  IMENA=$(DENY=.denylist perl -e '
    use utf8; binmode(STDOUT, ":utf8");
    open(my $d, "<:utf8", $ENV{DENY}) or die;
    my @t = grep { length && !/^#/ } map { s/\s+$//r } <$d>;
    for my $f (@ARGV) {
      open(my $h, "<:utf8", $f) or next;
      while (my $l = <$h>) {
        for my $t (@t) { print "$f:$.: $t\n" if $l =~ /\Q$t\E/i; }
      }
    }
  ' "${FAJLY[@]}" 2>/dev/null)
  if [ -n "$IMENA" ]; then
    echo "4. Чужие имена"
    while read -r l; do narushenie "$l"; done <<< "$IMENA"
  fi
else
  echo "4. Чужие имена: списка .denylist нет, проверка не выполнялась"
fi

# --- 5. Битые относительные ссылки ---------------------------------------------
SSYLKI=$(perl -e '
  for my $f (@ARGV) {
    open(my $h, "<", $f) or next;
    my $dir = $f; $dir =~ s{/[^/]*$}{}; $dir = "." if $dir eq $f;
    while (my $l = <$h>) {
      while ($l =~ m{\]\(((?:\.\.?/)?[A-Za-z0-9_./-]+\.md)\)}g) {
        my $p = "$dir/$1";
        print "$f:$.: $1\n" unless -e $p;
      }
    }
  }
' "${FAJLY[@]}" 2>/dev/null)
if [ -n "$SSYLKI" ]; then
  echo "5. Битые ссылки"
  while read -r l; do narushenie "$l"; done <<< "$SSYLKI"
fi

# --- 6. Терминология -----------------------------------------------------------
# Решение 04.09.2026: контрольные точки КТ1..КТ8. Старые формы запрещены, чтобы
# переименование не отползло обратно при следующей правке.
#
# Оговорка на строку, а не на файл: документ, который САМ объявляет запрет, обязан
# запрещённое назвать — иначе правило нельзя прочитать. Такая строка помечается
# «страж: цитата» и пропускается. Пометка на строке, а не на файле, потому что
# исключённый целиком файл перестаёт проверяться и на настоящем откате правила.
TERMIN=$(perl -CSD -Mutf8 -ne '
  next if /страж: цитата/;
  print "$ARGV:$.: старый токен контрольной точки\n" if /\bG[0-7]\b/;
' "${FAJLY[@]}" 2>/dev/null)
TERMIN2=$(perl -CSD -Mutf8 -ne '
  next if /страж: цитата/;
  print "$ARGV:$.: слово «ворота»\n" if /ворот/i;
' "${FAJLY[@]}" 2>/dev/null)
if [ -n "$TERMIN$TERMIN2" ]; then
  echo "6. Терминология"
  [ -n "$TERMIN" ] && while read -r l; do narushenie "$l"; done <<< "$TERMIN"
  [ -n "$TERMIN2" ] && while read -r l; do narushenie "$l"; done <<< "$TERMIN2"
fi

# --- 7. Форма шаблонов ---------------------------------------------------------
# Четыре обязательных раздела у каждого шаблона: без них шаблон не отвечает на вопрос
# «чем это принимают», а реестр обещает, что отвечает.
TDIR="${GUARD_TEMPLATES_DIR:-templates}"
if [ -z "${GUARD_FILES:-}" ] || [ -n "${GUARD_TEMPLATES_DIR:-}" ]; then
  echo_hdr=0
  for f in "$TDIR"/*.md; do
    [ "$f" = "$TDIR/README.md" ] && continue
    [ -f "$f" ] || continue
    n=$(perl -CSD -Mutf8 -ne 'print "1\n" if /^## (Требования|Шаблон|Критерий передачи|Критерий приёмки)/' "$f" | wc -l)
    if [ "$n" -lt 4 ]; then
      [ "$echo_hdr" = 0 ] && { echo "7. Форма шаблонов"; echo_hdr=1; }
      narushenie "$f: обязательных разделов $n из 4"
    fi
  done

  # --- 8. Реестр шаблонов ↔ файлы ----------------------------------------------
  # Двусторонне: шаблон без строки в реестре не найдут, строка без файла — обещание впустую.
  echo_hdr=0
  REESTR="$TDIR/README.md"
  for f in "$TDIR"/*.md; do
    b=$(basename "$f")
    [ "$b" = "README.md" ] && continue
    grep -q "($b)" "$REESTR" || {
      [ "$echo_hdr" = 0 ] && { echo "8. Реестр шаблонов"; echo_hdr=1; }
      narushenie "$b: файл есть, строки в реестре нет"
    }
  done
  for b in $(grep -oE '\(([a-z0-9-]+\.md)\)' "$REESTR" | tr -d '()' | sort -u); do
    [ -f "$TDIR/$b" ] || {
      [ "$echo_hdr" = 0 ] && { echo "8. Реестр шаблонов"; echo_hdr=1; }
      narushenie "$b: строка в реестре есть, файла нет"
    }
  done
fi

# --- Итог ----------------------------------------------------------------------
if [ "$NARUSHENIY" -gt 0 ]; then
  echo
  echo "Нарушений: $NARUSHENIY. Файлов проверено: ${#FAJLY[@]}."
  exit 1
fi
echo "Чисто. Файлов проверено: ${#FAJLY[@]}."
exit 0
