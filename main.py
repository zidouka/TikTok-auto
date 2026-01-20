import os
import gspread
import google.auth
import requests
import json

def main():
    print("--- 最終デバッグ開始 ---")
    
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

    # 2. 「未処理」ネタの取得
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        print(f"ターゲットネタ: {topic}")

        # --- 3. 【重要】利用可能なモデルをリストアップ ---
        list_url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        list_response = requests.get(list_url)
        models_data = list_response.json()
        
        # 使えるモデルの中から gemini を含むものを探す
        available_model = None
        if 'models' in models_data:
            for m in models_data['models']:
                # 404を避けるため、generateContentがサポートされているモデルを探す
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    # 名前を抽出 (例: models/gemini-1.5-flash)
                    available_model = m['name']
                    # もし flash があればそれを優先
                    if 'flash' in m['name']:
                        break
        
        if not available_model:
            print(f"致命的エラー: このAPIキーで利用可能なGeminiモデルが見つかりません。返却データ: {models_data}")
            return

        print(f"使用するモデル: {available_model}")

        # --- 4. 判明したモデルで台本生成 ---
        gen_url = f"https://generativelanguage.googleapis.com/v1/{available_model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": f"テーマ「{topic}」でTikTok台本と英語キーワード3つ作成して。形式は「台本：〜〜 キーワード：〜〜」"}]
            }]
        }

        response = requests.post(gen_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        result = response.json()

        if response.status_code == 200:
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            sh.update_cell(cell.row, 3, ai_text)
            sh.update_cell(cell.row, 2, "設計図完了")
            print(f"成功: {available_model} を使用して書き込み完了")
        else:
            print(f"生成エラー: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    main()
