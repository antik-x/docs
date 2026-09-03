#!/usr/bin/env python3
"""translate_overlay.py — 大页面的散文覆盖翻译辅助。

代码围栏逐字节保留；只抽取围栏外的散文行供翻译，再按行回填。

用法：
  python3 translate_overlay.py extract <file.mdx> [out.tsv]
      # 打印并写出 TSV：行号<TAB>原文（围栏外非空行）
  python3 translate_overlay.py apply <file.mdx> <tsv>
      # 用 TSV 中的译文替换对应行；文本为 \x00DROP\x00 时删除该行
  python3 translate_overlay.py autoapply <file.mdx> [pending.tsv] [memory.json]
      # 用翻译记忆自动替换完全相同的英文行；剩余行写 pending.tsv
  python3 translate_overlay.py learn <pending.tsv> <done.tsv> [memory.json]
      # 把 pending(英文) + done(译文) 按"行号相同"合并进翻译记忆
"""
import re
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
            old = lines[no - 1].strip()
            new = txt.strip()
            if old.startswith("<") and old.endswith(">") and not new.startswith("<"):
                print(f"警告：第 {no} 行把标签行 `{old}` 改成了文本，疑似行号错位！")
            lines[no - 1] = txt
        lines = [l for i, l in enumerate(lines, 1) if i not in drop]
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        print(f"applied {len(repl)} 行，删除 {len(drop)} 行")
    elif cmd == "autoapply":
        import json, os
        pending_path = sys.argv[3] if len(sys.argv) > 3 else path + ".pending.tsv"
        mem_path = sys.argv[4] if len(sys.argv) > 4 else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "state", "translation-memory.json")
        mem = json.load(open(mem_path, encoding="utf-8")) if os.path.exists(mem_path) else {}
        skip = prose_lines(text)
        cjk = re.compile(r"[\u4e00-\u9fff]")
        lines = text.split("\n")
        pending = []
        hit = 0
        for i, line in enumerate(lines, 1):
            if i in skip or not line.strip():
                continue
            if cjk.search(line):
                continue  # 已含中文：视为已翻译
            zh = mem.get(line.strip())
            if zh is not None:
                lines[i - 1] = zh
                hit += 1
            else:
                pending.append((i, line))
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        with open(pending_path, "w", encoding="utf-8") as f:
            for i, line in pending:
                f.write(f"{i}\t{line}\n")
        print(f"autoapplied {hit} 行（记忆命中）；待翻译 {len(pending)} 行 -> {pending_path}")
    elif cmd == "learn":
        import json, os
        pending_path, done_path = sys.argv[2], sys.argv[3]
        mem_path = sys.argv[4] if len(sys.argv) > 4 else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "state", "translation-memory.json")
        mem = json.load(open(mem_path, encoding="utf-8")) if os.path.exists(mem_path) else {}
        en = {}
        for ln in open(pending_path, encoding="utf-8"):
            no, _, txt = ln.rstrip("\n").partition("\t")
            en[int(no)] = txt
        added = 0
        for ln in open(done_path, encoding="utf-8"):
            if not ln.strip() or ln.startswith("#"):
                continue
            no, _, txt = ln.rstrip("\n").partition("\t")
            no = int(no)
            if no in en and txt.strip() and txt.strip() != "\\x00DROP\\x00" and txt != en[no]:
                en_txt = en[no].strip()
                zh_txt = txt.strip()
                # 毒化护栏：JSX 标签行只能映射回 JSX 标签行（<Note> -> 文本 是事故）
                if en_txt.startswith("<") and not zh_txt.startswith("<"):
                    continue
                mem[en_txt] = txt
                added += 1
        os.makedirs(os.path.dirname(mem_path), exist_ok=True)
        json.dump(mem, open(mem_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"learned {added} 条；记忆总量 {len(mem)}")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
