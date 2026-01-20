import os
import gspread
import google.auth
import requests
import time
from gtts import gTTS
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

# --- 設定項目 ---
FONT_PATH = "font.ttf"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_best_model(api_key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url).json()
        models = [m['name'] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        return next((m for m in models if '2.5-flash' in m), models[0] if models else "models/gemini-1.5-flash")
    except: return "models/gemini-2.5-flash"

def search_pexels_videos(api_key, keywords):
    headers = {"Authorization": api_key}
    clean_query = keywords.replace('[', '').replace(']', '').replace('"', '').replace("'", '').split(',')[0].strip()
    url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=1&orientation=portrait"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get('videos'):
                return max(data['videos'][0]['video_files'], key=lambda x: x.get('width', 0))['link']
    except: pass
    return "https://www.pexels.com/video/853889/"

def create_video(video_url, script_text, output_name):
    print(f"🎬 動画合成開始: {output_name}")
    video_path = "temp_video.mp4"
    audio_path = "temp_audio.mp3"
    
    # 1. 素材ダウンロード
    with open(video_path, "wb") as f:
        f.write(requests.get(video_url).content)
    
    # 2. ナレーション生成
    tts = gTTS(text=script_text.replace('\n', ' '), lang='ja')
    tts.save(audio_path)
    
    # 3. 編集
    clip = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    if clip.duration < audio.duration:
        clip = clip.loop(duration=audio.duration)
    else:
        clip = clip.set_duration(audio.duration)
    clip = clip.set_audio(audio)
    
    # 4. テロップ追加 (エラー対策版)
    try:
        txt_clip = TextClip(
            script_text, 
            fontsize=40, 
            color='white', 
            font=FONT_PATH, 
            method='caption', 
            size=(clip.w * 0.8, None), 
            align='center'
        ).set_duration(clip.duration).set_position('center')
    except Exception as e:
        print(f"⚠️ テロップ生成でエラー発生。短いテキストで代替します: {e}")
        txt_clip = TextClip("Processing Video...", fontsize=50, color='white', font=FONT_PATH).set_duration(clip.duration).set_position('center')
    
    final_video = CompositeVideoClip([clip, txt_clip])
    final_path = os.path.join(OUTPUT_DIR, output_name)
    final_video.write_videofile(final_path, fps=24, codec="libx264", audio_codec="aac")
    
    # 後片付け
    clip.close()
    audio.close()
    if os.path.exists(video_path): os.remove(video_path)
    if os.path.exists(audio_path): os.remove(audio_path)
    
    return final_path

def main():
    print("--- 実行開始 ---")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pexels_key = os.environ.get("PEXELS_API_KEY")
    
    creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    gc = gspread.authorize(creds)
    sh = gc.open("TikTok管理シート").sheet1

    try:
        cell = sh.find("未処理")
        row_num = cell.row
    except:
        print("未処理の行がありません。")
        return

    topic = sh.cell(row_num, 1).value
    print(f"対象テーマ: {topic}")

    # Geminiで設計図作成
    model_name = get_best_model(gemini_key)
    gen_url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={gemini_key}"
    prompt = f"Theme: {topic}\nTask: 60s TikTok script in Japanese and 1 English noun for video search.\nOutput: [Script] ### [Keyword]"
    
    res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}]})
    if res.status_code == 200:
        full_text = res.json()['candidates'][0]['content']['parts'][0]['text']
        script, keyword = full_text.split("###") if "###" in full_text else (full_text, "nature")
        video_url = search_pexels_videos(pexels_key, keyword.strip())
        
        # 動画合成実行
        video_file_name = f"video_{row_num}.mp4"
        try:
            final_path = create_video(video_url, script.strip(), video_file_name)
            sh.update_cell(row_num, 3, script.strip())
            sh.update_cell(row_num, 5, video_url)
            sh.update_cell(row_num, 6, final_path)
            sh.update_cell(row_num, 2, "動画生成完了")
            print(f"✅ 成功: {final_path}")
        except Exception as e:
            print(f"❌ エラー: {e}")
            sh.update_cell(row_num, 2, "合成エラー")

if __name__ == "__main__":
    main()
