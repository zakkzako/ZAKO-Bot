import os
import subprocess

def create_split_zips():
    # ユーザー提供の成功例に基づいた設定
    source_dir = os.path.expanduser('~/ZAKO-Bot')
    # ダウンロードフォルダ内の特定のサブフォルダ
    target_dir = os.path.expanduser('~/storage/downloads/ZAKO_source')
    output_prefix = 'essential_files_part'
    
    # 保存先フォルダがなければ作成
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # 1. .pyファイルを収集
    py_files = []
    for root, dirs, files in os.walk(source_dir):
        if any(skip in root for skip in ['.git', 'venv', '__pycache__', 'storage']):
            continue
        for file in files:
            if file.endswith('.py') and file != 'zip.py':
                # 相対パスを取得（zipコマンドで構造を保つため）
                rel_path = os.path.relpath(os.path.join(root, file), source_dir)
                py_files.append(rel_path)

    if not py_files:
        print("Pythonファイルが見つかりませんでした。")
        return

    # 2. リストを半分に分割
    py_files.sort()
    mid = len(py_files) // 2
    parts = [py_files[:mid], py_files[mid:]]

    # 3. Termuxの zip コマンドを実行
    os.chdir(source_dir)
    for i, part in enumerate(parts, 1):
        zip_name = f"{output_prefix}{i}.zip"
        target_path = os.path.join(target_dir, zip_name)
        
        # 既存ファイルを削除
        if os.path.exists(target_path):
            os.remove(target_path)
            
        # 成功例と同じ形式のコマンドを生成
        # subprocess.run で引数を渡す際はリスト形式が安全です
        cmd = ['zip', target_path] + part
        
        print(f"📦 {zip_name} を作成中...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 成功: {target_path} (ファイル数: {len(part)})")
        else:
            print(f"❌ 失敗: {result.stderr}")

if __name__ == "__main__":
    create_split_zips()
