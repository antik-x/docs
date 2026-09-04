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

_zh_norm = {}


def _norm_key(k):
    return re.sub(r"\([^)]*\)/", "", k)


for _k, _v in zh["pages"].items():
    _n = _norm_key(_k)
    _cur = _zh_norm.get(_n)
    if _cur is None or ("(" not in _k and "(" in _cur[0]):
        _zh_norm[_n] = (_k, _v)

SITE_DOCS = os.path.normpath(os.path.join(SKILL, CFG["site_root"], CFG["target_content_dir"]))
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
    """上游 page 字符串 → docs.json 页面路径字符串（侧栏标题走 frontmatter sidebarTitle）。

    站点文件已剥离 () 路由组以对齐 URL，因此导航路径同样剥离；
    index 页引用目录路径（与站点 URL 一致）。
    """
    # 范围外页面（上游 meta 引用但站点不含）
    if slug.rstrip("/").endswith("getting-started-llm-arena"):
        return None
    rel_noext = re.sub(r"\([^)]*\)/", "", slug)
    if rel_noext not in _zh_norm:
        missing.append(f"page:{rel_noext}")
    if os.path.exists(os.path.join(SITE_DOCS, rel_noext + ".mdx")):
        return page_key(rel_noext)
    if os.path.exists(os.path.join(SITE_DOCS, rel_noext, "index.mdx")):
        return page_key(rel_noext + "/index")
    return page_key(rel_noext)


def walk(entries, group_dir=""):
    """meta.json 的 pages 列表 → docs.json pages 数组。

    Fumadocs 的 `---[Icon]Title---` 分隔符作用于其后直至下一个分隔符的页面，
    因此页面要挂进当前分隔符组的 pages 里，而不是作为兄弟项。
    """
    out = []
    current = None  # 当前分隔符组（dict），页面挂到它的 pages 下

    def emit(item):
        if current is not None:
            current["pages"].append(item)
        else:
            out.append(item)

    for e in entries:
        if e.startswith("../"):  # 子目录 meta 引用的外部页面（可能带路由组）
            e_clean = re.sub(r"^(\.\./)+", "", e)
            out.extend(walk([e_clean], group_dir=""))
            continue
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
            current = g
        elif e.startswith("(") and e.endswith(")"):
            sub = os.path.join(group_dir, e) if group_dir else e
            mp = os.path.join(SRC, sub, "meta.json")
            entries2 = read_meta(mp).get("pages", []) if os.path.exists(mp) else []
            g = {"group": group_zh(e), "pages": walk(entries2, sub)}
            mt = read_meta(mp) if os.path.exists(mp) else {}
            if mt.get("icon"):
                g["icon"] = re.sub(r"(?<!^)(?=[A-Z])", "-", mt["icon"]).lower()
            emit(g)
        elif os.path.isdir(os.path.join(SRC, group_dir, e) if group_dir
                           else os.path.join(SRC, e)):
            sub = os.path.join(group_dir, e) if group_dir else e
            mp = os.path.join(SRC, sub, "meta.json")
            entries2 = read_meta(mp).get("pages", []) if os.path.exists(mp) else []
            g = {"group": group_zh(meta_title_for(sub)), "pages": walk(entries2, sub)}
            emit(g)
        else:
            slug = os.path.join(group_dir, e) if group_dir else e
            page = convert_page(slug)
            if page is not None:
                emit(page)
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
