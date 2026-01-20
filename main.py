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
    try:
        # ※ご自身のシート名になっているか確認！
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"Error: シートが見つかりません: {e}")
        return

    # 3. Geminiの設定
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 4. 「未処理」の行を探して処理
    try:
        # B列から「未処理」という文字を探す
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        
        print(f"処理を開始します: {topic}")
        
        prompt = f"テーマ「{topic}」について、TikTok用の動画台本と、Pexels検索用英語キーワード3つを作成して。形式は「台本：〜〜 キーワード：〜〜」としてください。"
        response = model.generate_content(prompt)
        
        # 書き込み（3列目に台本、2列目を更新）
        sh.update_cell(cell.row, 3, response.text)
        sh.update_cell(cell.row, 2, "設計図完了")
        print(f"成功: {topic} の台本を作成しました。")
        
    except Exception as e:
        # エラーの内容を判定
        if "matching cell" in str(e) or "CellNotFound" in str(type(e).__name__):
            print("未処理のネタが見つかりませんでした。B列に『未処理』と入力してください。")
        else:
            print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
