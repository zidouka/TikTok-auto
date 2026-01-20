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
        # 2.5-flashがあれば優先、なければ1.5-flashなどを探す
        best = next((m for m in models if '2.5-flash' in m), models[0] if models else "models/gemini-1.5-flash")
        return best
    except:
        return "models/gemini-2.5-flash"

def search_pexels_videos(api_key, keywords):
    """Pexelsで縦型動画を検索し、高画質なURLを1つ返す"""
    headers = {"Authorization": api_key}
    # 複数のキーワードがある場合は最初の1つをクエリに使用
    query = keywords.split(',')[0].strip()
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('videos'):
            video_files = data['videos'][0]['video_files']
            # 最も解像度が高い（widthが大きい）リンクを選択
            best_video = max(video_files, key=lambda x: x.get('width', 0) or 0)
            return best_video['link']
    except Exception as e:
        print(f"Pexels検索エラー: {e}")
    return "No Video Found"

def main():
    print("--- 実行開始 ---")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pexels_key = os.environ.get("PEXELS_API_KEY")
    
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

    # 3. Geminiで詳細な台本とキーワードを生成
    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    
    # 60秒用かつ飽きさせない詳細構成を英語で指示
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a detailed TikTok script in Japanese (approx. 60 seconds).\n"
        "The script must be engaging and cover 2-3 interesting facts to prevent boredom.\n"
        "Include: Characters, Narration, Telop (on-screen text), and Video descriptions with time stamps.\n"
        "Task 2: Provide 1 simple English keyword for searching high-quality vertical video footage.\n"
        "Constraint: Use '###' as a separator between Task 1 and Task 2.\n"
        "Output Format: [Script] ### [Keyword]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # AI生成実行（リトライ付き）
    for i in range(3):
        res = requests.post(gen_url, json=payload)
        if res.status_code == 200:
            full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            if "###" in full_text:
                script, keywords = full_text.split("###", 1)
            else:
                script, keywords = full_text, "nature"

            # 4. Pexelsで動画素材を検索
            print(f"動画素材を検索中: {keywords.strip()}")
            video_url = search_pexels_videos(pexels_key, keywords.strip())

            # 5. シートに反映
            sh.update_cell(row_num, 3, script.strip())    # C列: 60秒詳細台本
            sh.update_cell(row_num, 4, keywords.strip())  # D列: 英語キーワード
            sh.update_cell(row_num, 5, video_url)         # E列: 動画URL
            sh.update_cell(row_num, 2, "設計図完了")       # B列: ステータス
            
            print(f"【成功】台本作成と素材URL(E列)の取得が完了しました！")
            return
        elif res.status_code == 503:
            print("Gemini混雑中... 10秒待機してリトライします。")
            time.sleep(10)
        else:
            print(f"Geminiエラー: {res.status_code}")
            break

if __name__ == "__main__":
    main()
