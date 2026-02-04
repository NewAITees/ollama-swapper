# ollama-swapper
Ollama のモデルポリシー（コンテキスト長・keep-alive）を強制する軽量プロキシ + CLI です。アイドル状態のモデルを停止するスイープ機能も提供します。

## 目的
- クライアントが指定しない場合に、モデルごとの `num_ctx` 既定値を適用する。
- `keep_alive=0` を既定として、生成後にモデルを即時アンロードする。
- 依然ロードされているモデルを停止するスイープコマンドを提供する。

## インストール
```bash
pip install -e .
```

## 設定
YAML または JSON をサポートします。例:
```yaml
server:
  listen: "127.0.0.1:11434"
  upstream: "http://127.0.0.1:11436"
policy:
  defaults:
    num_ctx: 8192
    keep_alive: 0
  models:
    "llama3.1:8b-instruct-q4_K_M":
      num_ctx: 32768
      keep_alive: "60s"
    "qwen2.5-coder:32b-instruct-q4_K_M":
      num_ctx: 65536
      keep_alive: 0
```

## 使い方
### プロキシ起動
```bash
ollama-swapper proxy --config /path/to/config.yaml
```

### プロキシ起動（ポリシー注入の詳細ログ）
```bash
ollama-swapper proxy --config /path/to/config.yaml --verbose
```

### ロード中モデルの表示
```bash
ollama-swapper ps
```

### スイープ（全停止）
```bash
ollama-swapper sweep
```

### 単一モデルの停止
```bash
ollama-swapper stop llama3:latest
```

## 運用メモ
- 推奨ポート: プロキシを `11434`、Ollama 本体を `11436` に配置。
- プロキシは、クライアントが省略した場合のみ `options.num_ctx` と `keep_alive` を注入します。
- プロキシを介さない場合は `ollama-swapper sweep` で VRAM を回収してください。
- `ps`/`sweep`/`stop` は `ollama` コマンドが PATH にある必要があります。
- `ollama-swapper` が PATH に無い場合は
  `C:\analysis2\ollama-swapper\.venv\Scripts\ollama-swapper.exe` で実行してください。

## Ollama のデフォルトポートを変更する
Ollama 側の待受アドレス/ポートは環境変数 `OLLAMA_HOST` で変更できます。

例（PowerShell）:
```powershell
$env:OLLAMA_HOST="127.0.0.1:11436"
ollama serve
```

この変更に合わせて、`config.yaml` の `server.upstream` も同じポートに合わせてください。

## 起動時の自動起動手順（Windows）
### 目的
- Ollama を `11436` で自動起動する
- `ollama-swapper` を起動時に自動起動する

### 手順
1) **ユーザー環境変数に書き込む**
```powershell
setx OLLAMA_HOST "http://0.0.0.0:11436"
```

2) **再起動（またはサインアウト/サインイン）**
環境変数は新しいログオンセッションから反映されます。

3) **Ollama を起動時に自動起動**
スタートアップに `Ollama` のショートカットがある前提です。

4) **ollama-swapper を起動時に自動起動**
スタートアップに次のショートカットを作成します。

- 対象:
  `C:\analysis2\ollama-swapper\.venv\Scripts\ollama-swapper.exe`
- 引数:
  `proxy --config C:\analysis2\ollama-swapper\config.yaml`
- 作業フォルダ:
  `C:\analysis2\ollama-swapper`

### 確認
```powershell
Invoke-WebRequest -Uri http://127.0.0.1:11436/ -Method GET
```
