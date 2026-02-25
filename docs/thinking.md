# Thinking / Extended Reasoning

ollama-swapper は、モデルが生成する「思考過程（thinking）」をクライアント側でオプトインできる仕組みを提供します。

## 概要

多くの推論系モデル（DeepSeek-R1, QwQ, Qwen3 など）は `think: true` を指定すると、
最終回答の前に内部思考をストリームします。デフォルトでは ollama-swapper はこの思考部分を除去し、
本文のみをクライアントに返します。

クライアントが `include_thinking: true` をリクエストに含めると、thinking コンテンツも合わせて返します。

## リクエスト形式

```json
{
  "model": "deepseek-r1:8b",
  "think": true,
  "include_thinking": true,
  "messages": [
    {"role": "user", "content": "素数を説明して"}
  ],
  "stream": true
}
```

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `think` | bool | false | モデルに思考させる（upstream に転送される） |
| `include_thinking` | bool | **false** | thinking をレスポンスに含めるかどうか（proxy が処理・除去） |

> `include_thinking` は proxy が消費するフィールドで、upstream には転送されません。

## レスポンス形式

### ストリーミング（`stream: true`）

thinking チャンク:
```json
{"model": "deepseek-r1:8b", "message": {"role": "assistant", "content": "", "thinking": "まず素数の定義を..."}, "done": false}
```

本文チャンク（通常通り）:
```json
{"model": "deepseek-r1:8b", "message": {"role": "assistant", "content": "素数とは..."}, "done": false}
```

### 非ストリーミング（`stream: false`）

```json
{
  "model": "deepseek-r1:8b",
  "message": {
    "role": "assistant",
    "content": "素数とは...",
    "thinking": "まず素数の定義を..."
  },
  "done": true
}
```

## デフォルト動作（`include_thinking: false`）

- thinking チャンク（`message.thinking` を持つチャンク）はスキップされる
- 非ストリームレスポンスの `message.thinking` フィールドは除去される
- クライアントには本文のみが届く

## 対応パス

| パス | 対応 |
|---|---|
| ネイティブ Ollama upstream (`api/chat`) | ✅ |
| OpenAI 互換 upstream（`upstream` per-model 設定時） | ✅ |
| `api/generate` | ✅（ストリームフィルタのみ、thinking フィールドが存在する場合） |

## OpenAI 互換 upstream での動作

per-model `upstream` を設定したモデルは OpenAI API (`v1/chat/completions`) にブリッジされます。
OpenAI 互換サーバーが返す `reasoning_content` または `thinking` デルタフィールドを
Ollama 形式の `message.thinking` に変換します。

`include_thinking: false`（デフォルト）の場合、ブリッジ変換時にこれらのフィールドを除去します。

## 使用例

### curl（ストリームあり・thinking 表示）

```bash
curl http://127.0.0.1:11434/api/chat \
  -d '{
    "model": "deepseek-r1:8b",
    "think": true,
    "include_thinking": true,
    "messages": [{"role": "user", "content": "1+1は？"}],
    "stream": true
  }'
```

### curl（ストリームなし・thinking 非表示）

```bash
curl http://127.0.0.1:11434/api/chat \
  -d '{
    "model": "deepseek-r1:8b",
    "think": true,
    "messages": [{"role": "user", "content": "1+1は？"}],
    "stream": false
  }'
```

thinking は除去され、`message.content` のみが返ります。
