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
        best = next((m for m in models if '2.5-flash' in m), models[0] if models else None)
        return best
    except:
        return "models/gemini-2.5-flash"

def main():
    print("--- 実行開始 ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # 1. スプレッドシート接続
    try:
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        gc = gspread.authorize(creds)
        sh = gc.open("TikTok管理シート").sheet1
        print("スプレッドシート接続成功。")
    except Exception as e:
        print(f"エラー: スプレッドシート接続失敗: {e}")
        return

    # 2. 未処理行の検索
    try:
        cell = sh.find("未処理")
    except gspread.exceptions.CellNotFound:
        print("【完了】『未処理』の行が見つかりませんでした。")
        return

    row_num = cell.row
    topic = sh.cell(row_num, 1).value
    print(f"処理対象: {topic}")

    # 3. 英語プロンプトの作成（60秒・飽きさせない構成を指示）
    model_name = get_best_model(api_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={api_key}"
    
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a detailed TikTok script in Japanese (approx. 60 seconds).\n"
        "The script must be engaging and prevent viewer boredom by covering 2-3 interesting facts or deeper insights.\n"
        "It must include: Characters, Narration, Telop (on-screen text), and diverse Video descriptions divided by time stamps.\n"
        "Task 2: Provide 5 English image search keywords related to the theme for finding diverse video stock footage.\n"
        "Constraint: Use '###' as a separator between Task 1 and Task 2.\n"
        "Output Format:\n"
        "[Full Japanese Script]\n"
        "###\n"
        "[Keyword 1, Keyword 2, Keyword 3, Keyword 4, Keyword 5]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    # 4. 生成と書き込み
    for i in range(3):
        res = requests.post(gen_url, json=payload)
        if res.status_code == 200:
            full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            
            if "###" in full_text:
                script, keywords = full_text.split("###", 1)
            else:
                script, keywords = full_text, ""

            sh.update_cell(row_num, 3, script.strip())   # C列: 構成案付き台本
            sh.update_cell(row_num, 4, keywords.strip()) # D列: 検索キーワード
            sh.update_cell(row_num, 2, "設計図完了")      # B列: ステータス
            
            print(f"【成功】60秒構成案とキーワードの書き込みが完了しました。")
            return
        elif res.status_code == 503:
            print("混雑中... リトライします。")
            time.sleep(10)
        else:
            print(f"エラー: {res.status_code}\n{res.text}")
            break

if __name__ == "__main__":
    main()
