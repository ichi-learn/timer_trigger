# 開発・デプロイ設計書

## 1. 概要

本ドキュメントは、翻訳API機能を持つAzure Functionsアプリケーションの開発環境、デプロイプロセス、およびAzure上のインフラストラクチャについて定義する。

- **アプリケーション設計:** 機能詳細、API仕様、データモデルについては `DESIGN.md` を参照。
- **手動デプロイ手順:** 具体的なコマンド操作については `AZURE_DEPLOYMENT_PROCEDURE.md` を参照。

## 2. 開発環境

ローカルマシンでアプリケーションを開発し、テストするための環境を定義する。

### 2.1. 必要なツール

| ツール                                   | 用途                                       |
| -------------------------------------- | ------------------------------------------ |
| Python (3.9+)                          | アプリケーション実行言語                   |
| Visual Studio Code                     | 推奨IDE                                    |
| └ Azure Functions Extension            | VS Code上でのAzure Functions開発支援       |
| Azure Functions Core Tools (`func`)    | ローカルでのFunctions実行、デバッグ        |
| Azure CLI (`az`)                       | Azureリソースの管理とデプロイ              |
| Git                                    | ソースコードのバージョン管理               |

### 2.2. 環境構築手順

1.  **リポジトリのクローン:**
    ```bash
    git clone <repository_url>
    cd <repository_folder>
    ```
2.  **Python仮想環境の作成と有効化:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate      # Windows
    ```
3.  **依存ライブラリのインストール:**
    ```bash
    pip install -r requirements.txt
    ```

### 2.3. ローカル構成 (`local.settings.json`)

ローカル開発でアプリケーションをテストするには、クラウド上で利用するAzureサービス（Translator、Storage Account）への接続情報が必要です。これらの機密情報を管理するために `local.settings.json` ファイルを使用します。

#### 2.3.1. なぜローカル設定が必要か (クラウド環境との違い)

- **環境の分離:** ローカル開発環境 (`func start`で起動) は、実際のAzureクラウド環境から完全に独立しています。そのため、Azure PortalのFunction Appに設定した「構成」の値を自動で読み取ることはできません。

- **設定のシミュレーション:** `local.settings.json` ファイルは、Azure上のFunction Appの「構成 (Configuration)」をローカルで**模倣（シミュレート）**するための仕組みです。

- **コードの互換性:** `os.environ.get("SETTING_NAME")` のようなコードは、実行されている環境に応じて参照先を自動で切り替えます。
    - **ローカル実行時:** `local.settings.json` ファイル内の `"Values"` ブロックを参照します。
    - **クラウド実行時:** Function Appの「構成」に設定されたアプリケーション設定を参照します。

この仕組みにより、開発者は**コードを一切変更することなく**、ローカルとクラウドの両方でアプリケーションを実行できます。したがって、ローカルでの動作確認を円滑に進めるためには、開発者自身がAzureから取得したパラメータを `local.settings.json` に設定する必要があります。

#### 2.3.2. `local.settings.json` のテンプレート
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "<AZURE_STORAGE_CONNECTION_STRING>",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TRANSLATOR_KEY": "<YOUR_TRANSLATOR_KEY>",
    "TRANSLATOR_ENDPOINT": "<YOUR_TRANSLATOR_ENDPOINT>",
    "TRANSLATOR_REGION": "<YOUR_TRANSLATOR_REGION>"
  }
}
```

#### 2.3.3. Azureパラメータの取得方法

`local.settings.json` に設定する各値は、Azure PortalまたはAzure CLIを使用して取得します。

**1. Translator Service の情報**

-   **対象リソース:** Azure Portal上の `Translator` または `Cognitive Services` リソース。
-   **取得場所:** `Keys and Endpoint` ブレード。

| パラメータ              | `local.settings.json` のキー | Portalでの項目名          |
| ----------------------- | --------------------------- | ------------------------- |
| APIキー                 | `TRANSLATOR_KEY`            | `Key 1` (または `Key 2`)  |
| エンドポイントURL         | `TRANSLATOR_ENDPOINT`       | `Endpoint`                |
| リージョン              | `TRANSLATOR_REGION`         | `Location` / `Region`     |

**2. Storage Account の接続文字列**

-   **対象リソース:** Azure Portal上の `Storage Account` リソース。
-   **取得場所:** `Access keys` ブレード。

| パラメータ   | `local.settings.json` のキー | Portalでの項目名         |
| ------------ | --------------------------- | ------------------------ |
| 接続文字列   | `AzureWebJobsStorage`       | `Connection string`      |

### 2.4. ローカルでの実行とデバッグ

- **実行:** ターミナルで `func start` を実行します。
- **デバッグ:** VS Codeの "Run and Debug" 機能を利用します。

## 3. デプロイ設計

ローカルで開発したアプリケーションをAzureにデプロイする方法を定義する。

### 3.1. ソースコード管理

- **バージョン管理システム:** Git

### 3.2. デプロイ戦略

- **手動デプロイ:** Azure CLI (`az functionapp deployment source config-zip`) を使用。詳細は `AZURE_DEPLOYMENT_PROCEDURE.md` 参照。
- **自動デプロイ (CI/CD) - 推奨:** GitHub Actionsなどを使用し、`main` ブランチへのプッシュをトリガーに自動デプロイを実行する。

## 4. Azure環境設計

### 4.1. Azureリソース

| リソース               | 目的                                            |
| ---------------------- | ----------------------------------------------- |
| **Resource Group**     | 全てのリソースを管理するためのコンテナ          |
| **Storage Account**    | Function Appの実行状態、および翻訳履歴を保存     |
| **Translator Service** | Cognitive Servicesの翻訳機能を提供              |
| **Function App**       | アプリケーションコードの実行環境                |
| **Application Insights**| パフォーマンス監視、エラー追跡、ログ分析       |

### 4.2. 構成管理 (Azure上)

- ローカルの `local.settings.json` に設定した値は、デプロイ先のAzure Function Appの `Configuration` > `Application settings` にも同様に設定する必要があります。
- `AzureWebJobsStorage` はFunction App作成時に自動的に設定されます。

### 4.3. 監視とロギング

- **リアルタイムログ:** `az webapp log tail` コマンドでリアルタイムのログストリームを確認できます。
