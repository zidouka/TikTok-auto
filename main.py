import os
import gspread
import google.auth
import requests
import json
import time

def get_best_model(api_key):
    """利用可能な最新のGeminiモデルを自動判別する"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        # 2.5-flashがあれば優先、なければリストの先頭を使う
        best = next((m for m in models if '2.5-flash' in m), models[0] if models else None)
        return best
    except:
        return "models/gemini-2.5-flash" # 失敗時のフォールバック

def main():
    print("--- 実行開始 ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # 1. スプレッドシート接続
    try:
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        gc = gspread.authorize(creds)
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"エラー: スプレッドシートに接続できません。 {e}")
        return

    # 2. 未処理行の検索
    try:
        cell = sh.find("未処理")
    except gspread.exceptions.CellNotFound:
        print("【完了】『未処理』の行が見つかりませんでした。B列を確認してください。")
        return

    # 3. データの取得
    row_num = cell.row
    topic = sh.cell(row_num, 1).value # A列
    print(f"処理対象: {topic}")

    # 4. モデルの判別と生成
    model_name = get_best_model(api_key)
    print(f"使用モデル: {model_name}")
    
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": f"テーマ「{topic}」でTikTok台本と英語キーワード3つ作成して。形式は「台本：〜〜 キーワード：〜〜」"}]}]
    }

    # 5. リトライ付き実行
    for i in range(3):
        res = requests.post(gen_url, json=payload)
        if res.status_code == 200:
            ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            # スプレッドシート更新
            sh.update_cell(row_num, 3, ai_text)      # C列：台本
            sh.update_cell(row_num, 2, "設計図完了")  # B列：ステータス
            print(f"【成功】シートを更新しました。")
            return
        elif res.status_code == 503:
            print(f"混雑中... {10*(i+1)}秒待機してリトライします。")
            time.sleep(10 * (i+1))
        else:
            print(f"エラーが発生しました({res.status_code}): {res.text}")
            break

if __name__ == "__main__":
    main()
