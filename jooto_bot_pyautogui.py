import flask
import pyautogui
import time
import sys
import platform
import pyperclip
import tkinter as tk
import threading
import requests
import os

# PyAutoGUIの基本設定
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 1.5

# スクリプト自身の場所を基準にした画像フォルダの絶対パス
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(SCRIPT_DIR, 'images')

# ==============================================================================
# 補助関数
# ==============================================================================

def show_countdown_dialog():
    """5秒のカウントダウン付き通知ウィンドウを表示する関数（エラー対策済み修正版）"""
    root = tk.Tk()
    root.title("自動操作開始の案内")
    root.attributes("-topmost", True)
    
    # ウィンドウサイズと位置の調整（画面中央付近に見やすく表示）
    root.geometry("400x150+500+300")

    cancelled = False

    def cancel_and_close():
        nonlocal cancelled
        cancelled = True
        try:
            root.destroy()
        except tk.TclError:
            pass # すでに閉じられていてもエラーにしない

    # 「×」ボタンで閉じられたときの処理もキャンセル扱いにする
    root.protocol("WM_DELETE_WINDOW", cancel_and_close)

    label = tk.Label(root, text="", font=("Helvetica", 12), padx=20, pady=20)
    label.pack()
    
    cancel_button = tk.Button(root, text="5秒以内にクリックして自動操作を中止", command=cancel_and_close)
    cancel_button.pack(pady=10)
    
    for i in range(5, -1, -1):
        if cancelled:
            print("ユーザーによって操作がキャンセルされました。")
            return False
        
        try:
            label.config(text=f"自動操作を開始します... ({i}秒後)")
            root.update()
        except tk.TclError:
            # 途中でウィンドウが強制的に閉じられた場合
            print("ウィンドウが閉じられました。操作を中止します。")
            return False
            
        time.sleep(1)
    
    # ループ終了後にウィンドウを閉じる
    try:
        root.destroy()
    except tk.TclError:
        pass # すでに閉じられていても気にしない

    return True

def click_image(image_name, confidence=0.8, timeout=30, region=None):
    """
    指定された画像が画面に見つかるまで最大30秒待ち、見つけたらクリックする関数
    （エラー時に診断用スクリーンショットを保存する機能付き）
    """
    print(f"画像 '{image_name}' を全ディスプレイから探しています...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        locations = list(pyautogui.locateAllOnScreen(os.path.join(IMAGES_DIR, image_name), confidence=confidence, grayscale=True, region=region))
        
        if locations:
            target_location = pyautogui.center(locations[0])
            pyautogui.moveTo(target_location, duration=0.2)
            pyautogui.click()
            print(f"'{image_name}' をクリックしました。")
            return True
        
        time.sleep(1)
            
    # --- 診断機能 ---
    print("-------------------------------------------")
    print(f"診断: 画像 '{image_name}' が見つかりませんでした。診断用スクリーンショットの保存を試みます...")
    error_message = f"'{image_name}'が見つかりませんでした。"
    try:
        # スクリプトの実行場所を基準に保存
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = f'ERROR_DIAGNOSIS_{image_name.replace(".png", "")}_{time.strftime("%Y%m%d-%H%M%S")}.png'
        error_screenshot_path = os.path.join(script_dir, filename)
        pyautogui.screenshot(error_screenshot_path)
        print(f"成功: エラー発生時のスクリーンショットを保存しました: {error_screenshot_path}")
        error_message = (
            f"'{image_name}'が見つかりませんでした。\n\n"
            f"診断のため、スクリーンショットを '{error_screenshot_path}' として保存しました。\n"
            f"imagesフォルダ内の '{image_name}' と見比べて、見た目が変わっていないか確認してください。"
        )
    except Exception as e:
        print(f"失敗: スクリーンショットの保存中にエラーが発生しました: {e}")
        error_message = (
            f"'{image_name}'が見つかりませんでした。\n\n"
            f"さらに、診断用スクリーンショットの保存にも失敗しました。原因: {e}\n"
            f"スクリプトを実行しているフォルダへの「書き込み権限」があるか確認してください。"
        )
    print("-------------------------------------------")
    raise Exception(error_message)

def post_to_google_chat(title, description, jooto_url):
    """最終的なメッセージをGoogle ChatのWebhookに「カード形式」で送信する関数"""
    chat_webhook_url = os.environ.get('GOOGLE_CHAT_WEBHOOK_URL')
    if not chat_webhook_url:
        print("エラー: 環境変数 'GOOGLE_CHAT_WEBHOOK_URL' が設定されていません。")
        return
    
    # Google Chatに送信する「カード」のデータを構築
    payload = {
        "cardsV2": [
            {
                "cardId": "jootoTaskCard",
                "card": {
                    "header": {
                        "title": "新規事故報告受信",
                        "subtitle": title # *件名:* をサブタイトルに
                    },
                    "sections": [
                        {
                            "header": "内容",
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": description # *内容:* を本文に
                                    }
                                }
                            ]
                        },
                        {
                            "widgets": [
                                {
                                    "buttonList": {
                                        "buttons": [
                                            {
                                                "text": "Jootoタスクを開く",
                                                "onClick": {
                                                    "openLink": {
                                                        "url": jooto_url
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }

    try:
        response = requests.post(chat_webhook_url, json=payload)
        response.raise_for_status()
        print("Google Chatへの投稿に成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"Google Chatへの投稿に失敗しました: {e}")

# ==============================================================================
# メインの自動操作関数
# ==============================================================================

def run_automation(task_title, task_description):
    """PyAutoGUIの自動操作を実行する関数"""
    try:
        pyautogui.hotkey('win', 'd')
        time.sleep(1)
        if not show_countdown_dialog():
            return
        print("デスクトップのJOOTOショートカットを探しています...")
        locations = list(pyautogui.locateAllOnScreen(os.path.join(IMAGES_DIR, 'jooto_shortcut.png'), confidence=0.9))
        if locations:
            pyautogui.doubleClick(pyautogui.center(locations[0]), duration=0.2)
            print("ショートカットをダブルクリックしました。")
        else:
            raise Exception("'jooto_shortcut.png' が見つかりません。")
        print("Jootoウィンドウの起動を12秒間待機します...")
        time.sleep(12) 
        click_image('add_task_button.png')
        time.sleep(1) 
        print("タスク名を入力します...")
        paste_key = 'v'
        modifier_key = 'ctrl' if platform.system() == "Windows" else 'command'
        pyperclip.copy(task_title)
        pyautogui.hotkey(modifier_key, paste_key)
        click_image('advanced_settings_button.png')
        click_image('description_field.png')
        pyperclip.copy(task_description)
        pyautogui.hotkey(modifier_key, paste_key)
        pyautogui.press('enter')
        print("タスクの作成が完了しました。")
        
        # 1. URLを取得
        print("タスクURLの取得を開始します...")
        click_image('copy_url_icon.png') 
        time.sleep(1)
        jooto_url = pyperclip.paste()
        print(f"取得したJooto URL: {jooto_url}")
        
        # 2. 【先】にChatへ投稿する
        post_to_google_chat(task_title, task_description, jooto_url)
        
        # 3. 【後】でカードを閉じる
        click_image('close_card_button.png')
        
        print("全ての処理が完了しました！")
        pyautogui.alert(text='タスクの作成とGoogle Chatへの投稿が完了しました。', title='処理完了')

    except Exception as e:
        error_message = f"エラーが発生しました: {e}"
        print(error_message)
        pyautogui.alert(text=error_message, title='エラー')

# ==============================================================================
# Flaskサーバーの定義と実行
# ==============================================================================

app = flask.Flask(__name__)

@app.route('/', methods=['POST'])
def create_jooto_task():
    data = flask.request.get_json()
    task_title = data.get('title')
    task_description = data.get('description')
    print("--- GASからのリクエスト受信 ---")
    automation_thread = threading.Thread(
        target=run_automation, 
        args=(task_title, task_description)
    )
    automation_thread.start()
    print("--- 応答を即時返信し、バックグラウンド処理を開始 ---")
    return "OK, request received.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)