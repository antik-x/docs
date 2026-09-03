---
name: docs-translation
description: DeepEval 中文文档（非官方）翻译与上游同步技能：Fumadocs MDX 机械转换为 Mintlify 骨架、人工翻译、校验结构与术语一致性、同步上游更新、把流程复用到新的文档项目。凡涉及翻译本仓库文档、同步上游更新、比对译文一致性、维护术语表或初始化新翻译项目，一律使用本技能。Use whenever translating docs in this repo, syncing translations after upstream updates, verifying translation parity, or onboarding a new docs project.
---

# docs-translation：DeepEval 中文文档翻译与上游同步

## 工作原理

本技能**完全自包含**于站点仓库的 `.agents/skills/docs-translation/`（Mintlify 自动忽略该目录，不会发布）：

```
docs-translation/
├── SKILL.md            本文件：流程与红线
├── project.json        项目事实（上游仓库、路径、转换器、术语表位置等）
├── references/         rules.md 翻译规范+转换对照表；terminology.md 约束性术语表
├── scripts/
│   ├── fumadocs_norm.py      共享事实（组件映射、DEFAULT_MODELS、ASSETS、指标标签）
│   ├── convert_fumadocs.py   Fumadocs MDX → Mintlify MDX 骨架（机械转换，英文保留）
│   ├── build_nav.py          meta.json + nav-zh.json → docs.json navigation
│   ├── expected.py           从源文推导期望的行内代码/链接集合
│   ├── verify_structure.py   批量结构校验（转换感知）
│   └── verify_mdx.py         单篇深查 + MDX 编译安全
└── state/              batches.json 源↔译文配对；nav-zh.json 导航译文；sync-state.json 同步基线
```

**零侵入约束**：除译文内容（`docs/*.mdx`、`docs.json`、`index.mdx`）、技能目录自身与 `bootstrap_files`（docs.json/index.mdx/README.md 等站点引导，见 project.json）外，不修改仓库其他文件（AGENTS.md、LICENSE、favicon、logo、.mintignore 等一律不动）。每次会话动手前先读 `project.json`，不要凭记忆。所有命令在仓库根目录执行。

**站点定位（红线）**：本站是**非官方社区翻译**（zh-docs-deepeval.mintlifysite.com）。不引入 DeepEval 官方 logo/配色；非官方声明只出现在 index.mdx 与 README.md，不逐页标注；不自称官方。

| 配置字段 | 含义 |
|---|---|
| `upstream` | 上游仓库 `repo` / 分支 `branch` / 文档目录 `docs_dir`（`docs/content/docs`，Fumadocs） |
| `source_cache` | 上游仓库本地克隆（`/tmp` 会被清空，每次会话按步骤 0 重建） |
| `site_root` / `target_content_dir` / `nav_file` | 仓库根 / 译文目录 `docs/` / `docs.json` |
| `source_ext` → `target_ext` | `.mdx` → `.mdx`；路径映射＝去掉括号路由组段（URL 与 deepeval.com 一致） |
| `converter` | 机械转换脚本（先转换、后翻译） |
| `nav_translations` | `state/nav-zh.json`：组名+每页导航标题（译完一篇登记一篇） |
| `rules` / `terminology` | 翻译规范（含**转换对照表**）与约束性术语表（**动手前必读，双向约束**） |
| `pairs` / `sync_state` | 源↔译文配对清单 / 同步基线 |

要点速记（详见 rules / terminology）：代码围栏与行内代码逐字节保留；链接 URL 原样、链接文字翻译；`<Term>`/FAQ/Switch 等由转换器按对照表处理，译文中残留 `<Switch`、`qas={`、`:::`、`ASSETS.`、`import` 即 FAIL；术语严禁现场发明。

## 步骤 0：准备英文源（每次会话必做）

```bash
SRC=/tmp/deepeval-src     # project.json 的 source_cache
BR=main
REPO=https://github.com/confident-ai/deepeval
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" fetch origin "$BR" && git -C "$SRC" reset --hard "origin/$BR"
else
  git clone "$REPO" "$SRC"
fi
git -C "$SRC" rev-parse HEAD   # 与 sync-state 基线比对
```

**完整历史是硬要求**：A1 要对旧基线 commit 做 `git diff`。若 diff 因基线缺失报错，删掉缓存重新完整克隆（不要 `--depth 1`）。

## 工作流 A：同步上游更新

### A1. 找出变更

```bash
BASE=$(python3 -c "import json;print(json.load(open('.agents/skills/docs-translation/state/sync-state.json'))['last_synced_commit'])")
NEW=$(git -C /tmp/deepeval-src rev-parse origin/main)
git -C /tmp/deepeval-src diff --name-status "$BASE" "$NEW" -- docs/content/docs/ docs/snippets/ docs/src/assets.ts docs/lib/defaults.ts
```

- `M`（页面或被 include 的 snippets/assets/defaults 变了）→ A2
- `A` 新页面 → 工作流 B，登记 `pairs` 与 `nav-zh.json`
- `D` 删除 → 删译文并同步两处清单
- 改名 → 移动译文，同步两处清单
- 无变更则跑一次全量校验收尾

### A2. 逐页更新（最小改动原则）

1. 对 `M` 页面做基线 diff，只改译文中语义对应部分；**源文未动的段落译文一字不动**。被 include 的 snippets 变更会波及多个译文页，逐页最小更新。
2. 整页约三分之一以上重写时，放弃 A2 改按工作流 B 重转重译。
3. 转换规则变化（fumadocs_norm 的映射/常量更新）时，允许对受影响页面重跑转换器后重新翻译受影响片段。

### A3. 同步导航

组名/页面导航标题改 `state/nav-zh.json`，重跑 `python3 .agents/skills/docs-translation/scripts/build_nav.py` 再生成 `docs.json` 的 navigation。

## 工作流 B：翻译新页面（两步流水线）

1. 读 `rules` 与 `terminology`（每次都读，术语表可能已更新）。
2. **转换**：`python3 .agents/skills/docs-translation/scripts/convert_fumadocs.py <上游相对路径.mdx>`；输出的 WARN 必须逐条消化。
3. **翻译**：在骨架上把人类语言译成中文（frontmatter title、标题、散文、Tab/Accordion/Card 的 title/description、alt/figcaption、callout 标题；代码/URL/代码身份不动）。`beta: true` 页面顶部补 `<Note>` Beta 声明（对照表）。
4. 登记 `state/nav-zh.json`：`"pages": {"<去括号相对路径无扩展名>": "导航短标题"}`（取源文 sidebar_label 之意），重跑 build_nav.py。
5. 登记 `state/batches.json`（src=上游相对路径，dst=仓库内 `docs/...` 路径）。
6. 自检：`python3 .agents/skills/docs-translation/scripts/verify_mdx.py <源.mdx> <译.mdx>`；批次收尾跑 verify_structure.py。通读成稿去翻译腔。
7. 报告格式：每文件一行 `OK <路径>`；结尾列「待定术语」与不确定之处；不贴译文全文。

## 步骤 3：全量校验（A/B 收尾必做）

```bash
python3 .agents/skills/docs-translation/scripts/verify_structure.py
```

自动从 `project.json` 取路径（可用 `SRC_DIR`/`DST_DIR`/`PAIRS_FILE` 覆盖）。**必须全绿（exit 0）才算完成**，FAIL 逐条修到绿。结构校验抓不住散文措辞漂移——那靠 A1 的基线 diff，`state/sync-state.json` 是权威。

## 步骤 4：收尾

1. 更新 `state/sync-state.json`：`last_synced_commit` 取 `NEW`（完整 hash），更新 `last_synced_date`。
2. **自动提交**：`git add -A && git commit`，每批一个原子提交（校验绿+基线/清单更新）。**不 push**——推送是对外动作，由用户决定。

## 红线

- 本站非官方：不使用官方品牌资产，不自指官方；声明只在 index/README。
- 术语表双向约束，严禁现场发明译法；未收录的保留英文并列入「待定术语」。
- 代码围栏（含注释/信息串）与行内代码逐字节保留；链接 URL 原样。
- 译文不得引入裸 `{ } < >`（`$$` 公式块与 JSX 属性除外）；不得残留源格式标记（对照表左列）。
- 同步时最小改动；翻译时不增删信息、不改结构；转换 WARN 不许带着翻译。
- 未跑全量校验或未全绿，不得宣布完成；完成后必须更新同步基线。
- 零侵入：不碰译文内容、技能目录与 bootstrap_files 以外的任何文件。
- 新项目复用本技能前必须先有 `project.json` + 术语表 + 规则（含转换对照表）。
