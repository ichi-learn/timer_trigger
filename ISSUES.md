# Function App Deployment and Runtime Issues

## 概要

Function App `ichi-translator-rebuilt-20240523` のデプロイおよび実行において、深刻な問題が発生している。
`az functionapp deployment source config-zip` コマンドによるデプロイは成功しているように見えるが、Function Appのホストプロセスが正常に起動せず、結果としてHTTPトリガーが404エラーを返し、ログ関連のエンドポイントも機能していない。

## これまでの経緯

1.  **初期デプロイの試み:**
    *   `func azure functionapp publish ichi-translator-rebuilt-20240523` コマンドを実行したが、`Can't find app with name "ichi-translator-rebuilt-20240523"` というエラーで失敗。

2.  **Zipデプロイへの切り替え:**
    *   `zip -r deployment.zip .` でデプロイパッケージを作成。
    *   `az functionapp deployment source config-zip` でデプロイを実行したが、タイムアウトが発生。

3.  **Key Vault参照の修正と再デプロイ:**
    *   `local.settings.json` 内の `@Microsoft.KeyVault` 参照を修正し、再度デプロイを試みたが、状況は改善されなかった。

4.  **エンドポイントのテスト:**
    *   デプロイされたFunction Appのエンドポイント (`https://ichi-translator-rebuilt-20240523.azurewebsites.net/api/translate`) に対して `curl` でPOSTリクエストを送信したが、`HTTP/2 404` エラーが返された。

5.  **ログ取得の試み:**
    *   `az webapp log tail` および `az webapp log download` コマンドを実行してログを取得しようとしたが、いずれも `scm.azurewebsites.net` への接続に失敗し、404 Not Foundエラーとなった。これは、Function Appのホストが正常に起動していないため、ログ関連のエンドポイントが利用できないことを示唆している。

6.  **Function Appの再起動:**
    *   `az functionapp restart` を実行してFunction Appを再起動したが、問題は解決せず、ログ取得も依然として失敗する。

## 問題の核心

*   **Function Appホストの起動失敗:** デプロイされたコードのパッケージはストレージにアップロードされているものの、Azure Functionsのランタイムがそのコードを正常に読み込み、ホストプロセスを起動できていない可能性が高い。

## 考えられる原因

*   **依存関係の問題:** `requirements.txt` に記載されたライブラリのインストールが、デプロイプロセス中（Oryxビルドなど）に失敗している可能性がある。
*   **コードの実行時エラー:** `__init__.py` 内のコードに、起動シーケンスを妨げるような未処理の例外や設定ミスが存在する可能性がある。
*   **プラットフォーム構成の問題:** Function Appの構成（ランタイムバージョンの不一致など）や、関連するApp Service Planに何らかの問題がある可能性がある。
*   **環境起因の問題:** Nixベースの現在の開発環境とAzureのデプロイプロセスとの間に、予期せぬ非互換性が存在する可能性がある。

## 次のアクション

*   Azure PortalからFunction Appの「診断と問題の解決」ツールを使用して、プラットフォーム側の問題を調査する。
*   デプロイプロセスを簡略化し、最小限のコード（HTTPトリガーのみで他の依存関係なし）をデプロイして、ランタイム自体が正常に動作するかを切り分けする。
*   ローカル環境での実行は成功しているため、ローカルとAzure環境での設定（特に環境変数）の差異を再度徹底的に確認する。
