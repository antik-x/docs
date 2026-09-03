#!/usr/bin/env python3
"""convert_fumadocs.py — 把 confident-ai/deepeval 的 Fumadocs MDX 机械转换为
Mintlify MDX 骨架（英文原样保留，翻译在骨架上进行）。

用法：
  python3 convert_fumadocs.py docs/content/docs/a.mdx [更多.mdx ...]
  python3 convert_fumadocs.py --list <清单文件>     # 每行一个相对路径

路径映射：相对 docs/content/docs 的路径去掉括号路由组段后写入
<site_root>/<target_content_dir>/。代码围栏逐字节保护，不做任何转换。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fumadocs_norm as N  # noqa: E402

CFG = json.load(open(os.path.join(SKILL, "project.json"), encoding="utf-8"))
SRC_BASE = os.path.join(CFG["source_cache"], CFG["upstream"]["docs_dir"])
DST_BASE = os.path.normpath(
    os.path.join(SKILL, CFG["site_root"], CFG.get("target_content_dir", "docs")))

WARN = []


def warn(path, msg):
    WARN.append(f"{path}: {msg}")


# ---------------------------------------------------------------- 基础工具

def map_path(src_rel):
    segs = [s for s in src_rel.split("/")
            if not (s.startswith("(") and s.endswith(")"))]
    return os.path.join(DST_BASE, *segs)


def split_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            return text[3:end].strip("\n"), text[end + 4:].lstrip("\n")
    return "", text


def parse_frontmatter(fm_text):
    out = {}
    for line in fm_text.split("\n"):
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


protect_fences = N.protect_fences
restore_fences = N.restore_fences


def js_string(s):
    """JS 字符串字面量 → 实际文本。"""
    body = s.strip()
    if len(body) >= 2 and body[0] == body[-1] and body[0] in "\"'`":
        body = body[1:-1]
    body = body.replace('\\"', '"').replace("\\'", "'").replace("\\n", " ")
    body = body.replace("\\\\", "\\")
    return body


# ---------------------------------------------------------------- 行内转换

def convert_prose(text):
    """对一段（围栏外）文本做行内级转换：Term、code、图标、JSX 空串。"""
    text = N.TERM_RE.sub(
        lambda m: N.term_replacement(m.group(1), m.group(2)), text)
    text = re.sub(r'\{" "\}', " ", text)
    # 行内 lucide 图标（自闭合）
    for name in N.LUCIDE:
        text = re.sub(r"<%s\s*/>" % name, "", text)
        text = re.sub(r"<%s\s+[^<>]*?\s*/>" % name, "", text)
    # FAQ 答案等处的 <code>x</code> → `x`
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def pascal_to_kebab(s):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()


# ---------------------------------------------------------------- FAQs

def _split_objects(arr):
    """把 qas 数组文本按顶层对象切分：逐行剥掉字符串字面量后数括号深度。

    字符感知的字符级扫描会被反引号/撇号干扰，这里按行做，稳健得多。
    """
    objs, cur, depth = [], [], 0
    for line in arr.split("\n"):
        bare = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
        bare = re.sub(r"'(?:[^'\\]|\\.)*'", "''", bare)
        bare = re.sub(r"`(?:[^`\\]|\\.)*`", "``", bare)
        bare = re.sub(r"\{[^{}]*\}", "{}", bare)  # {" "} 之类平衡片段
        if cur or "{" in bare:
            cur.append(line)
            depth += bare.count("{") - bare.count("}")
            if depth <= 0:
                objs.append("\n".join(cur))
                cur, depth = [], 0
    return objs


def parse_qas(array_text, path):
    """解析 qas={[...]} 的数组文本 → [(question, answer_markdown)]。"""
    qas = []
    for obj in _split_objects(array_text):
        qm = re.search(r'question:\s*(["\'`])', obj)
        if not qm:
            warn(path, "FAQ 对象缺 question 字段，需手工转换")
            qas.append(("<待手工转换>", "<待手工转换>"))
            continue
        q_open = qm.end() - 1
        q_close = _skip_string(obj, q_open)
        q_plain = re.sub(r"`", "", js_string(obj[q_open:q_close + 1]))
        qas.append((q_plain.strip(), convert_answer(obj, path)))
    return qas


def _skip_string(s, i):
    """s[i] 是引号，返回结束引号的下标。"""
    q = s[i]
    j = i + 1
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == q:
            return j
        j += 1
    return len(s) - 1


def _match_delim(s, i, open_c, close_c):
    """s[i] 是 open_c，返回配对 close_c 下标（字符串感知）。"""
    depth, j, in_str, esc = 0, i, False, False
    while j < len(s):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = False
        else:
            if c in "\"'`":
                in_str = c
            elif c == open_c:
                depth += 1
            elif c == close_c:
                depth -= 1
                if depth == 0:
                    return j
        j += 1
    return len(s) - 1


def convert_answer(obj, path):
    m = re.search(r"\banswer:\s*", obj)
    if not m:
        warn(path, "FAQ 对象缺 answer 字段")
        return "<待手工转换>"
    i = m.end()
    while i < len(obj) and obj[i] in " \n":
        i += 1
    if i >= len(obj):
        return "<待手工转换>"
    if obj[i] == "(":
        # answer 的闭括号是对象里最后一个 ')'（对象以 `),` 或 `)` 收尾）
        j = obj.rfind(")")
        frag = obj[i + 1:j]
        frag = re.sub(r"^\s*<>\s*\n?", "", frag)
        frag = re.sub(r"\n?\s*</>\s*$", "", frag)
        return jsx_to_md(frag, path)
    q = obj[i]
    j = obj.rfind(q)
    return convert_prose(js_string(obj[i:j + 1])).strip()


def jsx_to_md(inner, path="FAQ"):
    # Switch/Case 嵌在答案里时先改成 Tabs 标签，再由扫描器压成「**X**：」标签
    inner = convert_tabs(inner)
    # 先做正则可覆盖的格式标签，再交给扫描器处理 code/Term/a/{" "}
    inner = re.sub(r"<(?:strong|b)>(.*?)</(?:strong|b)>", r"**\1**", inner, flags=re.S)
    inner = re.sub(r"<(?:em|i)>(.*?)</(?:em|i)>", r"*\1*", inner, flags=re.S)
    inner = re.sub(r"</?>", "", inner)
    inner = re.sub(r"</?(?:p|span|div)\b[^>]*>", "", inner)
    out, i, n = [], 0, len(inner)
    buf = ""

    def flush():
        nonlocal buf
        t = re.sub(r"\s+", " ", buf).strip()
        if t:
            out.append(t)
        buf = ""

    while i < n:
        if inner.startswith("<code>", i):
            flush()
            e = inner.find("</code>", i)
            if e < 0:
                warn(path, "answer 内 code 未闭合")
                buf += inner[i:]
                break
            out.append("`" + inner[i + 6:e] + "`")
            i = e + 7
        elif inner.startswith("<Term", i):
            flush()
            m = N.TERM_RE.match(inner, i)
            if not m:
                m = re.match(r'<Term\s[^>]*?/>', inner[i:], re.S)
                if not m:
                    warn(path, "answer 内 Term 解析失败，保留原文人工检查")
                    buf += "<Term…>"
                    e = inner.find("/>", i)
                    i = (e + 2) if e >= 0 else n
                    continue
                out.append("<Term…人工检查/>")
                i += m.end()
                continue
            mm = N.TERM_RE.search(m.group(0))
            out.append(N.term_replacement(mm.group(1), mm.group(2)))
            i = m.end()
        elif inner.startswith("<a", i) and inner[i:i+3] in ("<a ", "<a\n", "<a>"):
            flush()
            gt = inner.find(">", i)
            e = inner.find("</a>", i)
            if gt < 0 or e < 0:
                warn(path, "answer 内 a 标签异常")
                break
            open_tag = inner[i:gt + 1]
            hm = re.search(r'href="([^"]+)"', open_tag)
            label = re.sub(r"<code>(.*?)</code>", r"`\1`", inner[gt + 1:e], flags=re.S)
            if hm:
                out.append("[%s](%s)" % (
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", label)).strip(),
                    hm.group(1)))
            else:
                warn(path, "answer 内 a 标签缺 href")
                out.append(re.sub(r"<[^>]+>", "", label))
            i = e + 4
        elif inner.startswith("<Tab", i):
            flush()
            tm = re.match(r'<Tab\s+title="([^"]*)"\s*>', inner[i:])
            if tm:
                out.append("**%s**：" % tm.group(1))
                i += tm.end()
            else:
                e = inner.find(">", i)
                i = e + 1
        elif inner.startswith("</Tab", i) or inner.startswith("<Tabs", i) \
                or inner.startswith("</Tabs"):
            e = inner.find(">", i)
            if e < 0:
                break
            i = e + 1
        elif inner.startswith('{" "}', i):
            buf += " "
            i += 5
        elif inner[i] == "<":
            # 未知标签：报警并剥掉
            e = inner.find(">", i)
            if e < 0:
                break
            warn(path, f"answer 内未知标签 {inner[i:e+1][:40]}，请人工检查")
            i = e + 1
        else:
            buf += inner[i]
            i += 1
    flush()
    text = " ".join(out)
    return re.sub(r"\s+", " ", text).strip()


def convert_faqs(text, path):
    pat = re.compile(r"<FAQs\s+qas=\{\[(.*?)\]\}\s*/?>", re.S)
    m = pat.search(text)
    if not m:
        return text

    def repl(mm):
        qas = parse_qas(mm.group(1), path)
        blocks = ["<AccordionGroup>"]
        for q, a in qas:
            blocks.append(f'<Accordion title="{q}">')
            blocks.append(a)
            blocks.append("</Accordion>")
        blocks.append("</AccordionGroup>")
        return "\n".join(blocks)

    return pat.sub(repl, text)


# ---------------------------------------------------------------- 块级转换

def convert_callouts(text):
    out, stack = [], []
    for line in text.split("\n"):
        s = line.strip()
        m = re.match(r"^(:::+)([a-z]+)(?:\[([^\]]*)\])?\s*$", s)
        if m:
            comp = N.CALLOUT_MAP[m.group(2)]
            stack.append((len(m.group(1)), comp))
            out.append(f"<{comp}>")
            if m.group(3):
                out.append("")
                out.append(f"**{m.group(3).strip()}**")
                out.append("")
            continue
        if re.match(r"^:::+$", s):
            comp = stack.pop()[1] if stack else "Note"
            out.append(f"</{comp}>")
            continue
        out.append(line)
    if stack:
        warn("callouts", "存在未闭合的 ::: 指令")
    return "\n".join(out)


def convert_tabs(text):
    """单遍扫描，栈式处理嵌套 Tabs：
    - <Tabs items={[...]}> → <Tabs> 并把 titles 压栈
    - <Tab value="X"> → <Tab title="栈顶 titles[idx] 或 X">
    - <Switch>/<Case> 同步替换
    """
    stack = []
    token = re.compile(
        r'<Tabs\s+items=\{\[(.*?)\]\}\s*>|<Tabs>|</Tabs>|<Tab\s+value="([^"]*)"\s*>'
        r'|<Switch\s*>|</Switch>|<Case\s+id="python"\s*>|<Case\s+id="typescript"\s*>|</Case>'
    )

    def repl(m):
        if m.group(1) is not None:
            stack.append({"titles": re.findall(r'"([^"]*)"', m.group(1)), "idx": 0})
            return "<Tabs>"
        if m.group(0) == "<Tabs>":
            stack.append(None)
            return "<Tabs>"
        if m.group(0) == "</Tabs>":
            if stack:
                stack.pop()
            return "</Tabs>"
        if m.group(2) is not None:
            top = stack[-1] if stack else None
            if top:
                title = top["titles"][top["idx"]] \
                    if top["idx"] < len(top["titles"]) else m.group(2)
                top["idx"] += 1
            else:
                title = m.group(2)
            return f'<Tab title="{title}">'
        if m.group(0) == "<Switch>":
            stack.append(None)
            return "<Tabs>"
        if m.group(0) == "</Switch>":
            if stack:
                stack.pop()
            return "</Tabs>"
        if m.group(0).startswith('<Case id="python"'):
            return '<Tab title="Python">'
        if m.group(0).startswith('<Case id="typescript"'):
            return '<Tab title="TypeScript">'
        return "</Tab>"

    return token.sub(repl, text)


def convert_cards(text):
    text = re.sub(r"<Cards\s*>", '<CardGroup cols={2}>', text)
    text = re.sub(r"</Cards>", "</CardGroup>", text)
    text = re.sub(r'icon=\{<(\w+)\s*/>\}',
                  lambda m: 'icon="%s"' % pascal_to_kebab(m.group(1)), text)
    # 本地图片图标（/icons/...）：站点不带第三方图标资产，整块剥离
    text = re.sub(r"icon=\{\s*\n?\s*<img\b.*?/\>\s*\n?\s*\}\s*\n?", "", text,
                  flags=re.S)
    return text


def convert_single_tags(text, path):
    assets = N.load_assets(CFG["source_cache"])

    # <Equation formula="F" /> → $$F$$
    def eq_repl(mm):
        return "$$\n%s\n$$" % mm.group(1).strip()

    text = re.sub(r'<Equation\s+formula="(.*?)"\s*/>', eq_repl, text, flags=re.S)

    # <ImageDisplayer src={ASSETS.x} alt? caption? /> 
    def img_repl(mm):
        props = mm.group(0)
        key = re.search(r"ASSETS\.(\w+)", props)
        url = assets.get(key.group(1)) if key else None
        if not url:
            warn(path, f"ASSETS.{key.group(1) if key else '?'} 解析失败")
            url = "<URL 待补>"
        alt = re.search(r'alt="([^"]*)"', props)
        cap = re.search(r"caption=\{?\"([^\"]*)\"\}?", props)
        lines = [f"![{alt.group(1) if alt else key.group(1)}]({url})"]
        if cap:
            lines += ["", f"*{cap.group(1)}*"]
        return "\n".join(lines)

    text = re.sub(r"<ImageDisplayer[^>]*?/>", img_repl, text, flags=re.S)

    # <VideoDisplayer ... />
    def vid_repl(mm):
        props = mm.group(0)
        key = re.search(r"ASSETS\.(\w+)", props)
        url = assets.get(key.group(1)) if key else None
        if not url:
            warn(path, f"ASSETS.{key.group(1) if key else '?'} 解析失败")
            url = "<URL 待补>"
        desc = re.search(r'description="([^"]*)"', props)
        cta = re.search(r'ctaText="([^"]*)"', props)
        cta_url = re.search(r'confidentUrl="([^"]*)"', props)
        cap = desc.group(1) if desc else ""
        if cta:
            link = f"（[{cta.group(1)}]({cta_url.group(1)})）" if cta_url else \
                f"（{cta.group(1)}）"
            cap += link
        return ("<figure>\n"
                f'  <video controls src="{url}"></video>\n'
                f"  <figcaption>{cap}</figcaption>\n"
                "</figure>")

    text = re.sub(r"<VideoDisplayer[^>]*?/>", vid_repl, text, flags=re.S)

    # <DefaultLLMModel provider? /> → 代码段
    def llm_repl(mm):
        provider = mm.group(1) or "openai"
        val = N.DEFAULT_MODELS.get(provider)
        if not val:
            warn(path, f"DefaultLLMModel provider={provider} 未知")
            val = "<模型待查>"
        return f"`{val}`"

    text = re.sub(r'<DefaultLLMModel\s*(?:provider="(\w+)")?\s*/>', llm_repl, text)

    # <MetricTagsDisplayer ... />
    def tags_repl(mm):
        return N.metric_tags_line(mm.group(0))

    text = re.sub(r"<MetricTagsDisplayer[^>]*?/>", tags_repl, text, flags=re.S)

    # <NotImplemented id feature>children</NotImplemented>
    def ni_repl(mm):
        feature = mm.group(2)
        children = (mm.group(3) or "").strip()
        body = (f"`{feature}` 尚未在 TypeScript SDK 中提供，"
                "目前可在 Python 中使用，本节内容以 Python 为准。")
        if children:
            body += "\n\n" + convert_prose(children)
        return f"<Note>\n**501 · TypeScript 暂未实现**\n\n{body}\n</Note>"

    text = re.sub(
        r'<NotImplemented\s+id="(\w+)"\s+feature="([^"]+)"\s*>(.*?)</NotImplemented>',
        ni_repl, text, flags=re.S)
    text = re.sub(
        r'<NotImplemented\s+id="(\w+)"\s+feature="([^"]+)"\s*/>', ni_repl, text,
        flags=re.S)

    # 裸 JSX 属性里的 ASSETS 常量（如 <video><source src={ASSETS.x}>）
    def attr_url_repl(mm):
        url = assets.get(mm.group(1))
        if not url:
            warn(path, f"ASSETS.{mm.group(1)} 解析失败")
            url = "<URL 待补>"
        return f'="{url}"'

    text = re.sub(r'=\{ASSETS\.(\w+)\}', attr_url_repl, text)

    # 装饰组件删除
    for name in N.DECORATIVE:
        text = re.sub(r"<%s\s*[^<>]*?/>\n?" % name, "", text)
        text = re.sub(r"<%s\s*[^<>]*?>.*?</%s>\n?" % (name, name), "", text,
                      flags=re.S)
    return text


def convert_only(text):
    def py_repl(mm):
        return mm.group(1)

    def ts_repl(mm):
        inner = mm.group(1).strip()
        if "\n\n" in inner:
            return "<Info>\n**TypeScript**\n\n%s\n</Info>" % inner
        return "（TypeScript：%s）" % inner.strip()

    text = re.sub(r'<Only\s+id="python"\s*>(.*?)</Only>', py_repl, text, flags=re.S)
    text = re.sub(r'<Only\s+id="typescript"\s*>(.*?)</Only>', ts_repl, text,
                  flags=re.S)
    return text


def strip_imports(text):
    text = re.sub(r'^import\s+\{[^}]*\}\s+from\s+["\'][^"\']+["\'];?\s*$',
                  "", text, flags=re.M | re.S)
    text = re.sub(r'^import\s+\w+\s+from\s+["\'][^"\']+["\'];?\s*$',
                  "", text, flags=re.M)
    text = re.sub(r'^import\s+["\'][^"\']+["\'];?\s*$', "", text, flags=re.M)
    return text


def strip_icons_multiline(text):
    for name in N.LUCIDE:
        text = re.sub(r"<%s\s*/>" % name, "", text)
        text = re.sub(r"<%s\s[^<>]*?>[^<>]*?</%s>" % (name, name), "", text,
                      flags=re.S)
    return text


# ---------------------------------------------------------------- include 内联

INCLUDE_RE = re.compile(r"<include[^>]*>([^<]+)</include>")


def _slugify(heading_text):
    s = re.sub(r"[`*_]", "", heading_text).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s]+", "-", s)


def _snippet_section(snip_text, anchor):
    """按 #anchor 截取小节：<section id="anchor"> ... </section> 优先，
    其次标题匹配。"""
    m = re.search(
        r'<section\s+id="%s">\s*(.*?)</section>' % re.escape(anchor),
        snip_text, re.S)
    if m:
        return m.group(1).strip()
    lines = snip_text.split("\n")
    start, level = None, None
    for i, ln in enumerate(lines):
        hm = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if hm and _slugify(hm.group(2)) == anchor:
            start, level = i, len(hm.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        hm = re.match(r"^(#{1,6})\s+", lines[i])
        if hm and len(hm.group(1)) <= level:
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def expand_includes(text, cur_dir, path, depth=0):
    """<include cwd>x.mdx#anchor</include> → 片段内容（递归转换管线在后续步骤统一进行）。

    片段路径解析顺序：包含文件所在目录 → docs/content/docs → docs/。
    """
    if depth > 4:
        warn(path, "include 嵌套过深，停止展开")
        return text
    roots = [cur_dir,
             SRC_BASE,
             os.path.join(CFG["source_cache"], "docs")]

    def repl(m):
        target = m.group(1).strip()
        frag_path, _, anchor = target.partition("#")
        for root in roots:
            cand = os.path.join(root, frag_path)
            if os.path.exists(cand):
                break
        else:
            warn(path, f"include 片段找不到：{target}")
            return m.group(0)
        snip = open(cand, encoding="utf-8").read()
        snip = expand_includes(snip, os.path.dirname(cand), frag_path, depth + 1)
        if anchor:
            sec = _snippet_section(snip, anchor)
            if sec is None:
                warn(path, f"include 锚点 #{anchor} 找不到：{target}")
                sec = snip
            snip = sec
        return "\n\n" + snip.strip() + "\n\n"

    return INCLUDE_RE.sub(repl, text)


# ---------------------------------------------------------------- 主流程

def convert_file(src_rel):
    src_path = os.path.join(SRC_BASE, src_rel)
    dst_path = map_path(src_rel)
    text = open(src_path, encoding="utf-8").read()
    fm_text, body = split_frontmatter(text)
    fm = parse_frontmatter(fm_text)

    body = expand_includes(
        body, os.path.dirname(src_path), src_rel)
    body, store = protect_fences(body)
    body = convert_faqs(body, src_rel)
    body = convert_single_tags(body, src_rel)
    body = convert_callouts(body)
    body = convert_tabs(body)
    body = convert_cards(body)
    body = convert_only(body)
    body = strip_imports(body)
    body = strip_icons_multiline(body)
    body = convert_prose(body)
    # 折叠必须在围栏恢复之前（否则会吃掉围栏内的空行）
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = restore_fences(body, store)
    body = body.strip("\n")

    # 新 frontmatter：title 原样（翻译时改），其余键丢弃
    lines = ["---", f"title: {fm.get('title', src_rel)}"]
    if fm.get("description"):
        lines.append(f"description: {fm['description']}")
    lines.append("---")

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n" + body + "\n")
    return dst_path


def main():
    args = sys.argv[1:]
    files = []
    if args and args[0] == "--list":
        files = [l.strip() for l in open(args[1], encoding="utf-8")
                 if l.strip()]
    else:
        files = args
    if not files:
        print("用法: convert_fumadocs.py <src.mdx> ... | --list <清单>")
        sys.exit(2)
    done = []
    for rel in files:
        rel = os.path.relpath(rel, SRC_BASE) if os.path.isabs(rel) else rel
        done.append(convert_file(rel))
        print("CONVERTED", done[-1])
    if WARN:
        print("\nWARNINGS:")
        for w in WARN:
            print("  -", w)
    print(f"\n{len(done)} 个文件已转换；{len(WARN)} 条警告（警告必须逐条消化）")


if __name__ == "__main__":
    main()
