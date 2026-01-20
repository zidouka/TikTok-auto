import os
import gspread
import google.auth
from google import genai
from google.genai import types

def main():
    # --- 1. スプレッドシート用の認証（Google Cloud） ---
    creds, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    gc = gspread.authorize(creds)

    try:
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"Error: シートが見つかりません: {e}")
        return

    # --- 2. Gemini用の設定（ここが重要：完全に独立させます） ---
    # APIキーを直接指定し、余計な認証情報（creds）が混ざらないようにします
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # client作成時に明示的にAPIキーのみを使う設定にします
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1'} # 強制的にv1を指定
    )

    # --- 3. 処理実行 ---
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        print(f"処理を開始します: {topic}")
        
        # モデル名はシンプルに指定
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"テーマ「{topic}」について、TikTok用の15秒台本と、動画素材を探すための英語キーワード3つを作成して。形式は「台本：〜〜 キーワード：〜〜」としてください。"
        )
        
        # 書き込み
        sh.update_cell(cell.row, 3, response.text)
        sh.update_cell(cell.row, 2, "設計図完了")
        print(f"成功: {topic} の台本を書き込みました。")
        
    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。B列を確認してください。")
        else:
            # エラーの詳細をより詳しく出力するようにします
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
