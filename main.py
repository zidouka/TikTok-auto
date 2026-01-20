import os
import gspread
import google.auth
from google import genai

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
    # バージョン指定をあえて外して、ライブラリのデフォルトに任せます
    client = genai.Client(api_key=api_key)

    # 4. 処理実行
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        print(f"処理を開始します: {topic}")
        
        # モデル名を最も標準的な 'gemini-1.5-flash' に戻します
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"TikTok用の動画台本を作って。テーマ：{topic}"
        )
        
        # 書き込み
        sh.update_cell(cell.row, 3, response.text)
        sh.update_cell(cell.row, 2, "設計図完了")
        print(f"成功: {topic} の台本を書き込みました。")
        
    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。")
        else:
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
