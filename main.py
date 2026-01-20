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

# (get_best_model と search_pexels_videos は変更ないので省略可ですが、一応含めます)

def create_video(video_url, script_text, output_name):
    print(f"🎬 動画合成開始: {output_name}")
    video_path = "temp_video.mp4"
    audio_path = "temp_audio.mp3"
    
    with open(video_path, "wb") as f:
        f.write(requests.get(video_url).content)
    
    tts = gTTS(text=script_text.replace('\n', ' '), lang='ja')
    tts.save(audio_path)
    
    clip = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    if clip.duration < audio.duration:
        clip = clip.loop(duration=audio.duration)
    else:
        clip = clip.set_duration(audio.duration)
    clip = clip.set_audio(audio)

    # --- 改良：テロップを分割して表示する ---
    # 句点で分割して、短い文章のリストを作る
    sentences = [s.strip() for s in script_text.replace('\n', '。').split('。') if s.strip()]
    num_sentences = len(sentences)
    duration_per_sentence = clip.duration / num_sentences # 均等に時間を割り振る

    txt_clips = []
    for i, sentence in enumerate(sentences):
        try:
            t_clip = TextClip(
                sentence, 
                fontsize=60, 
                color='yellow', # 目立つように黄色に変更
                stroke_color='black', # 縁取り
                stroke_width=2,
                font=FONT_PATH, 
                method='caption', 
                size=(clip.w * 0.9, None), 
                align='center'
            ).set_start(i * duration_per_sentence).set_duration(duration_per_sentence).set_position(('center', clip.h * 0.7)) # 画面下寄りに配置
            txt_clips.append(t_clip)
        except Exception as e:
            print(f"テロップ分割エラー: {e}")

    # 背景動画の上にすべてのテロップを重ねる
    final_video = CompositeVideoClip([clip] + txt_clips)
    
    final_path = os.path.join(OUTPUT_DIR, output_name)
    final_video.write_videofile(final_path, fps=24, codec="libx264", audio_codec="aac")
    
    clip.close()
    audio.close()
    return final_path

# main関数などは以前のままでOKです
