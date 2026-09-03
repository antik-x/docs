#!/usr/bin/env python3
"""expected.py — 从源文推导译文应当具备的行内代码/组件/链接集合。

被 verify_structure.py / verify_mdx.py 共用；复用 convert_fumadocs 的
FAQ 解析，保证「期望」与「转换」同一逻辑。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fumadocs_norm as N          # noqa: E402
import convert_fumadocs as C       # noqa: E402

FAQ_RE = re.compile(r"<FAQs\s+qas=\{\[(.*?)\]\}\s*/?>", re.S)
SPAN_RE = re.compile(r"(`+)([^`\n]+?)\1")
CODE_TAG_RE = re.compile(r"<code>(.*?)</code>", re.S)


def prepare_src(src_text, src_dir=""):
    """源文预处理：<include> 片段内联（与转换器同一实现）。"""
    if src_dir and "<include" in src_text:
        return C.expand_includes(src_text, src_dir, "verify")
    return src_text


def expected_spans(src_text):
    """推导译文（骨架）应有的行内代码内容 multiset（排序列表）。输入须先经 prepare_src。"""
    body, _ = N.protect_fences(src_text)
    spans = []

    # 1) FAQ 块：问题中的反引号内容会被剥掉（title 纯文本），答案中的
    #    <code> 与 Term 经 convert_prose 转为行内代码
    faq_spans = []

    def faq_repl(m):
        for q, a in C.parse_qas(m.group(1), "expected"):
            faq_spans.extend(x[1] for x in SPAN_RE.findall(a))
        return " "

    body = FAQ_RE.sub(faq_repl, body)

    # 2) Term
    def term_repl(m):
        spans.append(m.group(1))
        if N.term_class(m.group(1), m.group(2)) == "C":
            spans.append(m.group(2))
        return " "

    body = N.TERM_RE.sub(term_repl, body)

    # 3) DefaultLLMModel
    def llm_repl(m):
        spans.append(N.DEFAULT_MODELS.get(m.group(1) or "openai", "?"))
        return " "

    body = re.sub(r'<DefaultLLMModel\s*(?:provider="(\w+)")?\s*/>', llm_repl, body)

    # 4) NotImplemented feature → `feature`
    body = re.sub(r'<NotImplemented\s+id="\w+"\s+feature="([^"]+)"\s*/?>',
                  lambda m: spans.append(m.group(1)) or " ", body)

    # 5) 散文中的 <code>x</code>（如 details/summary 里）→ `x`
    body = CODE_TAG_RE.sub(lambda m: spans.append(m.group(1)) or " ", body)

    # 6) 其余散文中的行内代码
    spans.extend(x[1] for x in SPAN_RE.findall(body))
    spans.extend(faq_spans)
    return sorted(spans)


def actual_spans(dst_text):
    body = N.strip_fences(dst_text)
    return sorted(x[1] for x in SPAN_RE.findall(body))


def src_link_set(src_text, cfg=None):
    body = N.strip_fences(src_text)
    links = set(re.findall(r"\]\(([^)\s]+)\)", body))
    links |= set(re.findall(r'href="([^"]+)"', body))
    # ASSETS 常量解析出的 URL 也是源文链接
    for key in set(re.findall(r"ASSETS\.(\w+)", body)):
        url = N.load_assets((cfg or {}).get("source_cache", "/tmp/deepeval-src")).get(key)
        if url:
            links.add(url)
    return links


def dst_link_set(dst_text):
    body = N.strip_fences(dst_text)
    links = set(re.findall(r"\]\(([^)\s]+)\)", body))
    links |= set(re.findall(r'href="([^"]+)"', body))
    links |= set(re.findall(r'\bsrc="([^"]+)"', body))
    return links
