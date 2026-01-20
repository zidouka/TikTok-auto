import os
import gspread
import google.auth
import requests
import json
import time

def get_best_model(api_key):
    """利用可能なGeminiモデルを自動取得"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        best = next((m for m in models if '2.5-flash' in m), models[0] if models else "models/gemini-1.5-flash")
        return best
    except:
        return "models/gemini-2.5-flash"

def search_pexels_videos(api_key, keywords):
    """Pexelsで縦型動画を検索。失敗時はリトライとフォールバックを行う"""
    if not api_key:
        return "Error: PEXELS_API_KEY is missing"

    headers = {"Authorization": api_key}
    # キーワードを徹底的にクリーンアップ
    clean_query = keywords.replace('[', '').replace(']', '').replace('"', '').replace("'", '').replace('.', '').replace('\n', '').split(',')[0].strip()
    
    if not clean_query:
        clean_query = "nature"

    url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=1&orientation=portrait"
    
    try:
        print(f"Pexels検索実行中: '{clean_query}'")
        res = requests.get(url, headers=headers)
        
        if res.status_code == 200:
            data = res.json()
            if data.get('videos') and len(data['videos']) > 0:
                video_files = data['videos'][0].get('video_files', [])
                if video_files:
                    # 最も高画質なリンク（widthが最大）を選択
                    best_video = max(video_files, key=lambda x: x.get('width', 0) or 0)
                    return best_video['link']
        
        # 1次検索で見つからない場合は「cinematic」で汎用素材を検索
        print(f"キーワード '{clean_query}' で見つかりませんでした。汎用素材を検索します。")
        fallback_url = "https://api.pexels.com/videos/search?query=cinematic&per_page=1&orientation=portrait"
        f_res = requests.get(fallback_url, headers=headers)
        if f_res.status_code == 200:
            f_data = f_res.json()
            if f_data.get('videos'):
                return f_data['videos'][0]['video_files'][0]['link']
                
    except Exception as e:
        print(f"Pexels接続エラー: {e}")
    
    return "https://www.pexels.com/video/853889/" # 最終的な予備URL

def main():
    print("--- 実行開始 ---")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pexels_key = os.environ.get("PEXELS_API_KEY")
    
    # 1. スプレッドシート接続
    try:
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        gc = gspread.authorize(creds)
        sh = gc.open("TikTok管理シート").sheet1
        print("スプレッドシートに正常に接続しました。")
    except Exception as e:
        print(f"スプレッドシート接続失敗: {e}")
        return

    # 2. 未処理行の検索
    cell = None
    try:
        cell = sh.find("未処理")
    except:
        pass

    if cell is None:
        print("【完了】『未処理』の行が見つかりませんでした。")
        return

    row_num = cell.row
    topic = sh.cell(row_num, 1).value
    print(f"処理対象テーマ: {topic}")

    # 3. Gemini生成（リトライ機能付き）
    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a highly engaging 60-second TikTok script in Japanese.\n"
        "Structure: [0-5s] Hook, [5-25s] Body 1, [25-50s] Body 2 (Twist), [50-60s] Outro.\n"
        "Format: Narration, Telop, Video Descriptions.\n\n"
        "Task 2: Provide ONLY ONE simple English noun for video search (e.g., 'dog').\n"
        "Separator: Use '###' between Task 1 and Task 2.\n"
        "Output Format: [Script] ### [Keyword]"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(5):
        res = requests.post(gen_url, json=
