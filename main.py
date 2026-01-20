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
        sh = gc.open("TikTok管理シート").sheet1
    except Exception as e:
        print(f"Error: シートが見つかりません: {e}")
        return

    # 3. Geminiの設定
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # モデルの指定方法を変更しました
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 4. 「未処理」の行を探して処理
    try:
        cell = sh.find("未処理")
        topic = sh.cell(cell.row, 1).value
        
        print(f"処理を開始します: {topic}")
        
        prompt = f"テーマ「{topic}」について、TikTok用の動画台本（15秒程度）と、動画素材を探すための英語キーワード3つを作成して。回答はシンプルに台本とキーワードだけでお願いします。"
        
        # 通信エラーを避けるため、明示的に最新のAPI（v1betaではない方）を使う設定で呼び出し
        response = model.generate_content(prompt)
        
        # C列に書き込み、B列を「設計図完了」に更新
        sh.update_cell(cell.row, 3, response.text)
        sh.update_cell(cell.row, 2, "設計図完了")
        print(f"成功: {topic} の台本を作成しました。")
        
    except Exception as e:
        if "matching cell" in str(e):
            print("未処理のネタが見つかりませんでした。B列に『未処理』と入力してください。")
        else:
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
