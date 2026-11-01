# Project descriptions

## English

**Byte-Level BPE Analysis and Multilingual Sampling Design — Reproducible Tokenization Study**

Traced how MinBPE counts overlapping pairs and applies disjoint replacements. Used a counterexample to explain how learned merge order determines encoding. Verified exact `cl100k_base` token IDs and full-text round trips on eight ordinary-text inputs. Implemented four checks on hypothetical language quotas and designed a controlled German/Spanish tokenizer experiment. Documented the AI-assisted work in a reproducible report with three vector figures.

## 中文

**字节级 BPE 分析与多语言抽样方案设计——可复现分词研究**

跟踪 MinBPE 如何统计重叠的相邻词元对、执行互不重叠的替换，并用反例说明已学合并顺序如何决定编码。在 8 个普通文本输入上核对了与 `cl100k_base` 完全一致的编号和完整往返结果。对假设语料配额实施 4 项算术检查，设计德语与西班牙语分词器的对照实验方案，并在 AI 辅助下完成可复现报告和 3 张矢量图。

The descriptions concern the executed mechanism and encoding checks and the documented multilingual design. Real-corpus ratio experiments remain proposed. Source and tool-use provenance is recorded in [CONTRIBUTIONS](CONTRIBUTIONS.md).
