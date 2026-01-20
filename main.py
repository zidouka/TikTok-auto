import os
import gspread
import google.auth
import requests
import json

def main():
    print("--- デバッグ開始 ---")
    
    # 1. APIキーの読み込みチェック
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("致命的エラー: GEMINI_API_KEY がGitHubのSecretsから読み込めていません。")
        return
    else:
        # キーの最初の3文字だけ表示して、正しく読み込めているか確認
        print(f"APIキーを確認しました (先頭3文字): {api_key[:3]}...")

    # 2. スプレッドシート用の認証
    try:
        creds, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        gc = gspread.authorize(creds)
        sh = gc.open("TikTok管理シート").sheet1
        print("スプレッドシート接続成功。")
    except Exception as e:
        print(f"スプレッドシート接続失敗: {e}")
        return

    # 3. 処理実行
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        print(f"ターゲットネタ: {topic}")

        # --- Gemini API 通信 (もっとも原始的なURL形式) ---
        # 確実に 1.5-flash を v1 で叩きます
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": f"テーマ「{topic}」でTikTok台本と英語キーワード3つ作成して。形式は「台本：〜〜 キーワード：〜〜」"}]
            }]
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"HTTPステータス: {response.status_code}")
        
        result = response.json()

        if response.status_code == 200:
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            sh.update_cell(cell.row, 3, ai_text)
            sh.update_cell(cell.row, 2, "設計図完了")
            print(f"成功: 書き込み完了")
        else:
            # エラーの詳細をさらに詳しく表示
            print(f"詳細エラーログ: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    main()
