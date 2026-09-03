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
    _, fences = split_fences(dst_text)
    body = dst_text
    for i, f in enumerate(fences):
        body = body.replace(f, f"\x00F{i}\x00")
    # $$...$$ 数学块内的花括号合法
    body = re.sub(r"\$\$.*?\$\$", " ", body, flags=re.S)
    nb, _ = frontmatter(body)
    nb = re.sub(r"<[A-Za-z/][^>\n]*>", "", nb)
    nb = re.sub(r"`[^`\n]+`", "", nb)
    nb = re.sub(r"\{[^{}]*\}", "", nb)  # Map/JS 对象字面量已在 JSX 之外的合法场景
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
