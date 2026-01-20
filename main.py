import os
import gspread
import google.auth
import requests
import json
import time # リトライ用に待機時間を設けるため追加

def main():
    print("--- 最終接続フェーズ ---")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # 1. スプレッドシート用の認証
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

    # 2. ネタの取得
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        print(f"ターゲットネタ: {topic}")

        # --- 3. 2026年最新モデルへのリクエスト ---
        # 503エラー対策として最大3回リトライします
        for i in range(3):
            print(f"台本生成中... (試行 {i+1}回目)")
            
            # ログで確認された最新モデルを直接指定
            gen_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": f"テーマ「{topic}」でTikTok台本と英語キーワード3つ作成して。形式は「台本：〜〜 キーワード：〜〜」"}]
                }]
            }

            response = requests.post(gen_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
            
            if response.status_code == 200:
                result = response.json()
                ai_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # スプレッドシート書き込み
                sh.update_cell(cell.row, 3, ai_text)
                sh.update_cell(cell.row, 2, "設計図完了")
                print(f"祝・大成功! 「{topic}」の書き込みが完了しました。")
                return # 成功したので終了

            elif response.status_code == 503:
                print("サーバー混雑中 (503)。10秒待機してリトライします...")
                time.sleep(10) # 10秒待つ
            else:
                print(f"エラーが発生しました: {response.status_code}")
                print(response.text)
                break

    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。")
        else:
            print(f"実行中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
