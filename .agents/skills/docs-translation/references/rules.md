# DeepEval 中文文档翻译规则（约束性摘要）

源：https://deepeval.com/docs/* （源码：github.com/confident-ai/deepeval 仓库 `docs/content/docs/`，Fumadocs/MDX，Apache-2.0）
目标：本仓库（antik-x/docs）Mintlify 站点，URL/slug 与原站一一对应，输出 `.mdx`。
本站为**非官方社区翻译**：不使用官方 logo/品牌色，站点声明见 index.mdx 与 README.md。

## 0. 两步流水线（本项目特有）

1. **机械转换**：`python3 .agents/skills/docs-translation/scripts/convert_fumadocs.py <源.mdx ...>`
   把上游 Fumadocs MDX 转成 Mintlify MDX 骨架（英文原样保留）。转换规则见第 D 节对照表，
   脚本与 `fumadocs_norm.py` 是唯一实现；转换出现的 WARN 必须逐条消化，不许带着警告翻译。
2. **人工翻译**：在骨架上把人类语言译成中文（第 A/B/C 节约束）。代码围栏、URL、代码身份不动。
3. **校验**：单篇 `verify_mdx.py <源> <译>`；批次 `verify_structure.py`。全绿才算完成。

## A. 忠实（信）

1. 逐语义单元翻译：先读懂整段，再以中文技术作者口吻重述。**不增删任何信息**——不加解释、不加总结、不删例子、不合并段落。
2. 语气与原文一致：第二人称统一为「你」、主动语态、直接陈述。原文强调（粗体/斜体）落在语义对应位置。
3. 内容承诺（数字、版本号、限制、默认值、S3 链接）原样保留。

## B. 结构锁定

1. **标题**：层级与数量一一对应，顺序不变；标题不译出英文对照。
2. **代码围栏**：数量相同，**围栏内逐字节一致**（含 `title=`/`showLineNumbers` 等信息串）；语言标注原样。
3. **行内代码**：内容逐字节保留，位置语义对应；`<Term py="X" ts="Y"/>` 转换产生的行内代码见对照表。
4. **列表**：有序/无序不变，项数不变，嵌套不变。FAQ 答案内的要点以散文合并，不算列表项（源文即在字符串里）。
5. **表格**：行列数不变；表头译中文。
6. **链接**：URL/锚点/查询串逐字节保留（`/docs/...` 在本站同路径可达）；**链接文字**翻译。
7. **图片/视频**：`src` 逐字节保留；`alt`/`figcaption` 翻译。
8. **JSX 组件**：只译标签间人类文本与展示型属性（`title`/`label`/`description`/`alt`/`caption`）；`id`/`href`/`src`/`icon` 原样。`<Tab title>`、`<Accordion title>` 的 title 译中文。
9. **frontmatter**：只保留 `title`（译中文，简洁）与 `description`（如有，忠实完整）；不增删键。
10. **转义**：译文中不得引入裸 `{ } < >`；源文 `\{`、`&lt;` 等原样保留。
11. **水平线、空行分段**与源文一致。

## C. 术语纪律

- 术语表 `references/terminology.md` 必读、双向约束，严禁现场发明译法。
- 核心概念正文首现用「中文（English）」；标题不加对照。
- 未收录且无中文社区先例的术语保留英文，列入任务报告「待定术语」。
- 同一篇内同一术语译法唯一。

## D. Fumadocs → Mintlify 转换对照表（转换器已实现，翻译时不要改回）

| 源（Fumadocs） | 目标（Mintlify） |
|---|---|
| frontmatter `id`/`languages`/`sidebar_label` | 删除；`sidebar_label` 译中文后登记 `state/nav-zh.json`（导航标题） |
| frontmatter `beta: true` | 正文顶部插 `<Note>`：**Beta。** 该功能处于 Beta 阶段，接口与行为可能变化。 |
| `import ...` 行 | 全部删除 |
| `<Term py="X" ts="Y"/>`，Y=camelCase(X) 或 Y="npx "+X | `` `X` `` |
| `<Term py="X" ts="Y"/>`，其余 | `` `X` ``（TypeScript 中为 `` `Y` ``） |
| `<Switch>/<Case id="python|typescript">` | `<Tabs>/<Tab title="Python|TypeScript">` |
| `<Tabs items={["A",...]}>` + `<Tab value="A">` | `<Tabs>` + `<Tab title="A">` |
| `:::tip[标题]` | `<Tip>` 内首行 `**标题**`（info/note/warning/caution/danger → Info/Note/Warning/Warning/Danger） |
| `<Cards>/<Card icon={<X/>}>` | `<CardGroup cols={2}>/<Card icon="x-kebab">` |
| `<Steps>/<Step>` | 同名保留（Step 子内容含 `###` 小标题，原样） |
| `<Equation formula="F"/>` | `$$F$$` |
| `<FAQs qas={[...]}/>` | `<AccordionGroup>` + `<Accordion title="问题">答案</Accordion>`（title 去反引号） |
| `<ImageDisplayer src={ASSETS.x} alt caption>` | `![alt](URL)` + `*caption*` 行 |
| `<VideoDisplayer src description ctaText>` | `<figure><video controls src="URL"/></video><figcaption>描述</figcaption></figure>` |
| 裸 `src={ASSETS.x}`（如 `<video><source>`） | 字面 URL |
| `<DefaultLLMModel provider?/>` | 对应默认模型代码段（openai=`gpt-5.4` 等，见 fumadocs_norm.DEFAULT_MODELS） |
| `<MetricTagsDisplayer .../>` | `**标签**：LLM-as-a-judge · 单轮 · …`（默认值展开规则见 fumadocs_norm.METRIC_TAG_ORDER） |
| `<NotImplemented id="typescript" feature="X">` | `<Note>`：**501 · TypeScript 暂未实现** + `X` 尚未在 TypeScript SDK 中提供… |
| `<Only id="python">X</Only>` | 直接解包为 X |
| `<Only id="typescript">Y</Only>` | 行内 `（TypeScript：Y）`；块级 `<Info>`+`**TypeScript**` 首行 |
| `<include cwd>片段#锚点</include>` | 片段内容内联（`#锚点` 取 `<section id>` 小节） |
| `<details>/<summary>` | 保留（Mintlify 可编译） |
| `<span id="..."/>` 锚点 | 保留 |
| lucide 行内图标（`<Bot/>` 等） | 删除（纯装饰） |
| 装饰动画组件（VibeCodingLoop/AgentTraceTerminal/TraceLoopConnector/ClaudeCodeTerminal/RepoContributors） | 删除（纯视觉演示，无文字内容） |

译文残留上表左列任何标记（`<Switch`、`qas={`、`:::`、`ASSETS.`、`import `…）即校验 FAIL。

## E. 中文排版（雅）

1. 全角标点：，。；：？！（）；破折号——；省略号……。
2. 中西文之间加一个空格（含中文与数字之间，如「50+ 个指标」「使用 pip 安装」）。
3. 全角括号内为纯英文/代码时用半角括号且外侧不加空格。
4. 标题不使用句末标点；列表项完整句用句号，短语不加。
5. 单位写法：50%、3 GB、v1.2。

## F. 流程与收尾

1. 每批按导航组推进（约 9–12K 英文词）：转换 → 翻译 → 自检 → `verify_structure.py` 全绿 → 登记 `pairs`/`nav-zh.json` → 重新生成 `docs.json` → 原子 commit（不 push）。
2. 任务报告：每文件一行 `OK <路径>`；结尾列「待定术语」与不确定之处；不贴译文全文。
3. 全部批次完成后：全量校验 + 更新 `state/sync-state.json` 的 `last_synced_commit`。
