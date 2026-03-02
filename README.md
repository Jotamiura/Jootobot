# Jootobot

GAS（Google Apps Script）からのリクエストを受け取り、PyAutoGUIでJootoにタスクを自動作成し、Google Chatに通知するBotです。

## 処理の流れ

1. Flaskサーバー（ポート5000）がGASからPOSTリクエストを受信
2. デスクトップ上のJootoアプリを画像認識で自動操作し、タスクを作成
3. 作成したタスクのURLを取得
4. Google Chat Webhookにカード形式で通知を送信

## セットアップ

### 1. 必要なライブラリをインストール

```bash
pip install flask pyautogui pyperclip requests
```

### 2. 環境変数を設定

Google Chat Webhook URLを環境変数に設定してください。

```bash
# .env.example をコピーして .env を作成
cp .env.example .env
```

`.env` を編集し、実際のWebhook URLを設定します。

```
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/XXXXX/messages?key=XXXXX&token=XXXXX
```

OS側で環境変数を直接設定する場合：

```bash
# Linux / macOS
export GOOGLE_CHAT_WEBHOOK_URL="実際のURL"

# Windows (PowerShell)
$env:GOOGLE_CHAT_WEBHOOK_URL="実際のURL"
```

### 3. 画像ファイルの確認

`images/` フォルダに、Jooto画面のUI要素のスクリーンショットが格納されています。Jootoの画面表示が変わった場合は、画像を撮り直してください。

| ファイル名 | 用途 |
|---|---|
| `jooto_shortcut.png` | デスクトップのJootoショートカット |
| `add_task_button.png` | タスク追加ボタン |
| `advanced_settings_button.png` | 詳細設定ボタン |
| `description_field.png` | 説明入力欄 |
| `copy_url_icon.png` | URLコピーアイコン |
| `close_card_button.png` | カード閉じるボタン |

## 実行

```bash
python jooto_bot_pyautogui.py
```

サーバーが `http://0.0.0.0:5000` で起動します。

## リクエスト形式

GASから以下のJSON形式でPOSTリクエストを送信してください。

```json
{
  "title": "タスクの件名",
  "description": "タスクの内容"
}
```

## 注意事項

- 実行中はマウス・キーボードの操作を避けてください（PyAutoGUIが画面を操作します）
- 緊急停止：マウスを画面の左上隅に素早く移動するとフェイルセーフが作動します
- 自動操作開始前に5秒間のカウントダウンが表示され、キャンセルできます
- 画像が見つからない場合、診断用スクリーンショットが自動保存されます
