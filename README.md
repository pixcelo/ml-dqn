# 自動売買プログラム

機械学習モデルを使用した仮想通貨の自動売買プログラムです。

このプログラムは、市場データを取得し、学習済みのモデルに基づいて売買の予測を行い、実際の取引を実行します。

また、取引結果をログに出力し、Discordの指定チャンネルに通知します。

## ディレクトリ構成
```
.
├── config.ini
├── discord_notifier.py
├── logger.py
├── main.py
├── model
│   └── model.pkl
├── predict.py
└── trade.py
```

## アーキテクチャ

1. エントリポイント: main.py
   - プログラムの開始地点で、他のコンポーネントを呼び出します。

2. 設定ファイル: config.ini
   - 仮想通貨の取引所アカウント情報や、DiscordのWebhook URLなどの設定を格納します。

3. 仮想通貨取引用モジュール: trade.py
   - ccxtライブラリを使用して仮想通貨の売買を行います。
   - トレードの実行、現在のポジションや利益情報の取得などを行います。

4. 機械学習モデルの読み込みと予測モジュール: predict.py
   - 学習済みのモデルを読み込み、現在の市場データに基づいて売買の予測を行います。

5. ログ出力モジュール: logger.py
   - トレードや予測の結果をログに出力します。

6. Discord通知モジュール: discord_notifier.py
   - webhookを使用して、指定したDiscordチャンネルにトレードや予測結果を通知します。

## 使用方法

1. config.iniファイルに取引所のAPIキー、シークレットキー、取引所名、DiscordのWebhook URLを設定してください。

```
[exchange]
api_key = your_api_key
secret_key = your_secret_key
exchange_name = bybit

[discord]
webhook_url = your_discord_webhook_url

[model]
model_path = model/model.pkl
```

2. 学習済みの機械学習モデルを、`model`フォルダに格納してください。

3. 必要なライブラリをインストールしてください。

```
pip install ccxt requests
```

4. main.pyを実行して、プログラムを開始します。



## 開発メモ
loguruを使用したlogger.pyは以下のように使用する

```
from logger import Logger

def main():
    logger = Logger("main")
    logger().info("Main function started")

if __name__ == "__main__":
    main()
```