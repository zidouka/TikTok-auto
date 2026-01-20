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
    """Pexelsで動画を検索し、詳細なエラーログを出力する"""
    if not api_key:
        return "Error: PEXELS_API_KEY is missing"

    headers = {"Authorization": api_key}
    # キーワードから余計な文字（改行、カッコ、ドットなど）を徹底排除
    clean_query = keywords.replace('[', '').replace(']', '').replace('"', '').replace("'", '').replace('.', '').replace('\n', '').split(',')[0].strip()
    
    if not clean_query:
        clean_query = "nature"

    url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=1&orientation=portrait"
    
    try:
        print(f"Pexels検索実行中: '{clean_query}'")
        res = requests.get(url, headers=headers)
        
        # 認証エラーなどのチェック
        if res.status_code != 200:
            print(f"Pexels API警告: ステータスコード {res.status_code}")
            print(f"レスポンス内容: {res.text}")
            return f"Error: {res.status_code}"

        data = res.json()
        
        if data.get('videos') and len(data['videos']) > 0:
            video_files = data['videos'][0].get('video_files', [])
            if video_files:
                # HD以上のサイズを優先して取得
                best_video = max(video_files, key=lambda x: x.get('width', 0) or 0)
                return best_video['link']
        
        # ヒットしなかった場合の予備検索
        print(f"'{clean_query}' で動画が見つかりませんでした。代替素材 'cinematic' で検索します。")
        fallback_url = "https://api.pexels.com/videos/search?query=cinematic&per_page=1&orientation=portrait"
        f_res = requests.get(fallback_url, headers=headers)
        f_data = f_res.json()
        if f_data.get('videos'):
            return f_data['videos'][0]['video_files'][0]['link']
            
    except Exception as e:
        print(f"Pexels接続中に例外発生: {e}")
    
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
        print("スプレッドシートに正常に接続しました。")
    except Exception as e:
        print(f"スプレッドシート接続失敗: {e}")
        return

    # 2. 未処理行の検索
    try:
        cell = sh.find("未処理")
        row_num = cell.row
    except gspread.exceptions.CellNotFound:
        print("【注意】B列に『未処理』というセルが見つかりませんでした。")
        return
    except Exception as e:
        print(f"検索エラー: {e}")
        return

    topic = sh.cell(row_num, 1).value
    print(f"処理対象テーマ: {topic}")

    # 3. Gemini生成（飽きさせない60秒構成）
    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    
    prompt = (
        f"Theme: {topic}\n"
        "Task 1: Create a highly engaging 60-second TikTok script in Japanese.\n"
        "Structure: [0-5s] Hook, [5-25s] Body 1, [25-50s] Body 2 (Twist), [50-60s] Outro.\n"
        "Format: Must include Narration, Telop, and Video Descriptions for each segment.\n\n"
        "Task 2: Provide ONLY ONE simple English noun for video search (e.g., 'cat', 'ocean').\n"
        "Constraint: Output only the noun itself after '###'.\n"
        "Separator: Use '###' between Task 1 and Task 2.\n"
        "Output Format: [Script] ### [Keyword]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    res = requests.post(gen_url, json=payload)
    if res.status_code == 200:
        full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
        
        if "###" in full_text:
            parts = full_text.split("###")
            script = parts[0].strip()
            keywords = parts[1].strip()
        else:
            script = full_text.strip()
            keywords = "nature"

        # 4. 動画検索
        video_url = search_pexels_videos(pexels_key, keywords)

        # 5. 書き込み
        sh.update_cell(row_num, 3, script)    # C列: 60秒台本
        sh.update_cell(row_num, 4, keywords)  # D列: キーワード
        sh.update_cell(row_num, 5, video_url) # E列: 動画URL
        sh.update_cell(row_num, 2, "設計図完了") # B列: ステータス
        
        print(f"【成功】行番号 {row_num} の処理が完了しました！")
        print(f"使用キーワード: {keywords}")
        print(f"取得URL: {video_url}")
    else:
        print(f"Geminiエラー: {res.status_code} - {res.text}")

if __name__ == "__main__":
    main()
