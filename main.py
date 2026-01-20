import os
import gspread
import google.auth
from google import genai

def main():
    print("プログラムを開始します...")

    # --- 1. スプレッドシート用の認証（Google Cloud / Workload Identity） ---
    try:
        creds, project = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        gc = gspread.authorize(creds)
        
        # スプレッドシートを開く
        # ※シート名が「TikTok管理シート」であることを確認してください
        sh = gc.open("TikTok管理シート").sheet1
        print("スプレッドシートの接続に成功しました。")
    except Exception as e:
        print(f"Error: スプレッドシートの接続に失敗しました: {e}")
        return

    # --- 2. Gemini用の設定（API Key） ---
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY が設定されていません。")
        return

    # クライアント作成（API Keyによる独立した認証）
    client = genai.Client(api_key=api_key)

    # --- 3. 処理実行 ---
    try:
        # B列から「未処理」という文字を探す
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value # A列のネタを取得
        print(f"処理を開始します: {topic}")
        
        prompt = (
            f"テーマ「{topic}」について、TikTok用の15秒程度の動画台本と、"
            f"動画素材を探すための英語キーワード3つを作成して。"
            f"形式は「台本：〜〜 キーワード：〜〜」としてください。"
        )
        
        # モデルを最もエラーの出にくい 'gemini-1.0-pro' に指定
        response = client.models.generate_content(
            model='gemini-1.0-pro',
            contents=prompt
        )
        
        # AIの回答を取得
        ai_text = response.text
        
        # スプレッドシートへの書き込み
        sh.update_cell(cell.row, 3, ai_text)      # C列に台本を書き込む
        sh.update_cell(cell.row, 2, "設計図完了")  # B列のステータスを更新
        
        print(f"成功: 「{topic}」の台本をシートに書き込みました！")
        
    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。B列に『未処理』と入力されているか確認してください。")
        else:
            print(f"実行中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
