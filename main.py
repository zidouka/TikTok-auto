import os
import gspread
import google.auth
import google.generativeai as genai

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

    # 3. Geminiの設定（ここが重要です！）
    api_key = os.environ.get("GEMINI_API_KEY")
    # 明示的に最新の v1 チャンネルを使うように設定します
    genai.configure(api_key=api_key, transport='rest') 
    
    # 4. 「未処理」の行を探して処理
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        
        print(f"処理を開始します: {topic}")
        
        # モデル名はシンプルに指定します
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"テーマ「{topic}」について、TikTok用の動画台本と、動画素材を探すための英語キーワード3つを作成して。形式は「台本：〜〜 キーワード：〜〜」としてください。"
        
        # 実行
        response = model.generate_content(prompt)
        
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
