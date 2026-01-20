import os
import gspread
import google.auth
from google import genai
from google.genai import types # 追加

def main():
    # 1. Google Cloud 認証
    creds, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    gc = gspread.authorize(creds)

    # 2. スプレッドシートを開く
    try:
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"Error: シートが見つかりません: {e}")
        return

    # 3. Geminiの設定
    api_key = os.environ.get("GEMINI_API_KEY")
    # http_options を追加して、強制的に v1 API を使うように仕向けます
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1'} 
    )

    # 4. 「未処理」の行を探して処理
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        
        print(f"処理を開始します: {topic}")
        
        prompt = f"テーマ「{topic}」について、TikTok用の動画台本と、英語キーワード3つを作成して。"
        
        # モデル名を最新のエイリアスに変更
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest', 
            contents=prompt
        )
        
        # 書き込み
        sh.update_cell(cell.row, 3, response.text)
        sh.update_cell(cell.row, 2, "設計図完了")
        print(f"成功: {topic} の台本を作成しました。")
        
    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。")
        else:
            print(f"エラー詳細: {e}")

if __name__ == "__main__":
    main()
