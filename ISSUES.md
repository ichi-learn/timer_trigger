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

# Azure Function デプロイに関するトラブルシューティングの記録

## 概要

`ichi-translator-rebuilt-simple-20240523` という名前のAzure Function Appにおいて、`translate`関数が正常に動作しない問題が発生。以下に、これまでの調査と試行錯誤の過程を記録する。

## 初期症状

- `curl`コマンドでAPIエンドポイントを呼び出すと、空のレスポンスが返される。
- エラーメッセージやログは確認できない。

## 調査と対応の履歴

1.  **関数の登録状況の確認**
    - `az functionapp function show` コマンドを実行したところ、`translate`関数がAzure上で認識されていないことが判明。
    - **原因**: v2プログラミングモデルで作成された `function_app.py` が、v1モデルとして構成されたFunction Appと互換性がないためと推測。

2.  **v1プログラミングモデルへの移行**
    - v2モデルの `function_app.py` を削除。
    - v1モデルに準拠した以下のファイルを作成・修正。
        - `HttpTrigger/function.json`: HTTPトリガーと関数を定義。
        - `HttpTrigger/__init__.py`: 関数ロジックを記述。
        - `host.json`: Function Appのグローバル設定。
        - `requirements.txt`: 必要なPythonライブラリを定義。
    - 上記のファイルをzip化し、`az functionapp deployment source config-zip` で再デプロイ。
    - デプロイ後、`az functionapp function show` コマンドで関数が正常に登録されたことを確認。

3.  **実行時エラーの調査**
    - 関数登録後も `curl` は依然として空のレスポンスを返す。
    - `az webapp log tail` でログストリームに接続しようとしたが、`404 Not Found` エラーで失敗。
    - **原因**: ログサービスが起動する前の、極めて早い段階でアプリケーションがクラッシュしている可能性が浮上。起動時に必須の環境変数が読み込めていないと推測。

4.  **環境変数の設定ミス特定と修正**
    - `HttpTrigger/__init__.py` のコードを再レビューした結果、Key Vaultからシークレットを取得する箇所で、シークレット名が `translator-key` となっていることを発見。
    - 正しくは `TRANSLATOR-API-KEY` であり、この不一致が原因で `SecretClient` がエラーを吐き、アプリケーションが起動シーケンスの早い段階でクラッシュしていたと断定。
    - `__init__.py` 内のシークレット名を `TRANSLATOR-API-KEY` に修正。

5.  **デプロイパッケージの構成見直し**
    - 修正版のコードを `az functionapp deployment source config-zip` でデプロイしようとしたが、複数回にわたり `Bad Request` エラーで失敗。
    - `zip` コマンドの実行方法に問題がある可能性を考慮し、以下の対応を実施。
        - `HttpTrigger` ディレクトリに移動してからzip化。
        - カレントディレクトリを戻し、含めるファイルを明示的に指定してzip化。
    - いずれの方法でも `Bad Request` エラーは解決せず。

## 現在の状況と次のステップ

- コード上の問題（プログラミングモデルの不一致、不正なシークレット名）はすべて修正済み。
- Function AppもAzure上で正常に稼働している。
- しかし、修正版コードのデプロイ自体が `Bad Request` エラーで失敗する、という新たな問題に直面している。
- 次のステップとして、クリーンな一時ディレクトリ `temp_deploy` を作成し、そこにデプロイに必要なファイル（`HttpTrigger`フォルダ、`host.json`, `requirements.txt`）をコピーして、再度zipパッケージの作成とデプロイを試みる。
