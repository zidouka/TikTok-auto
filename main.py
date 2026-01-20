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
    """Pexelsで動画を検索する（ヒットしない場合は単語を削ってリトライ）"""
    headers = {"Authorization": api_key}
    
    # キーワードを整理：余計な記号を消し、最初の2単語程度に絞る
    clean_query = keywords.replace('[', '').replace(']', '').replace('"', '').replace("'", '').split(',')[0].strip()
    
    # 検索試行
    search_url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=1&orientation=portrait"
    
    try:
        print(f"Pexels検索中: {clean_query}")
        res = requests.get(search_url, headers=headers)
        data = res.json()
        
        if data.get('videos'):
            video_files = data['videos'][0]['video_files']
            best_video = max(video_files, key=lambda x: x.get('width', 0) or 0)
            return best_video['link']
        else:
            # ヒットしなかった場合、デフォルトの安全な単語で再試行
            print(f"キーワード '{clean_query}' で見つかりませんでした。代替検索中...")
            fallback_url = f"https://api.pexels.com/videos/search?query=nature&per_page=1&orientation=portrait"
            res = requests.get(fallback_url, headers=headers)
            data = res.json()
            if data.get('videos'):
                return data['videos'][0]['video_files'][0]['link']
                
    except Exception as e:
        print(f"Pexelsエラー: {e}")
    return "No Video Found"

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

    try:
        cell = sh.find("未処理")
    except:
        print("未処理なし")
        return

    row_num = cell.row
    topic = sh.cell(row_num, 1).value
    print(f"処理対象: {topic}")

    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    
    # プロンプトをより厳格に（キーワードは1つの単語のみに制限）
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a detailed 60-second TikTok script in Japanese.\n"
        "Task 2: Provide ONLY ONE simple English NOUN (keyword) for video search. (e.g., 'dog', 'ocean', 'city')\n"
        "Constraint: Use '###' as a separator.\n"
        "Output Format: [Script] ### [Single Keyword]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    res = requests.post(gen_url, json=payload)
    if res.status_code == 200:
        full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
        if "###" in full_text:
            script, keywords = full_text.split("###", 1)
        else:
            script, keywords = full_text, "background"

        # 動画検索
        video_url = search_pexels_videos(pexels_key, keywords.strip())

        # 書き込み
        sh.update_cell(row_num, 3, script.strip())
        sh.update_cell(row_num, 4, keywords.strip())
        sh.update_cell(row_num, 5, video_url)
        sh.update_cell(row_num, 2, "設計図完了")
        
        print(f"【完了】E列にURLを書き込みました: {video_url}")
    else:
        print(f"エラー: {res.status_code}")

if __name__ == "__main__":
    main()
