# Project descriptions

## English

**Byte-Level BPE Analysis and Multilingual Sampling Design — Reproducible Tokenization Study**

Traced MinBPE merge behavior and verified exact `cl100k_base` token IDs on eight selected inputs. Tested three German/Spanish tokenizer-training mixtures across three paired seeds with a fixed bilingual bigram training corpus. On 1,000 aligned PUD sentence pairs, changing the German:Spanish quota from 90:10 to 75:25 lowered equal-language byte perplexity by 1.63%. Spanish improved by 4.25% while German worsened by 1.05%. The 50:50 reference scored within 0.04% of 75:25 on the aggregate.

## 中文

**字节级 BPE 分析与多语言抽样方案设计——可复现分词研究**

分析 MinBPE 合并规则，在 8 个测试输入上核对了与 `cl100k_base` 完全一致的编码。固定双语二元语言模型的训练文本，使用三个配对种子比较三种分词器训练配比。在 PUD 的 1,000 对测试句上，德语与西班牙语配额由 90:10 调整为 75:25 时，两种语言等权的每字节困惑度下降 1.63%，其中西语下降 4.25%、德语上升 1.05%。50:50 与 75:25 的综合差异约为 0.04%。

The project and report were developed with Codex assistance. [Measured pilot results](../results/quota_pilot.json) · [Contribution and source provenance](CONTRIBUTIONS.md)
