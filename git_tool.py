#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import argparse
import subprocess
import filecmp
import difflib
import json
import shutil
from pathlib import Path

# --- 色の定義 ---
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"

def print_colored(text, color=Colors.WHITE, bold=False, end="\n"):
    style = color
    if bold:
        style += Colors.BOLD
    print(f"{style}{text}{Colors.RESET}", end=end)

def print_header(title):
    print("\n" + "=" * 60)
    print_colored(f"  {title}", Colors.CYAN, bold=True)
    print("=" * 60)

# --- Config ---
CONFIG_FILE = "git_tool_config.json"

def load_config():
    """設定ファイルを読み込む。なければNoneを返す"""
    # 1. カレントディレクトリ
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        # 2. スクリプトと同じディレクトリ
        script_dir = Path(__file__).parent.resolve()
        config_path = script_dir / CONFIG_FILE
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print_colored(f"設定ファイルの読み込みに失敗: {e}", Colors.RED)
    return None

def create_default_config():
    """デフォルトの設定ファイルを作成する"""
    default_config = {
        "compare": {
            "pro_dir": "/path/to/production/src",
            "dev_dir": "/path/to/development/src",
            "ignore_names": ["__pycache__", ".git", ".DS_Store", "node_modules", "venv"]
        }
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print_colored(f"設定ファイルを作成しました: {Path(CONFIG_FILE).resolve()}", Colors.GREEN)
        print("内容を編集して利用してください。")
    except Exception as e:
        print_colored(f"設定ファイルの作成に失敗: {e}", Colors.RED)


# --- Git Status Wrapper ---

def get_git_root(path=None):
    """指定されたパス（またはカレント）のGitルートディレクトリを取得"""
    cmd = ["git", "rev-parse", "--show-toplevel"]
    if path:
        cmd = ["git", "-C", str(path), "rev-parse", "--show-toplevel"]
    
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return Path(output)
    except subprocess.CalledProcessError:
        return None

def add_to_gitignore(git_root, target_rel_path):
    """対話的に.gitignoreに追記する"""
    gitignore_path = git_root / ".gitignore"
    
    print_header("無視リスト(.gitignore)への追加")
    print(f"対象ファイル: {target_rel_path}")
    print(f"設定ファイル: {gitignore_path}")
    
    # 提案オプション作成
    path_obj = Path(target_rel_path)
    options = []
    
    # 1. そのファイルそのもの
    options.append(str(target_rel_path).replace(os.sep, '/'))
    
    # 2. 拡張子で無視
    if path_obj.suffix:
        options.append(f"*{path_obj.suffix}")
        
    # 3. 親ディレクトリで無視 (ルート直下でなければ)
    parent = path_obj.parent
    if parent != Path('.'):
        options.append(f"{str(parent).replace(os.sep, '/')}/")
        
    print("\nどのように無視しますか？:")
    for i, opt in enumerate(options):
        print(f"  [{i+1}] {opt}")
    print("  [c] キャンセル")
    
    while True:
        choice = input("選択 >> ").strip().lower()
        if choice == 'c':
            return False
            
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                pattern = options[idx]
                break
                
    # 書き込み
    try:
        # 既に存在するかチェック
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                if pattern in f.read():
                    print_colored("既に.gitignoreに含まれています。", Colors.YELLOW)
                    return True
                    
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{pattern}\n")
            print_colored(f"'{pattern}' を .gitignore に追加しました。", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"書き込みエラー: {e}", Colors.RED)
        return False

def get_git_status():
    """git status --porcelain の結果を取得してパースする"""
    git_root = get_git_root()
    if not git_root:
        print_colored("エラー: ここはGitリポジトリではないようです。", Colors.RED)
        return None

    try:
        output = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.STDOUT).decode("utf-8")
    except subprocess.CalledProcessError as e:
        print_colored(f"git statusの実行に失敗しました: {e.output.decode()}", Colors.RED)
        return None

    changes = []
    for line in output.splitlines():
        if not line: continue
        status_code = line[:2]
        filepath = line[3:]
        changes.append({"status": status_code, "path": filepath})
    return changes

def show_git_diff(filepath):
    """指定されたファイルのgit diffを表示する"""
    print_header(f"変更内容: {filepath}")
    try:
        # 色付きでdiffを表示
        subprocess.run(["git", "diff", "--color", filepath])
    except Exception as e:
        print_colored(f"diffの表示に失敗しました: {e}", Colors.RED)

def run_status_check():
    changes = get_git_status()
    if changes is None:
        return
    
    if not changes:
        print_header("Git ステータス確認")
        print_colored("変更されたファイルはありません。Cleanな状態です！", Colors.GREEN, bold=True)
        return

    width = len(str(len(changes)))

    def print_menu(message=None):
        # 画面をクリア (Windows/Mac/Linux対応)
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("Git ステータス確認")
        
        if message:
            print_colored(message, Colors.RED, bold=True)
            print("-" * 60)

        print_colored(f"合計 {len(changes)} 個のファイルに変更があります:\n", Colors.YELLOW)

        # 変更一覧を表示
        for i, item in enumerate(changes):
            stat = item['status']
            path = item['path']
            
            # ステータスの日本語化と色付け
            status_str = stat
            color = Colors.WHITE
            desc = ""
            
            if 'M' in stat:
                color = Colors.YELLOW
                desc = "変更 (Modified)"
            elif 'A' in stat:
                color = Colors.GREEN
                desc = "追加 (Added)"
            elif 'D' in stat:
                color = Colors.RED
                desc = "削除 (Deleted)"
            elif '??' in stat:
                color = Colors.BLUE
                desc = "未追跡 (Untracked)"
                
            print(f"[{i+1:>{width}}] ", end="")
            print_colored(f"{stat:2} : {path}", color, bold=True, end="")
            print(f"  <= {desc}")

        print("\n" + "-" * 60)
        print("操作を選択してください:")
        print("  [番号]   : そのファイルの差分(diff)を見る")
        print("  [i 番号] : そのファイルを .gitignore に追加する")
        print("  [q]      : 終了")
        print("  [enter]  : 画面クリア＆リスト再表示")

    # 初回表示
    print_menu()

    while True:
        try:
            choice = input("\nどうしますか？ >> ").strip()
        except KeyboardInterrupt:
            print("\n終了します。")
            break

        if choice.lower() == 'q':
            break
        
        # Enterのみ -> 再描画
        if choice == '':
            print_menu()
            continue
        
        # ignore コマンドの処理 (i 1, i1 など)
        if choice.lower().startswith('i'):
            try:
                target_idx_str = choice[1:].strip()
                if not target_idx_str:
                    print_menu("番号を指定してください (例: i 1)")
                    continue
                    
                idx = int(target_idx_str) - 1
                if 0 <= idx < len(changes):
                    target_file = changes[idx]['path']
                    # Gitルート取得
                    git_root = get_git_root()
                    if git_root and add_to_gitignore(git_root, target_file):
                        # 成功したらリストを更新して再表示
                        input("\n続行するにはEnterを押してください...")
                        # 変更を反映するために再取得
                        changes = get_git_status() or [] 
                        print_menu("無視リストを更新しました。")
                    else:
                        print_menu("キャンセルしました。")
                else:
                    print_menu("無効な番号です。")
            except ValueError:
                print_menu("無効な入力です。")
            continue

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(changes):
                target_file = changes[idx]['path']
                # Untrackedの場合はdiffが出ないので中身を表示
                if '??' in changes[idx]['status']:
                    print_header(f"新規ファイルの中身: {target_file}")
                    try:
                        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
                            print(f.read())
                    except Exception as e:
                        print_colored(f"読み込み失敗: {e}", Colors.RED)
                else:
                    show_git_diff(target_file)
                # Diff表示後はリストを再表示せず、そのままプロンプト待ちにする（Diffを見たいから）
            else:
                print_menu("無効な番号です。")
        else:
            print_menu("無効な入力です。")

# --- Directory Compare Tool ---

def get_all_files(directory, ignore_names=None):
    """ディレクトリ以下の全ファイルを再帰的に取得（相対パス）
    gitリポジトリの場合は .gitignore や .git/info/exclude を考慮する
    ignore_names: 無視するファイル/ディレクトリ名のリスト
    """
    file_list = set()
    root_path = Path(directory)
    if not root_path.exists():
        return file_list

    if ignore_names is None:
        ignore_names = []
        
    # 方法1: git ls-files を試みる
    try:
        # --cached: 管理済ファイル
        # --others: 未追跡ファイル
        # --exclude-standard: .gitignore, .git/info/exclude, global config 等のルール適用
        cmd = ["git", "-C", str(root_path), "ls-files", "--cached", "--others", "--exclude-standard"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8')
        
        for line in output.splitlines():
            filepath = line.strip()
            if not filepath: continue
            
            # ignore_names によるフィルタリング
            path_parts = Path(filepath).parts
            if any(name in path_parts for name in ignore_names):
                continue
                
            file_list.add(filepath)
        
        return file_list
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Gitリポジトリでない場合やgitコマンドがない場合はフォールバック
        pass

    # 方法2: 従来のrglob + 簡易フィルタ
    for p in root_path.rglob('*'):
        if p.is_file():
            # 部分パスを取得してチェック
            rel_path_obj = p.relative_to(root_path)
            parts = rel_path_obj.parts
            
            # 基本的な除外
            if '.git' in parts or '__pycache__' in parts:
                continue
            if p.name == '.DS_Store':
                continue
            
            # ignore_names によるフィルタリング
            if any(name in parts for name in ignore_names):
                continue
                
            file_list.add(str(rel_path_obj))
            
    return file_list

def show_file_diff(file_pro, file_dev):
    """2つのファイルの差分を表示"""
    print_header(f"ファイル差分比較")
    print(f"PRO (基準): {file_pro}")
    print(f"DEV (比較): {file_dev}")
    
    try:
        with open(file_pro, 'r', encoding='utf-8', errors='ignore') as f1, \
             open(file_dev, 'r', encoding='utf-8', errors='ignore') as f2:
            f1_lines = f1.readlines()
            f2_lines = f2.readlines()
            
        diff = difflib.unified_diff(
            f1_lines, f2_lines,
            fromfile='PRO', tofile='DEV',
            lineterm=''
        )
        
        # diffを見やすく表示
        has_diff = False
        for line in diff:
            has_diff = True
            if line.startswith('+'):
                print_colored(line, Colors.GREEN, end='')
            elif line.startswith('-'):
                print_colored(line, Colors.RED, end='')
            elif line.startswith('@'):
                print_colored(line, Colors.CYAN, end='')
            else:
                print(line, end='')
        
        if not has_diff:
            print_colored("※ 差分はありません（バイナリ等の可能性あり）", Colors.YELLOW)
            
    except Exception as e:
        print_colored(f"比較中にエラーが発生しました: {e}", Colors.RED)

def run_compare(pro_dir, dev_dir, ignore_names=None):
    if ignore_names is None:
        ignore_names = []
        
    pro_path = Path(pro_dir)
    dev_path = Path(dev_dir)
    
    if not pro_path.exists():
        print_colored(f"エラー: PROディレクトリが見つかりません: {pro_dir}", Colors.RED)
        return
    if not dev_path.exists():
        print_colored(f"エラー: DEVディレクトリが見つかりません: {dev_dir}", Colors.RED)
        return

    print_colored("ファイルをスキャン中...", Colors.CYAN)
    if ignore_names:
        print(f"無視する名前: {', '.join(ignore_names)}")
        
    pro_files = get_all_files(pro_path, ignore_names)
    dev_files = get_all_files(dev_path, ignore_names)
    
    all_files = sorted(list(pro_files | dev_files))
    
    common_files = []
    only_pro = []
    only_dev = []
    diff_files = []

    for f in all_files:
        in_pro = f in pro_files
        in_dev = f in dev_files
        
        if in_pro and in_dev:
            # 中身を比較
            if not filecmp.cmp(pro_path / f, dev_path / f, shallow=False):
                diff_files.append(f)
            else:
                common_files.append(f)
        elif in_pro:
            only_pro.append(f)
        elif in_dev:
            only_dev.append(f)

    # --- サマリー表示 ---
    
    target_list = []
    # 表示用リストを作成 (ラベル, ファイルパス, 色, タイプ)
    # 事前にリストを作成しておく
    if diff_files:
        for f in diff_files:
            target_list.append(('diff', f, Colors.RED, "MODIFIED"))
    if only_dev:
        for f in only_dev:
            target_list.append(('dev_only', f, Colors.CYAN, "DEV ONLY"))
    if only_pro:
        for f in only_pro:
            target_list.append(('pro_only', f, Colors.YELLOW, "PRO ONLY"))

    total_count = len(target_list)
    width = len(str(total_count)) if total_count > 0 else 1

    def print_menu(message=None):
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("ディレクトリ比較ツール")
        print_colored(f"PRO (Main/Stable) : {pro_dir}", Colors.CYAN)
        print_colored(f"DEV (Develop)     : {dev_dir}", Colors.MAGENTA)
        
        if message:
            print_colored(message, Colors.RED, bold=True)
            print("-" * 60)

        print_colored(f"一致したファイル : {len(common_files)}", Colors.GREEN)
        print_colored(f"PROのみにある    : {len(only_pro)}", Colors.BLUE)
        print_colored(f"DEVのみにある    : {len(only_dev)}", Colors.BLUE)
        print_colored(f"内容が異なる     : {len(diff_files)}", Colors.RED, bold=True)

        if not target_list:
            print_colored("\n対応が必要な差異は見つかりませんでした！", Colors.GREEN, bold=True)
            return

        print("\n--- 差異のあるファイル一覧 ---")
        for i, (type_, f, color, label) in enumerate(target_list):
            print(f"[{i+1:>{width}}] ", end="")
            print_colored(f"{label:8} : {f}", color)

        print("\n" + "-" * 60)
        print("操作を選択してください:")
        print("  [番号]   : ファイルの差分/中身を見る")
        print("  [i 番号] : DEV側の .gitignore に追加する")
        print("  [q]      : 終了")
        print("  [enter]  : 画面クリア＆リスト再表示")

    print_menu()
    
    if not target_list:
        return

    while True:
        try:
            choice = input("\nどうしますか？ >> ").strip()
        except KeyboardInterrupt:
            break

        if choice.lower() == 'q':
            break
        
        # Enterのみ -> 再描画
        if choice == '':
            print_menu()
            continue
        
        # ignore コマンドの処理 (i 1, i1 など)
        if choice.lower().startswith('i'):
            try:
                target_idx_str = choice[1:].strip()
                if not target_idx_str:
                    print_menu("番号を指定してください (例: i 1)")
                    continue
                    
                idx = int(target_idx_str) - 1
                if 0 <= idx < len(target_list):
                    _, filepath, _, _ = target_list[idx]
                    # DEV側のGitルート取得を試みる
                    git_root = get_git_root(dev_path)
                    if git_root:
                        if add_to_gitignore(git_root, filepath):
                            input("\n続行するにはEnterを押してください...")
                            # 再スキャン
                            print("\n変更を反映するために再スキャンします...")
                            run_compare(pro_dir, dev_dir, ignore_names)
                            return 
                        else:
                            print_menu("キャンセルしました。")
                    else:
                        print_menu("DEVディレクトリはGitリポジトリではないようです。")
                else:
                    print_menu("無効な番号です。")
            except ValueError:
                print_menu("無効な入力です。")
            continue
            
        if choice.isdigit():
            sel_idx = int(choice) - 1
            if 0 <= sel_idx < len(target_list):
                type_, filepath, _, _ = target_list[sel_idx]
                
                if type_ == 'diff':
                    show_file_diff(pro_path / filepath, dev_path / filepath)
                elif type_ == 'dev_only':
                    print_header(f"DEVファイルのプレビュー: {filepath}")
                    try:
                        with open(dev_path / filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            print(f.read())
                    except:
                        print("表示できません(バイナリ等)")
                elif type_ == 'pro_only':
                    print_header(f"PROファイルのプレビュー: {filepath}")
                    try:
                        with open(pro_path / filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            print(f.read())
                    except:
                        print("表示できません")
            else:
                print_menu("無効な番号です。")
        else:
            print_menu("無効な入力です。")

def main():
    parser = argparse.ArgumentParser(description='Gitワークフロー支援ツール')
    subparsers = parser.add_subparsers(dest='command', help='サブコマンド')

    # init command
    parser_init = subparsers.add_parser('init', help='設定ファイル(git_tool_config.json)を作成します')

    # check command
    parser_check = subparsers.add_parser('check', help='現在のディレクトリのGit変更を確認します')

    # compare command
    parser_compare = subparsers.add_parser('compare', help='2つのディレクトリを比較します')
    parser_compare.add_argument('--pro', help='PRO(Stable)ディレクトリのパス (設定ファイルで指定可能)')
    parser_compare.add_argument('--dev', help='DEV(Development)ディレクトリのパス (設定ファイルで指定可能)')

    args = parser.parse_args()

    if args.command == 'init':
        create_default_config()
    
    elif args.command == 'check':
        run_status_check()
        
    elif args.command == 'compare':
        pro_dir = args.pro
        dev_dir = args.dev
        ignore_names = []

        # 設定ファイル読み込み
        config = load_config()
        if config and 'compare' in config:
            # 引数がなければ設定ファイルから使用
            if not pro_dir:
                pro_dir = config['compare'].get('pro_dir')
            if not dev_dir:
                dev_dir = config['compare'].get('dev_dir')
            
            # 設定ファイルのignoreリストを追加
            if 'ignore_names' in config['compare']:
                ignore_names.extend(config['compare']['ignore_names'])

        if not pro_dir or not dev_dir:
            print_colored("PROディレクトリまたはDEVディレクトリが指定されていません。", Colors.RED)
            print("引数(--pro, --dev)で指定するか、'init'コマンドで設定ファイルを作成してください。")
            return

        run_compare(pro_dir, dev_dir, ignore_names)
        
    else:
        # デフォルトでhelpを表示
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n終了します。")
