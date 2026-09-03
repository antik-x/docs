# DeepEval 中文文档（社区翻译）

本仓库是 [DeepEval](https://github.com/confident-ai/deepeval) 官方文档（deepeval.com）的**非官方中文翻译**，基于 Apache-2.0 许可的上游文档翻译，使用 Mintlify 构建与发布。

- 上游源码：[confident-ai/deepeval](https://github.com/confident-ai/deepeval) `docs/content/docs/`（Fumadocs/MDX）
- 翻译基线：见 `.agents/skills/docs-translation/state/sync-state.json`
- 内容以 [deepeval.com 官方英文文档](https://deepeval.com/docs/introduction) 为准；本站与官方无关，仅作社区学习交流

## 翻译流程

仓库内自带翻译技能 `.agents/skills/docs-translation/`（流程、术语表与校验脚本），采用「机械转换 → 人工翻译 → 结构校验」流水线：Fumadocs MDX 先转换为 Mintlify MDX 骨架（代码块逐字节保留），再进行人工翻译，最后由脚本校验结构一致性。

## 本地开发

```bash
npm i -g mint
mint dev
```

访问 `http://localhost:3000` 预览。
