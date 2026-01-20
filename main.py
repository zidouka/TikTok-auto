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
    """Pexelsで動画を検索する。失敗時は単語を簡略化してリトライ"""
    headers = {"Authorization": api_key}
    # 不要な記号を削除し、最初の単語を抽出
    clean_query = keywords.replace('[', '').replace(']', '').replace('"', '').replace("'", '').split(',')[0].strip()
    
    try:
        print(f"Pexels検索実行中: {clean_query}")
        url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=1&orientation=portrait"
        res = requests.get(url, headers=headers)
        data = res.json()
        
        if data.get('videos'):
            video_files = data['videos'][0]['video_files']
            # 最も高画質なリンクを取得
            best_video = max(video_files, key=lambda x: x.get('width', 0) or 0)
            return best_video['link']
        else:
            # 見つからない場合は「abstract（抽象的）」な背景動画で代替
            print("指定ワードでヒットせず。代替素材を検索します。")
            fallback_url = "https://api.pexels.com/videos/search?query=cinematic&per_page=1&orientation=portrait"
            res = requests.get(fallback_url, headers=headers)
            data = res.json()
            return data['videos'][0]['video_files'][0]['link'] if data.get('videos') else "No Video Found"
                
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
        print(f"スプレッドシート接続失敗: {e}")
        return

    try:
        cell = sh.find("未処理")
    except:
        print("処理待ちの行（未処理）が見つかりません。")
        return

    row_num = cell.row
    topic = sh.cell(row_num, 1).value
    print(f"処理対象テーマ: {topic}")

    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    
    # 【飽きさせない60秒構成】を徹底する英語指示
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a highly engaging 60-second TikTok script in Japanese.\n"
        "Structure Requirements for 60s (to prevent boredom):\n"
        "1. [0-5s] Hook: Start with a shocking fact or a question that grabs attention.\n"
        "2. [5-25s] Body 1: Explain the first interesting point with high energy.\n"
        "3. [25-50s] Body 2: Introduce a 'Did you know?' twist or a deeper insight to keep interest.\n"
        "4. [50-60s] Outro: Call to action and summary.\n"
        "Format: Must include Narration, Telop, and Video Descriptions for each segment.\n\n"
        "Task 2: Provide ONLY ONE simple English noun for video search (e.g., 'dog').\n"
        "Separator: Use '###' between Task 1 and Task 2.\n"
        "Output: [Script] ### [Keyword]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    res = requests.post(gen_url, json=payload)
    if res.status_code == 200:
        full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
        if "###" in full_text:
            script, keywords = full_text.split("###", 1)
        else:
            script, keywords = full_text, "nature"

        # 動画検索
        video_url = search_pexels_videos(pexels_key, keywords.strip())

        # スプレッドシートへ書き込み
        sh.update_cell(row_num, 3, script.strip())    # C列: 60秒台本
        sh.update_cell(row_num, 4, keywords.strip())  # D列: 単一キーワード
        sh.update_cell(row_num, 5, video_url)         # E列: 動画URL
        sh.update_cell(row_num, 2, "設計図完了")       # B列: ステータス
        
        print(f"【完了】60秒台本の作成と素材収集に成功しました。URL: {video_url}")
    else:
        print(f"Gemini APIエラー: {res.status_code}")

if __name__ == "__main__":
    main()
