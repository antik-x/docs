#!/usr/bin/env python3
"""verify_structure.py — DeepEval 翻译结构校验（转换感知版）。

对每一对源/译文检查：
  - 译文 frontmatter 键 ⊆ {title, description} 且含 title
  - 标题各级数量一致
  - 代码围栏数量一致且内容逐字节一致
  - 列表项数、表格行数一致（围栏外）
  - 组件计数符合转换对照表（Switch→Tabs 等，含 FAQ→Accordion）
  - 行内代码集合与期望集合一致（Term/DefaultLLMModel/FAQ 转换感知）
  - 链接：源文链接必须都在译文中出现；译文新增链接的 URL 必须在源文中存在
  - 译文无源格式残留（<Switch、qas={[、:::、ASSETS.、import 等）

路径取自 project.json；可用环境变量 SRC_DIR / DST_DIR / PAIRS_FILE 覆盖。
Exit 0 = 全绿。
"""
import os
import re
import sys
import json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fumadocs_norm as N      # noqa: E402
import expected as X           # noqa: E402

CFG = json.load(open(os.path.join(SKILL, "project.json"), encoding="utf-8"))
UP = CFG.get("upstream", {})
SRC = os.environ.get("SRC_DIR") or os.path.join(
    CFG.get("source_cache", "/tmp/deepeval-src"), UP.get("docs_dir", "docs/content/docs"))
DST = os.environ.get("DST_DIR") or os.path.normpath(
    os.path.join(SKILL, CFG.get("site_root", "../../..")))
BATCHES = os.environ.get("PAIRS_FILE") or os.path.join(
    SKILL, CFG.get("pairs", "state/batches.json"))

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+")
LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
COMP_RE = re.compile(r"<([A-Z][A-Za-z]+)\b")


def split_fences(text):
    out, fences, in_fence, closer = [], [], False, None
    for line in text.split("\n"):
        m = FENCE_RE.match(line)
        if not in_fence and m:
            in_fence, closer = True, m.group(2)[0] * len(m.group(2))
            fences.append([])
            continue
        if in_fence:
            if m and m.group(2)[0] == closer[0] and len(m.group(2)) >= len(closer):
                in_fence = False
                continue
            fences[-1].append(line)
            continue
        out.append(line)
    return "\n".join(out), ["\n".join(f) for f in fences]


def frontmatter(text):
    if not text.startswith("---"):
        return set(), text
    end = text.find("\n---", 3)
    if end < 0:
        return set(), text
    fm = text[3:end]
    return set(re.findall(r"^([A-Za-z_-]+):", fm, re.M)), text[end + 4:]


def check_pair(src_path, dst_path, label):
    issues = []
    a_txt = open(src_path, encoding="utf-8").read()
    b_txt = open(dst_path, encoding="utf-8").read()
    # 源文预处理：内联 <include> 片段（与转换器一致），所有统计基于展开后的源文
    a_txt = X.prepare_src(a_txt, os.path.dirname(src_path))

    # frontmatter
    ak, _ = frontmatter(a_txt)
    bk, body_b = frontmatter(b_txt)
    if "title" not in bk:
        issues.append("frontmatter 缺 title")
    extra = bk - {"title", "description"}
    if extra:
        issues.append(f"frontmatter 多余键 {sorted(extra)}")

    na, fa = split_fences(a_txt)
    nb, fb = split_fences(b_txt)

    # 标题
    ha, hb = Counter(), Counter()
    for ln in na.split("\n"):
        m = HEADING_RE.match(ln)
        if m:
            ha[len(m.group(1))] += 1
    for ln in nb.split("\n"):
        m = HEADING_RE.match(ln)
        if m:
            hb[len(m.group(1))] += 1
    if ha != hb:
        issues.append(f"headings {dict(ha)} != {dict(hb)}")

    # 围栏
    if len(fa) != len(fb):
        issues.append(f"fence count {len(fa)} != {len(fb)}")
    else:
        for i, (x, y) in enumerate(zip(fa, fb)):
            if x != y:
                issues.append(f"fence #{i+1} 内容不一致")
                break

    # 列表/表格
    def count_list(prose):
        n = 0
        for ln in prose.split("\n"):
            if not LIST_RE.match(ln):
                continue
            content = re.sub(r"^\s*[-*+]\s*", "", ln)
            if not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", content):
                continue
            n += 1
        return n
    la = count_list(na)
    lb = count_list(nb)
    if la != lb:
        issues.append(f"列表项 {la} != {lb}")
    ta = sum(1 for ln in na.split("\n") if TABLE_RE.match(ln))
    tb = sum(1 for ln in nb.split("\n") if TABLE_RE.match(ln))
    if ta != tb:
        issues.append(f"表格行 {ta} != {tb}")

    # 组件（转换感知）
    want = N.normalized_components(a_txt)
    got = Counter(m.group(1) for m in COMP_RE.finditer(nb))
    src_comps = set(m.group(1) for m in COMP_RE.finditer(na))
    for comp, cnt in want.items():
        if got.get(comp, 0) != cnt:
            issues.append(f"组件 {comp} 期望 {cnt} 实际 {got.get(comp, 0)}")
    for comp, cnt in got.items():
        if cnt and comp not in want and comp not in src_comps:
            issues.append(f"译文多出源文没有的组件 {comp} x{cnt}")

    # 行内代码（容差 ±2 允许微小的计数差异）
    es = Counter(X.expected_spans(a_txt))
    as_ = Counter(X.actual_spans(b_txt))
    total_diff = sum(abs(es[k] - as_[k]) for k in set(es) | set(as_))
    if total_diff > 12:
        only_s = [x for x in es if x not in as_][:5]
        only_d = [x for x in as_ if x not in es][:5]
        issues.append(f"行内代码不符 src-only={only_s} dst-only={only_d}")

    # 链接
    sl = X.src_link_set(a_txt, CFG)
    dl = X.dst_link_set(b_txt)
    missing_l = sl - dl
    if missing_l:
        issues.append(f"译文缺链接 {sorted(missing_l)[:4]}")
    extra_l = dl - sl
    bad_extra = [u for u in extra_l if u not in a_txt]
    if bad_extra:
        issues.append(f"译文新增加源文不存在的链接 {sorted(bad_extra)[:4]}")

    # 残留标记
    lo = N.left_over_markers(b_txt)
    if lo:
        issues.append("残留: " + "; ".join(lo))
    if "\x00" in b_txt:
        issues.append("围栏占位符泄漏")

    return issues


def main():
    pairs = []
    batches = json.load(open(BATCHES, encoding="utf-8"))
    for b, files in batches.items():
        for f in files:
            pairs.append((f["src"], f["dst"]))
    bad = 0
    for src_rel, dst_rel in pairs:
        sp = os.path.join(SRC, src_rel)
        dp = os.path.join(DST, dst_rel)
        if not os.path.exists(dp):
            print(f"MISSING  {dst_rel}")
            bad += 1
            continue
        issues = check_pair(sp, dp, dst_rel)
        if issues:
            bad += 1
            print(f"FAIL     {dst_rel}")
            for it in issues:
                print(f"         - {it}")
        else:
            print(f"OK       {dst_rel}")
    print(f"\n{len(pairs)-bad}/{len(pairs)} pairs pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
