#!/usr/bin/env python3
"""build_nav.py — 从上游 meta.json + state/nav-zh.json 生成 Mintlify docs.json 的 navigation。

用法：python3 build_nav.py          # 只更新 docs.json 的 navigation 键
      python3 build_nav.py --audit  # 只打印缺失译文清单，不写文件
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(SKILL, "project.json"), encoding="utf-8"))
SRC = os.path.join(CFG["source_cache"], CFG["upstream"]["docs_dir"])
DOCS_JSON = os.path.normpath(os.path.join(SKILL, CFG["site_root"], CFG["nav_file"]))
NAV_ZH = os.path.join(SKILL, CFG.get("nav_translations", "state/nav-zh.json"))

zh = json.load(open(NAV_ZH, encoding="utf-8")) if os.path.exists(NAV_ZH) else \
    {"groups": {}, "pages": {}}
missing = []


def group_zh(name):
    """组名翻译：优先目录名/英文标题查表。"""
    if name in zh["groups"]:
        return zh["groups"][name]
    missing.append(f"group:{name}")
    return name


def page_key(rel_noext):
    return f"{CFG['target_content_dir']}/{rel_noext}"


def page_title(rel_noext, fallback):
    if rel_noext in zh["pages"]:
        return zh["pages"][rel_noext]
    missing.append(f"page:{rel_noext}")
    return fallback


def read_meta(path):
    return json.load(open(path, encoding="utf-8"))


def meta_title_for(group_dir):
    mp = os.path.join(SRC, group_dir, "meta.json")
    if os.path.exists(mp):
        return read_meta(mp).get("title", group_dir)
    return group_dir


def convert_page(slug):
    """上游 page 字符串 → docs.json 页面对象。"""
    # 子目录页面（conversation-simulator → 其 index）
    rel_noext = slug
    cand = os.path.join(SRC, slug + ".mdx")
    if not os.path.exists(cand):
        idx = os.path.join(SRC, slug, "index.mdx")
        if os.path.exists(idx):
            rel_noext = slug + "/index"
    fallback = slug
    # 尝试从译文/源文 frontmatter 取 sidebar_label 作回退
    src_md = os.path.join(SRC, rel_noext + ".mdx")
    if os.path.exists(src_md):
        head = open(src_md, encoding="utf-8").read(600)
        m = re.search(r"sidebar_label:\s*(.+)", head)
        if not m:
            m = re.search(r"title:\s*(.+)", head)
        if m:
            fallback = m.group(1).strip()
    key = page_key(rel_noext)
    title = page_title(rel_noext, fallback)
    return {"page": key, "title": title}


def walk(entries, group_dir=""):
    """meta.json 的 pages 列表 → docs.json pages 数组。"""
    out = []
    for e in entries:
        if e.startswith("---") and e.endswith("---"):
            m = re.match(r"---\[?([A-Za-z]*)\]?(.*)---", e)
            icon_src, title = m.group(1), m.group(2).strip()
            if not title:  # ---Title--- 无图标形式
                title = m.group(1)
                icon_src = ""
            g = {"group": group_zh(title), "pages": []}
            if icon_src:
                g["icon"] = re.sub(r"(?<!^)(?=[A-Z])", "-", icon_src).lower()
            out.append(g)
        elif e.startswith("(") and e.endswith(")"):
            sub = os.path.join(group_dir, e) if group_dir else e
            mp = os.path.join(SRC, sub, "meta.json")
            entries2 = read_meta(mp).get("pages", []) if os.path.exists(mp) else []
            g = {"group": group_zh(e), "pages": walk(entries2, sub)}
            mt = read_meta(mp) if os.path.exists(mp) else {}
            icon = mt.get("icon") or mt.get("defaultOpen")
            if mt.get("icon"):
                g["icon"] = re.sub(r"(?<!^)(?=[A-Z])", "-", mt["icon"]).lower()
            out.append(g)
        elif "/" in e and os.path.isdir(os.path.join(SRC, group_dir, e) if group_dir
                                        else os.path.join(SRC, e)):
            sub = os.path.join(group_dir, e) if group_dir else e
            mp = os.path.join(SRC, sub, "meta.json")
            entries2 = read_meta(mp).get("pages", []) if os.path.exists(mp) else []
            g = {"group": group_zh(meta_title_for(sub)), "pages": walk(entries2, sub)}
            out.append(g)
        else:
            slug = os.path.join(group_dir, e) if group_dir else e
            out.append(convert_page(slug))
    return out


def main():
    root_meta = read_meta(os.path.join(SRC, "meta.json"))
    nav = {"navigation": {"pages": walk(root_meta.get("pages", []))}}
    if "--audit" in sys.argv:
        if missing:
            print("缺失译文：")
            for m in missing:
                print("  -", m)
        else:
            print("导航译文齐全")
        print(f"共 {len(missing)} 条缺失" if missing else "")
        return
    doc = json.load(open(DOCS_JSON, encoding="utf-8"))
    doc["navigation"] = nav["navigation"]
    with open(DOCS_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"docs.json 已更新：{len(json.dumps(nav))} 字节；缺翻译 {len(missing)} 条")
    for m in missing[:20]:
        print("  -", m)


if __name__ == "__main__":
    main()
