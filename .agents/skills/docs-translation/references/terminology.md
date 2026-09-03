# DeepEval 中文文档术语表（约束性·初版）

> 本表对所有翻译任务**双向约束**：表中词出现时必须按指定译法渲染；表中没有、且无可引用的中文技术社区先例的术语，保留英文并在任务报告中列入「待定术语」。**严禁现场发明译法。** 初版由翻译侧起草，用户审定后回填。

## 1. 保留英文（永不翻译）

- **产品与品牌**：DeepEval、Confident AI、Cursor、Claude Code、Codex、Windsurf、Jupyter
- **公司/模型/生态**：OpenAI、Anthropic、Gemini、Ollama、Azure OpenAI、OpenRouter、LangChain、LangGraph、LlamaIndex、CrewAI、Pydantic AI、Vertex AI、Bedrock、MCP、Vercel、Cloudflare、npx、pip、PyPI、Pytest、Vitest、GitHub、Discord
- **技术缩写**（首现按第 3 节标注中文）：LLM、RAG、CI/CD、CLI、SDK、API、JSON、YAML、CSV、URL、DOM、TPOT、TTFT、OTEL
- **评测范式名**：LLM-as-a-judge、G-Eval（作为概念时）；代码身份 GEval/ConversationalGEval 按代码身份处理
- **代码身份**：一切类名（LLMTestCase、ConversationalTestCase、Golden、EvaluationDataset、GEval、AnswerRelevancyMetric、TaskCompletionMetric、Synthesizer、ConversationSimulator、Konfig、DeepEvalBaseLLM…）、函数/方法/参数名（assert_test、evaluate、@observe、update_current_trace、metric_collection…）、指标枚举值（HIGH_SCHOOL_COMPUTER_SCIENCE…）、文件路径、命令行、环境变量（OPENAI_API_KEY、DEEPEVAL_RESULTS_FOLDER…）、配置键——**逐字节保留**
- **Tracing 语境**：trace→追踪（动词/名词均可按上下文），span→Span（保留），span name→Span 名称
- Token、Embedding 在代码/参数语境保留原文

## 2. 术语对照（EN → 简中）

| English | 中文 |
|---|---|
| evaluation / evals | 评估 |
| evaluation model | 评估模型 |
| metric | 指标 |
| score | 分数 |
| threshold | 阈值 |
| test case | 测试用例 |
| single-turn | 单轮 |
| multi-turn | 多轮 |
| turn | 轮次 |
| conversational | 对话式 |
| agent | 智能体 |
| tool call / tool use | 工具调用 |
| trajectory | 轨迹 |
| tracing | 追踪 |
| observability | 可观测性 |
| end-to-end | 端到端 |
| component-level | 组件级 |
| unit testing | 单元测试 |
| regression testing | 回归测试 |
| online evals | 在线评估 |
| golden / goldens | 金标（golden）（待定：或保留 golden） |
| dataset | 数据集 |
| synthetic data generation | 合成数据生成 |
| synthesizer | 合成器（组件名 Synthesizer 保留） |
| conversation simulation / simulator | 对话模拟 / 模拟器 |
| persona | 人设 |
| prompt | 提示词 |
| prompt optimization | 提示词优化 |
| prompt over-optimization | 提示词过拟合优化（待定） |
| benchmark | 基准测试 |
| hallucination | 幻觉 |
| faithfulness | 忠实度 |
| answer relevancy | 答案相关性 |
| contextual precision | 上下文精确率 |
| contextual recall | 上下文召回率 |
| contextual relevancy | 上下文相关性 |
| correctness | 正确性 |
| coherence | 连贯性 |
| safety | 安全 |
| bias | 偏见 |
| toxicity | 毒性 |
| red teaming | 红队测试 |
| vulnerability | 漏洞 |
| attack / attack method | 攻击 / 攻击方法 |
| simulated attack | 模拟攻击 |
| jailbreak | 越狱 |
| prompt injection | 提示词注入 |
| PII (personally identifiable information) | 个人身份信息（PII） |
| role violation | 角色违规 |
| misuse | 滥用 |
| unauthorized | 未授权 |
| ground truth | 基准真值 |
| expected output | 预期输出 |
| actual output | 实际输出 |
| retrieval context | 检索上下文 |
| input | 输入 |
| multimodal | 多模态 |
| conversational simulator | 对话模拟器 |
| framework | 框架 |
| integration | 集成 |
| local-first | 本地优先 |
| self-authored / custom metric | 自定义指标 |
| metric collection | 指标集合 |
| flag | 开关（环境开关语境） |
| voice agent | 语音智能体 |
| interruptibility | 可打断性 |
| chatbot | 聊天机器人 |
| arena | 竞技场（Arena 模式语境保留 Arena） |
| human feedback | 人类反馈 |
| pairwise comparison | 成对比较 |
| cost | 成本 |
| latency | 延迟 |

## 3. 首次出现中英对照（first occurrence）

- 检索增强生成（RAG）、大语言模型（LLM）、红队测试（red teaming）、金标（golden）、轨迹（trajectory）、追踪（tracing）、合成数据生成（synthetic data generation）
- 指标名正文行文中用「忠实度（Faithfulness）」式表述，代码语境一律 `FaithfulnessMetric`

## 4. 品牌/产品语（全站统一）

- 本站声明：「本站为社区维护的非官方中文翻译，内容以 deepeval.com 官方英文文档为准。」
- Confident AI 平台功能名（Datasets、Metrics、Tracing、Evaluation 等页面区块）译中文，首次出现保留英文对照。

## 5. 待定术语（首批交付后请用户审定）

- golden/goldens：「金标（golden）」vs 保留「golden」——当前按「金标（golden）」执行
- prompt over-optimization：当前按「提示词过拟合优化」执行
- Section/heading 内的 Confident AI 平台区块名是否译中文——当前按译中文执行
