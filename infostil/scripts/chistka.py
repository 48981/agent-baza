#!/usr/bin/env python3
"""Просмотр и удаление невидимых знаков в тексте.

  chistka.py файл            — показать: позиция · код · имя · контекст
  chistka.py файл --fix      — удалить, результат в файл (оригинал → файл.bak)
  chistka.py - < текст       — читать stdin, показать
  chistka.py - --fix < в > из — очищенный текст в stdout

Удаляет: нулевой ширины (U+200B..200F), управляющие направлением (202A..202E, 2066..2069),
невидимые операторы (2060..2064), BOM (FEFF), мягкий перенос (00AD), теги (E0000..E007F),
прочие управляющие. ZWJ и селекторы вариантов внутри эмодзи не трогает.
Неразрывные и узкие пробелы (00A0, 202F, 2009) только показывает: в русской типографике они законны.
Статистическую метку в подборе слов (водяной знак OpenAI textGrain и подобные) эта чистка
не видит и не снимает: её нет в знаках, она в выборе слов.
"""
import sys, unicodedata, shutil

REMOVE = set(range(0x200B, 0x2010)) | set(range(0x202A, 0x202F)) | set(range(0x2060, 0x2065)) \
    | set(range(0x2066, 0x206A)) | {0xFEFF, 0x00AD, 0x180E, 0x034F, 0x3164, 0xFFA0} | set(range(0xE0000, 0xE0080))
KEEP_SPACES = {0x00A0, 0x202F, 0x2009, 0x2007, 0x2008, 0x200A}
EMOJI_GLUE = {0x200D, 0xFE0F, 0xFE0E}


def is_emoji(ch):
    o = ord(ch)
    return 0x1F000 <= o <= 0x1FFFF or 0x2600 <= o <= 0x27BF or 0x2190 <= o <= 0x21FF or o in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2B50, 0x2B55)


def scan(text):
    """Список (индекс, знак, действие) — действие 'del' или 'show'."""
    out = []
    for i, ch in enumerate(text):
        o = ord(ch)
        if o in EMOJI_GLUE:
            prev = text[i - 1] if i else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if is_emoji(prev) or (o == 0x200D and is_emoji(nxt)) or prev in ("#", "*") or prev.isdigit():
                continue
            out.append((i, ch, "del"))
        elif o in REMOVE:
            out.append((i, ch, "del"))
        elif o in KEEP_SPACES:
            out.append((i, ch, "show"))
        elif unicodedata.category(ch) == "Cc" and ch not in "\n\r\t":
            out.append((i, ch, "del"))
        elif unicodedata.category(ch) in ("Cf", "Co", "Cn") and o not in EMOJI_GLUE:
            out.append((i, ch, "del"))
    return out


def report(text, hits):
    line = lambda p: text.count("\n", 0, p) + 1
    for i, ch, act in hits:
        ctx = text[max(0, i - 12):i].replace("\n", "⏎") + "⟦⟧" + text[i + 1:i + 12].replace("\n", "⏎")
        name = unicodedata.name(ch, "БЕЗ ИМЕНИ")
        print(f"стр {line(i):>4} · поз {i:>6} · U+{ord(ch):04X} · {name} · {'удалить' if act == 'del' else 'оставить'} · {ctx}")
    d = sum(1 for h in hits if h[2] == "del")
    print(f"\nНайдено: {len(hits)} (к удалению {d}, к просмотру {len(hits) - d}). Длина текста: {len(text)} знаков.")


def clean(text, hits):
    drop = {i for i, _, a in hits if a == "del"}
    return "".join(c for i, c in enumerate(text) if i not in drop)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if a != "--fix"]
    fix = "--fix" in sys.argv
    if not args:
        print(__doc__); return 2
    src = args[0]
    if src == "-":
        text = sys.stdin.buffer.read().decode("utf-8")
    else:
        text = open(src, encoding="utf-8").read()
    hits = scan(text)
    if not fix:
        report(text, hits) if hits else print("Невидимых знаков не найдено.")
        return 0
    res = clean(text, hits)
    if src == "-":
        sys.stdout.buffer.write(res.encode("utf-8"))
        print(f"Удалено знаков: {len(text) - len(res)}", file=sys.stderr)
    else:
        if res != text:
            shutil.copy(src, src + ".bak")
            open(src, "w", encoding="utf-8", newline="").write(res)
        print(f"Удалено знаков: {len(text) - len(res)}" + (f"; оригинал в {src}.bak" if res != text else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
