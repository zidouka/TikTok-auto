import os
import gspread
import google.auth
import google.generativeai as genai

def main():
    # 1. Google Cloud 認証
    creds, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    gc = gspread.authorize(creds)

    # 2. スプレッドシートを開く
    # ※実際のシート名に書き換えてください
    try:
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"Error: シートが見つかりません。共有設定を確認してください: {e}")
        return

    # 3. Geminiの設定
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 4. 「未処理」の行を探して処理
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value # A列のネタを取得
        
        prompt = f"テーマ「{topic}」について、TikTok用の動画台本と、Pexels検索用英語キーワード3つを作成して。形式は「台本：〜〜 キーワード：〜〜」としてください。"
        response = model.generate_content(prompt)
        
        sh.update_cell(cell.row, 3, response.text) # C列に書き込み
        sh.update_cell(cell.row, 2, "設計図完了") # B列のステータス更新
        print(f"成功: {topic} の台本を作成しました。")
    except gspread.exceptions.CellNotFound:
        print("未処理のネタが見つかりませんでした。スプレッドシートのB列に『未処理』と入力してください。")

if __name__ == "__main__":
    main()
