#!/usr/bin/env python3
"""translate_overlay.py — 大页面的散文覆盖翻译辅助。

代码围栏逐字节保留；只抽取围栏外的散文行供翻译，再按行回填。

用法：
  python3 translate_overlay.py extract <file.mdx> [out.tsv]
      # 打印并写出 TSV：行号<TAB>原文（围栏外非空行）
  python3 translate_overlay.py apply <file.mdx> <tsv>
      # 用 TSV 中的译文替换对应行；文本为 \x00DROP\x00 时删除该行
"""
import sys


def prose_lines(text):
    fences = set()
    in_fence = False
    closer = None
    for i, line in enumerate(text.split("\n"), 1):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            if not in_fence:
                in_fence, closer = True, s[0] * len([c for c in s if c == s[0]])
                fences.add(i)
            elif s[0] == closer[0]:
                in_fence = False
                fences.add(i)
        elif in_fence:
            fences.add(i)
    return fences


def main():
    cmd = sys.argv[1]
    path = sys.argv[2]
    text = open(path, encoding="utf-8").read()
    if cmd == "extract":
        skip = prose_lines(text)
        rows = []
        for i, line in enumerate(text.split("\n"), 1):
            if i in skip or not line.strip():
                continue
            rows.append((i, line))
        out = sys.argv[3] if len(sys.argv) > 3 else path + ".prose.tsv"
        with open(out, "w", encoding="utf-8") as f:
            for i, line in rows:
                f.write(f"{i}\t{line}\n")
        for i, line in rows:
            print(f"{i}\t{line}")
        print(f"# {len(rows)} 行 -> {out}", file=sys.stderr)
    elif cmd == "apply":
        tsv = sys.argv[3]
        repl = {}
        drop = set()
        for ln in open(tsv, encoding="utf-8"):
            if not ln.strip() or ln.startswith("#"):
                continue
            no, _, txt = ln.rstrip("\n").partition("\t")
            no = int(no)
            if txt.strip() in ("\\x00DROP\\x00", "\x00DROP\x00"):
                drop.add(no)
            else:
                repl[no] = txt
        lines = text.split("\n")
        for no, txt in repl.items():
            lines[no - 1] = txt
        lines = [l for i, l in enumerate(lines, 1) if i not in drop]
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        print(f"applied {len(repl)} 行，删除 {len(drop)} 行")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
