import os
import gspread
import google.auth
import requests
import json

def main():
    print("プログラムを開始します（直接通信モード）...")

    # --- 1. スプレッドシート用の認証（Google Cloud） ---
    try:
        creds, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        gc = gspread.authorize(creds)
        # スプレッドシート名が正しいか確認してください
        sh = gc.open("TikTok管理シート").sheet1
        print("スプレッドシートの接続に成功しました。")
    except Exception as e:
        print(f"Error: スプレッドシート接続失敗: {e}")
        return

    # --- 2. APIキーの取得 ---
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY が設定されていません。")
        return

    # --- 3. スプレッドシートからネタを取得 ---
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        print(f"処理を開始します: {topic}")

        # --- 4. Gemini API へ直接リクエスト ---
        # 住所を「v1」に完全固定し、モデルも「gemini-1.5-flash」を指定
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": f"テーマ「{topic}」について、TikTok用の15秒台本と、動画素材検索用の英語キーワード3つを作成して。形式は「台本：〜〜 キーワード：〜〜」としてください。"}]
            }]
        }

        # APIを叩く
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        result = response.json()

        if response.status_code == 200:
            # AIの回答を抽出
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # C列に回答を書き込み、B列を更新
            sh.update_cell(cell.row, 3, ai_text)
            sh.update_cell(cell.row, 2, "設計図完了")
            print(f"成功: 「{topic}」の台本を書き込みました！")
        else:
            print(f"Gemini API エラー発生: {response.status_code}")
            print(f"詳細: {json.dumps(result, indent=2)}")

    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。B列に『未処理』と入力してください。")
        else:
            print(f"実行中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
