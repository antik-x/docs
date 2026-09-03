#!/usr/bin/env python3
"""Shared Fumadocs→Mintlify normalization facts for convert/verify scripts.

Single source of truth for:
  - DEFAULT_MODELS (docs/lib/defaults.ts)
  - ASSETS resolver (docs/src/assets.ts → literal S3 URLs)
  - <Term py/ts> classification
  - component mapping source→target and expected-count normalization
  - callout directive mapping
"""
import os
import re

# docs/lib/defaults.ts 的 DEFAULT_MODELS（同步时人工核对一次）
DEFAULT_MODELS = {
    "openai": "gpt-5.4",
    "anthropic": "claude-opus-5",
    "gemini": "gemini-3.6-flash",
    "openrouter": "openai/gpt-5.4",
}

# 纯动画/装饰组件：转换时删除，译文中不得出现
DECORATIVE = {
    "VibeCodingLoop",
    "AgentTraceTerminal",
    "TraceLoopConnector",
    "ClaudeCodeTerminal",
    "RepoContributors",
}

# lucide-react 图标（行内装饰，删除；出现在 Card icon 属性时转 kebab-case 字符串）
LUCIDE = {
    "Bot", "Cloud", "Database", "FileSearch", "FlaskConical", "Gauge",
    "GitMerge", "MessagesSquare", "Plug", "Rocket", "Route", "ShieldCheck",
    "Sparkles", "Workflow", "Terminal", "TriangleAlert", "SendToBack",
    "ArrowDownWideNarrow", "MessageSquareText", "PackageCheck",
}

# ::: 指令 → Mintlify 组件
CALLOUT_MAP = {
    "tip": "Tip",
    "info": "Info",
    "note": "Note",
    "warning": "Warning",
    "caution": "Warning",
    "danger": "Danger",
}

# MetricTagsDisplayer pill 顺序与译名（props 为 true 时按此顺序输出）
METRIC_TAG_ORDER = [
    ("community", "社区维护"),
    ("usesLLMs", "LLM-as-a-judge"),   # 默认 true
    ("custom", "自定义"),
    ("singleTurn", "单轮"),
    ("multiTurn", "多轮"),
    ("trajectory", "轨迹"),
    ("referenceless", "无参考"),
    ("referenceBased", "有参考"),
    ("rag", "RAG"),
    ("agent", "智能体"),
    ("chatbot", "聊天机器人"),
    ("safety", "安全"),
    ("multimodal", "多模态"),          # 默认 true，usesLLMs=false 时强制关闭
]

_ASSETS_CACHE = None


def assets_file(upstream_root):
    return os.path.join(upstream_root, "docs", "src", "assets.ts")


def load_assets(upstream_root):
    """解析 docs/src/assets.ts，返回 {key: url}。模板字符串用 BUCKETS 展开。"""
    global _ASSETS_CACHE
    if _ASSETS_CACHE is not None:
        return _ASSETS_CACHE
    path = assets_file(upstream_root)
    buckets = {}
    assets = {}
    if os.path.exists(path):
        txt = open(path, encoding="utf-8").read()
        m = re.search(r"const BUCKETS = \{(.*?)\};", txt, re.S)
        if m:
            for k, v in re.findall(r'(\w+):\s*"([^"]+)"', m.group(1)):
                buckets[k] = v
        m = re.search(r"export const ASSETS = \{(.*?)\n\};", txt, re.S)
        if m:
            for k, v in re.findall(r'(\w+):\s*`(.*?)`', m.group(1)):
                url = re.sub(r"\$\{BUCKETS\.(\w+)\}",
                             lambda mm: buckets.get(mm.group(1), ""), v)
                assets[k] = url
    _ASSETS_CACHE = assets
    return assets


def camel(s):
    return re.sub(r"_([a-zA-Z])", lambda m: m.group(1).upper(), s)


def term_class(py, ts):
    """<Term py="X" ts="Y"/> → 'A' 机械驼峰 | 'B' npx 前缀 | 'C' 其余（需双呈现）。"""
    if ts == camel(py):
        return "A"
    if ts == "npx " + py:
        return "B"
    return "C"


TERM_RE = re.compile(
    r'<Term\s+py="([^"]+)"\s+ts="([^"]+)"\s*/>', re.S)


def term_replacement(py, ts):
    c = term_class(py, ts)
    if c in ("A", "B"):
        return "`%s`" % py
    return "`%s`（TypeScript 中为 `%s`）" % (py, ts)


def expected_term_spans(src_text):
    """Term 转换后目标侧应新增的行内代码段数量。"""
    n = 0
    for m in TERM_RE.finditer(strip_fences(src_text)[0]):
        n += 1 if term_class(m.group(1), m.group(2)) in ("A", "B") else 2
    return n


def split_fences(text):
    """返回 (无围栏文本, [围栏内容逐字节列表])。与 verify_structure 同逻辑。"""
    fence_re = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
    out, fences, in_fence, closer = [], [], False, None
    for line in text.split("\n"):
        m = fence_re.match(line)
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


def strip_fences(text):
    return split_fences(text)[0]


_CALLUT_OPEN_RE = re.compile(r"^(:::+)([a-z]+)(?:\[([^\]]*)\])?\s*$")


FENCE_LINE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


def protect_fences(text):
    """围栏内容替换为单行占位符。返回 (占位文本, {token: 原内容})。

    norm 与转换器共用，保证「期望」与「实际」在同样的文本形态上判定。
    """
    out, store, in_fence, closer, idx = [], {}, False, None, 0
    token = None
    for line in text.split("\n"):
        m = FENCE_LINE_RE.match(line)
        if not in_fence and m:
            in_fence, closer = True, m.group(2)[0] * len(m.group(2))
            idx += 1
            token = f"\x00FENCE{idx}\x00"
            store[token] = [line]
            out.append(token)
            continue
        if in_fence:
            if m and m.group(2)[0] == closer[0] and len(m.group(2)) >= len(closer):
                in_fence = False
                store[token].append(line)
            else:
                store[token].append(line)
            continue
        out.append(line)
    return "\n".join(out), {t: "\n".join(v) for t, v in store.items()}


def restore_fences(text, store):
    for token, content in store.items():
        text = text.replace(token, content)
    return text


FAQ_ARRAY_RE = re.compile(r"<FAQs\s+qas=\{\[(.*?)\]\}\s*/?>", re.S)


def normalized_components(src_text):
    """源文（Fumadocs）→ 期望的目标侧（Mintlify）组件计数。

    返回 {组件名: 数量}。FAQ 答案内嵌的 Switch/Case 会被 jsx_to_md 压成
    「**X**：」标签，不计入 Tabs/Tab 期望。
    """
    body, _ = protect_fences(src_text)  # 与转换器同形态（围栏→单行占位符）
    exp = {}
    add = lambda k, n=1: exp.__setitem__(k, exp.get(k, 0) + n)
    n_faq = len(FAQ_ARRAY_RE.findall(body))
    body_no_faq = FAQ_ARRAY_RE.sub(" ", body)
    add("Tabs", len(re.findall(r"<Switch\b", body_no_faq)))
    add("Tabs", len(re.findall(r"<Tabs\b", body_no_faq)))
    add("Tab", len(re.findall(r"<Case\b", body_no_faq)))
    add("Tab", len(re.findall(r"<Tab\b", body_no_faq)))
    add("CardGroup", len(re.findall(r"<Cards\b", body)))
    add("Card", len(re.findall(r"<Card\b", body)))
    add("Steps", len(re.findall(r"<Steps\b", body)))
    add("Step", len(re.findall(r"<Step\b", body)))
    if n_faq:
        add("AccordionGroup", n_faq)
        add("Accordion", body.count("question:"))
    for m in body.split("\n"):
        cm = _CALLUT_OPEN_RE.match(m.strip())
        if cm:
            add(CALLOUT_MAP[cm.group(2)], 1)
    add("Note", len(re.findall(r"<NotImplemented\b", body)))
    # 块级 <Only id="typescript"> → <Info>（与转换器同口径：strip 后判断）
    for m in re.finditer(r'<Only\s+id="typescript"\s*>(.*?)</Only>', body, re.S):
        if "\n\n" in m.group(1).strip():
            add("Info", 1)
    return exp


def left_over_markers(dst_text):
    """译文中不得残留的源格式标记（转换不完整即 FAIL）。"""
    body = strip_fences(dst_text)
    pats = [
        (r"<Switch\b", "<Switch 未转换"),
        (r"<Case\b", "<Case 未转换"),
        (r'<Tab\s+value=', "Tab value= 未转 title"),
        (r"<Term\b", "<Term 未转换"),
        (r"qas=\{\[", "FAQs 未转换"),
        (r"<FAQs\b", "<FAQs 未转换"),
        (r"^::+[a-z]", "::: 指令未转换"),
        (r"ASSETS\.", "ASSETS 未解析"),
        (r"^import\s", "import 未删除"),
        (r"<Equation\b", "<Equation 未转换"),
        (r"<ImageDisplayer\b", "<ImageDisplayer 未转换"),
        (r"<VideoDisplayer\b", "<VideoDisplayer 未转换"),
        (r"<DefaultLLMModel\b", "<DefaultLLMModel 未转换"),
        (r"<MetricTagsDisplayer\b", "<MetricTagsDisplayer 未转换"),
        (r"<NotImplemented\b", "<NotImplemented 未转换"),
        (r"<Only\b", "<Only 未转换"),
        (r"\{\" \"\}", 'JSX 空串 {" "} 残留'),
    ]
    for name in DECORATIVE:
        pats.append((r"<%s\b" % name, "装饰组件 %s 应删除" % name))
    found = []
    for pat, label in pats:
        if re.search(pat, body, re.M):
            found.append(label)
    return found


def metric_tags_line(props_str):
    """<MetricTagsDisplayer .../> 的 props 字符串 → 单行标签文本。"""
    props = dict(re.findall(r"(\w+)=\{(true|false)\}", props_str))
    uses_llms = props.get("usesLLMs", "true") == "true"
    tags = []
    for key, zh in METRIC_TAG_ORDER:
        if key == "usesLLMs":
            on = uses_llms
        elif key == "multimodal":
            on = (props.get("multimodal", "true") == "true") and uses_llms
        else:
            on = props.get(key, "false") == "true"
        if on:
            tags.append(zh)
    return "**标签**：" + " · ".join(tags)
