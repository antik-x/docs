#!/usr/bin/env python3
"""verify_mdx.py — 单篇深查：verify_structure.check_pair + MDX 编译安全检查。

用法：python3 verify_mdx.py <源.mdx> <译文.mdx>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_structure import check_pair, split_fences, frontmatter  # noqa: E402


def mdx_safety(dst_text):
    issues = []
    fenced = set()
    in_fence = False
    closer = None
    for i, ln in enumerate(dst_text.split("\n"), 1):
        m = re.match(r"^\s*(`{3,}|~{3,})", ln)
        if m:
            tick = m.group(1)[0]
            if not in_fence:
                in_fence, closer = True, tick
                fenced.add(i)
            elif tick == closer:
                in_fence = False
                fenced.add(i)
        elif in_fence:
            fenced.add(i)
    lines = [ln for i, ln in enumerate(dst_text.split("\n"), 1)
             if i not in fenced]
    nb = "\n".join(lines)
    # $$...$$ 数学块内的花括号合法
    nb = re.sub(r"\$\$.*?\$\$", " ", nb, flags=re.S)
    _, nb = frontmatter(nb)
    # 多行 JSX 标签（<Card\n ...>）先移除，再查裸 <
    nb = re.sub(r"<[A-Za-z/][^>]*>", "", nb, flags=re.S)
    nb = re.sub(r"`[^`\n]+`", "", nb)
    nb = re.sub(r"\{[^{}]*\}", "", nb)  # 平衡花括号（Map/JS 字面量等合法场景）
    bare = nb.count("{")
    lt = len(re.findall(r"<[a-zA-Z/]", nb))
    if bare:
        issues.append(f"裸 {{ x{bare}（MDX 编译风险）")
    if lt:
        issues.append(f"裸 < x{lt}（MDX 编译风险）")
    return issues


def main():
    src, dst = sys.argv[1], sys.argv[2]
    if not os.path.exists(dst):
        print(f"FAIL {dst}: 不存在")
        return 1
    issues = check_pair(src, dst, dst)
    dst_text = open(dst, encoding="utf-8").read()
    issues += mdx_safety(dst_text)
    if issues:
        print(f"FAIL {dst}")
        for it in issues:
            print("  -", it)
        return 1
    print(f"OK {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
