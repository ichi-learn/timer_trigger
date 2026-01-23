# Azure Functions アプリケーション設計書

## 1. 概要

本ドキュメントは、Azure Functionsを利用して構築された日本語から英語へのテキスト翻訳APIの設計について記述する。

この関数アプリは、HTTPリクエストをトリガーとして、指定された日本語テキストを英語に翻訳し、結果をJSON形式で返す機能を提供する。Azure Cognitive Services の一つである Translator サービスと連携して動作する。**さらに、翻訳の履歴をAzure Table Storageに保存する機能も持つ。**

## 2. 機能要件

- HTTP POSTリクエストで日本語テキストを受け付ける。
- 受け取った日本語テキストを英語に翻訳する。
- **翻訳の原文、訳文、タイムスタンプをAzure Table Storageに保存する。**
- 翻訳結果をJSON形式のHTTPレスポンスとして返す。
- 外部サービス（Azure Translator, Azure Storage）の認証情報を環境変数から安全に読み込む。
- 想定されるエラー（不正なリクエスト、認証エラーなど）に対して適切なHTTPステータスコードとエラーメッセージを返す。

## 3. 技術仕様

### 3.1. 関数定義

- **トリガータイプ:** HTTP Trigger
- **エンドポイント (ルート):** `/translate`
- **認証レベル:** Anonymous (誰でもアクセス可能)
- **許可するHTTPメソッド:** `POST`

### 3.2. APIインターフェース

#### リクエスト

- **メソッド:** `POST`
- **ヘッダー:** `Content-Type: application/json`
- **ボディ:**
  ```json
  {
    "text": "こんにちは"
  }
  ```
  - `text` (string, 必須): 翻訳対象の日本語テキスト。

#### レスポンス

- **成功時 (200 OK):**
  - **ヘッダー:** `Content-Type: application/json`
  - **ボディ:**
    ```json
    {
      "translated_text": "Hello"
    }
    ```
- **エラー時:**
  - **400 Bad Request:** リクエストボディが不正なJSON形式、または`text`フィールドが存在しない場合。
  - **401 Unauthorized:** Translatorサービスの認証に失敗した場合。
  - **500 Internal Server Error:** その他の予期せぬエラーが発生した場合。

### 3.3. 依存関係

#### 外部サービス

- **Azure Cognitive Service for Translator:** テキスト翻訳機能を提供。
- **Azure Table Storage:** 翻訳履歴を永続化するために使用。

#### Pythonライブラリ

プロジェクトは以下の主要なPythonライブラリに依存する。詳細なリストは`requirements.txt`を参照。

- `azure-functions`: Azure Functionsのランタイムライブラリ。
- `azure.ai.translation.text`: Azure Translatorサービスクライアントライブラリ。
- `azure.core`: Azureクライアントライブラリのコア機能。
- **`azure.data.tables`**: Azure Table Storageを操作するためのライブラリ。**（新規）**

### 3.4. 環境変数

本関数アプリは、動作するために以下の環境変数が設定されている必要がある。

- `TRANSLATOR_KEY`: Azure TranslatorサービスのAPIキー。
- `TRANSLATOR_ENDPOINT`: Azure TranslatorサービスのエンドポイントURL。
- `TRANSLATOR_REGION`: Azure Translatorサービスがデプロイされているリージョン。
- **`AzureWebJobsStorage`**: Azure Storageアカウントへの接続文字列。翻訳履歴の保存に使用する。**（新規）**

### 3.5. データモデル (Azure Table Storage)

- **テーブル名:** `TranslationHistory`
- **エンティティ:**
  - **PartitionKey:** `translation` (固定値)
  - **RowKey:** `str(uuid.uuid4())` (各レコードの一意なID)
  - **OriginalText** (string): 翻訳元の日本語テキスト。
  - **TranslatedText** (string): 翻訳後の英語テキスト。
  - **Timestamp** (datetime): 翻訳が実行された日時。

## 4. 内部実装 (`function_app.py`)

1.  **クライアント初期化:**
    - 環境変数から`KEY`, `ENDPOINT`, `REGION`を読み込む。
    - `AzureKeyCredential`と`TextTranslationClient`を用いて、Translatorサービスクライアントを初期化する (`get_client`関数)。
    - **環境変数 `AzureWebJobsStorage` から接続文字列を取得し、`TableServiceClient` を初期化する。**

2.  **HTTPトリガー関数 (`translate_function`):**
    - `POST`リクエストを受け取る。
    - リクエストボディをJSONとして解析し、`text`フィールドを取得する。
    - バリデーションチェックを行い、`text`フィールドが存在しない場合は400エラーを返す。
    - `get_client`を呼び出してTranslatorサービスクライアントを取得する。
    - `client.translate`メソッドを呼び出し、翻訳を実行する。
    - **翻訳が成功した場合、以下の処理を行う。**
        - **`TableClient` を使用して `TranslationHistory` テーブルにアクセスする。**
        - **新しいエンティティを作成し、`OriginalText`、`TranslatedText`、`Timestamp` を設定する。**
        - **`create_entity` メソッドを呼び出して、エンティティをテーブルに保存する。**
    - レスポンスから翻訳済みテキストを抽出し、JSON形式でクライアントに返す。
    - 例外処理を実装し、認証エラーやその他のエラーを適切にハンドリングして、500エラーまたは401エラーを返す。

## 5. デプロイと運用

デプロイと運用手順の詳細は `AZURE_DEPLOYMENT_PROCEDURE.md` に記載されている。(変更なし)

## 6. アーキテクチャ図

```
[クライアント]
     |
     | (1) HTTP POST /api/translate
     |     Request: { "text": "日本語テキスト" }
     V
+-----------------------------------+
|      Azure Function App           |
|  (Python, HTTP Trigger)           |
+-----------------------------------+
     |        |
     |        | (2) 翻訳API呼び出し
     |        V
     |  +--------------------------+
     |  | Azure Translator Service |
     |  +--------------------------+
     |        ^
     |        | (3) 翻訳結果の返却
     |        |
     |        | (4) 履歴エンティティの書き込み
     |        V
     |  +-----------------------------+
     |  |     Azure Table Storage     |
     |  | (TranslationHistory テーブル) |
     |  +-----------------------------+
     |
     V
+-----------------------------------+
|      Azure Function App           |
| (履歴保存後、レスポンス返却)      |
+-----------------------------------+
     |
     | (5) HTTP 200 OK
     |     Response: { "translated_text": "Translated Text" }
     V
[クライアント]
```
