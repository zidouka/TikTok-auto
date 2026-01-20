import os
import gspread
import google.auth
from google import genai

def main():
    # 1. Google Cloud 認証（スプレッドシート用）
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

    # 3. 新しいGeminiライブラリの設定
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # 4. 「未処理」の行を探して処理
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        
        print(f"処理を開始します: {topic}")
        
        prompt = f"テーマ「{topic}」について、TikTok用の動画台本と、動画素材を探すための英語キーワード3つを作成して。形式は「台本：〜〜 キーキーワード：〜〜」としてください。"
        
        # 最新の呼び出し方式
        response = client.models.generate_content(
            model='gemini-1.5-flash',
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
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
