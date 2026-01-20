import os
import gspread
import google.auth
import requests
import json
import time

def get_best_model(api_key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        best = next((m for m in models if '2.5-flash' in m), models[0] if models else "models/gemini-1.5-flash")
        return best
    except:
        return "models/gemini-2.5-flash"

def search_pexels_videos(api_key, keywords):
    if not api_key:
        return "Error: PEXELS_API_KEY is missing in env"
    headers = {"Authorization": api_key}
    clean_query = keywords.replace('[', '').replace(']', '').replace('"', '').replace("'", '').replace('.', '').replace('\n', '').split(',')[0].strip()
    if not clean_query: clean_query = "nature"
    url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=1&orientation=portrait"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get('videos'):
                video_files = data['videos'][0].get('video_files', [])
                if video_files:
                    best_video = max(video_files, key=lambda x: x.get('width', 0) or 0)
                    return best_video['link']
    except Exception as e:
        print(f"Pexels接続エラー: {e}")
    return "https://www.pexels.com/video/853889/" # 万が一の予備URL

def main():
    print("--- 実行開始 ---")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pexels_key = os.environ.get("PEXELS_API_KEY")
    
    try:
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        gc = gspread.authorize(creds)
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"接続失敗: {e}")
        return

    cell = None
    try:
        cell = sh.find("未処理")
    except: pass

    if cell is None:
        print("未処理の行がありません。")
        return

    row_num = cell.row
    topic = sh.cell(row_num, 1).value
    print(f"処理対象テーマ: {topic}")

    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a highly engaging 60-second TikTok script in Japanese.\n"
        "Structure: [0-5s] Hook, [5-25s] Body 1, [25-50s] Body 2 (Twist), [50-60s] Outro.\n"
        "Format: Narration, Telop, Video Descriptions.\n\n"
        "Task 2: Provide ONLY ONE simple English noun for video search (e.g., 'cat').\n"
        "Output Format: [Script] ### [Keyword]"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    # --- リトライロジック追加 ---
    success = False
    for attempt in range(5): # 最大5回試す
        res = requests.post(gen_url, json=payload)
        if res.status_code == 200:
            full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            script, keywords = full_text.split("###", 1) if "###" in full_text else (full_text, "nature")
            
            video_url = search_pexels_videos(pexels_key, keywords.strip())
            
            sh.update_cell(row_num, 3, script.strip())
            sh.update_cell(row_num, 4, keywords.strip())
            sh.update_cell(row_num, 5, video_url)
            sh.update_cell(row_num, 2, "設計図完了")
            
            print(f"【成功】{topic} の処理が完了しました！")
            success = True
            break
        elif res.status_code == 503:
            wait_time = (attempt + 1) * 10
            print(f"AIが混雑しています。{wait_time}秒後にリトライします...({attempt+1}/5)")
            time.sleep(wait_time)
        else:
            print(f"エラー: {res.status_code}")
            break
    
    if not success:
        print("時間を置いて再度実行してください。")

if __name__ == "__main__":
    main()
