# FastGPT Knowledge Retrieval

**Author:** xiaozie-xy  
**Version:** 0.0.1  
**Type:** Tool plugin

## Overview

FastGPT Knowledge Retrieval is a Dify tool plugin. It calls the FastGPT [searchTest](https://cloud.fastgpt.cn/apidoc/devapi#tag/%E7%9F%A5%E8%AF%86%E5%BA%93%E7%AE%A1%E7%90%86/POST/core/dataset/searchTest) API to retrieve chunks.

It helps developers who want to use a FastGPT knowledge base from Dify. Search parameters follow the payload used by the FastGPT knowledge-base test page.

## Features

- **Runtime dataset selection.** Each run searches the knowledge base given by `datasetId`.
- **Search mode.** Semantic, full-text, or mixed search.
- **Semantic search weight.** For mixed search, set the vector weight.
- **Citation limit and similarity.** `limit` is a token budget, not top K. Use `similarity` to filter results.
- **Rerank.** Toggle rerank and pick a rerank model from the saved FastGPT account, plus a weight. When rerank is off, the model and weight are not sent.
- **Query extension.** Optionally rewrite the query with a model and background text. When extension is off, the model and background are not sent.
- **Temporary image keys.** Optional. Accepts only FastGPT presign temporary keys.
- **Two outputs.** `result` is the chunk list. `context` is the joined text.

## Installation

Upload `fastgpt_knowledge-0.0.1.difypkg` on the Dify plugins page. If a self-hosted instance rejects the unsigned local package, turn off forced plugin signature checks in the deployment configuration and install it again. Then enter the FastGPT site URL and an API key.

## Configuration

### Provider credentials

Configure these once. This key is not a key from an application publish page.

| Parameter | Description | Required |
|-----------|-------------|:--------:|
| `api_base` | FastGPT site URL without `/api`. Cloud: `https://cloud.fastgpt.cn`. Self-hosted: your own site URL. The plugin calls `{base}/api/core/dataset/searchTest`. | Yes |
| `api_key` | Create it under Account → API Keys. See [How to get an API key](https://doc.fastgpt.io/zh-CN/openapi/intro#%E5%A6%82%E4%BD%95%E8%8E%B7%E5%8F%96-api-key). The account must be the dataset creator or a collaborator, or search returns `unAuthDataset`. Do not use a key from an app publish page. | Yes |

### Tool parameters

**Bound from workflow variables**

| Parameter | Description | Required |
|-----------|-------------|:--------:|
| `datasetId` | FastGPT dataset ID for this run. | Yes |
| `text` | Content to search. | Yes |
| `searchMode` | `embedding`, `fullTextRecall`, or `mixedRecall`. | No |
| `embeddingWeight` | From 0 to 1. Sent only when search mode is mixed. | No |
| `usingReRank` | Whether FastGPT reranks the result. When off, the rerank model and weight are not sent. | No |
| `rerankModelId` | Rerank model from the saved FastGPT account. Sent only when rerank is on. | No |
| `rerankWeight` | From 0 to 1. Sent only when rerank is on. Default 0.5. | No |
| `datasetSearchUsingExtensionQuery` | Rewrite the query before search. When off, the extension model and background are not sent. | No |
| `datasetSearchExtensionModelId` | Language model from the saved FastGPT account. Sent only when query extension is on. | No |
| `datasetSearchExtensionBg` | Background for query rewriting. When extension is on, an empty value is still sent as an empty string. | No |

**Set on the tool node**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `queryImageUrls` | Comma-separated FastGPT temporary image keys. Leave empty for text search; the request then sends `[]`. Public URLs and Dify file IDs are not accepted. | Empty |
| `limit` | Maximum cited tokens, from 1 to 20000. | 5000 |
| `similarity` | Minimum relevance from 0 to 1. Applied to semantic search and reranked results. 0 keeps every recalled chunk. | 0 |

Save the FastGPT URL and API key successfully before opening a model dropdown. The plugin loads `GET /api/core/ai/model/catalog` and submits the selected FastGPT model ID. If credentials are not saved yet, the dropdown shows a message asking you to save them first.

## Screenshots

Parameters follow FastGPT's knowledge-base search settings, such as search mode, citation limit, similarity, rerank, and query extension:

![FastGPT knowledge search settings](_assets/fastgpt-search-config.png)

In the Dify tool node, dataset ID, search text, search mode, semantic weight, rerank, and query extension live under input variables:

![Dify node input variables](_assets/dify-node-inputs-top.png)

Temporary image keys, max tokens, and minimum similarity are in the node settings block:

![Dify node settings](_assets/dify-node-inputs-settings.png)

Rerank and query-extension models use a dynamic dropdown loaded from the saved FastGPT account:

![Model dynamic dropdown](_assets/dify-node-model-dropdown.png)

In current Dify builds, opening a `dynamic-select` in the tool node settings zone (`form: form`) may not send the saved plugin credentials, so the list fails to load. Rerank and query-extension model fields therefore stay in the input variables zone (`form: llm`) for now. After Dify merges a fix, these model selectors may move back into settings.

## Examples

Semantic search of one knowledge base:

```text
datasetId: your-dataset-id
text: content to search
searchMode: embedding
limit: 5000
similarity: 0
```

Mixed search with rerank and query extension:

```text
searchMode: mixedRecall
embeddingWeight: 0.65
usingReRank: true
rerankModelId: (choose from dropdown)
rerankWeight: 0.5
datasetSearchUsingExtensionQuery: true
datasetSearchExtensionModelId: (choose from dropdown)
datasetSearchExtensionBg: The current dialogue is about HR policies
limit: 5000
similarity: 0.13
```

## Workflow

```text
Start
  datasetId = FastGPT dataset ID for this task
  text      = content to search
        |
        v
FastGPT Knowledge Retrieval
  Build the searchTest body from searchMode / rerank / query extension
  Call FastGPT {base}/api/core/dataset/searchTest
        |
        v
Downstream LLM
  Use context as the retrieved text
  Use result when scores, sources, or chunk details are needed
```

Creating, uploading, and indexing datasets stay on the FastGPT side. The target dataset should already be searchable before this tool runs.

## Outputs

| Output | Description |
|--------|-------------|
| `result` | Chunks in FastGPT's return order. Each item has `content`, `q`, `a`, `score`, `score_details`, `id`, `dataset_id`, `collection_id`, `source_name`, `source_id`, `chunk_index`, `update_time`, and `position`. Document chunks often have an empty `a`. `score` prefers rerank, then embedding, full text, and RRF. `score_details` keeps each `type`, `value`, and `index`. Full-text values can be greater than 1. |
| `context` | Chunk `content` values joined with blank lines, ready for an LLM prompt. |
| Text message | Same as `context`. When nothing matches, the text says that no chunks were retrieved. |

The JSON message also includes `duration`, `limit`, `searchMode`, `usingReRank`, `similarity`, and `queryExtensionModel` from the FastGPT response.

## Limitations

- `limit` is a token budget. This API does not take a top-K count.
- `queryImageUrls` accepts only FastGPT temporary keys from the presign API, not public URLs or Dify file IDs.
- Semantic search weight is sent only for mixed search. When rerank or query extension is off, the related model and weight (or background) are not sent.
- If the account is neither the dataset creator nor a collaborator, search returns `unAuthDataset`.
- This plugin does not create, upload to, or delete FastGPT knowledge bases.
- Model dropdowns need saved plugin credentials. The settings zone cannot reliably trigger dynamic select yet, so model fields stay in input variables for now.

## Requirements

- Dify 1.17.1 or newer
- A FastGPT API key created by the dataset creator or a collaborator on that dataset
- Python 3.12

## License

[Apache License 2.0](https://github.com/xiaozie-xy/dify_plugin_fastgpt_knowledge/blob/main/LICENSE).

## Links

- [Source repository](https://github.com/xiaozie-xy/dify_plugin_fastgpt_knowledge)
- [FastGPT dataset API](https://cloud.fastgpt.cn/apidoc/devapi#tag/%E7%9F%A5%E8%AF%86%E5%BA%93%E7%AE%A1%E7%90%86/POST/core/dataset/searchTest)
- [How to get an API key](https://doc.fastgpt.io/zh-CN/openapi/intro#%E5%A6%82%E4%BD%95%E8%8E%B7%E5%8F%96-api-key)
- [Dify](https://dify.ai/)
