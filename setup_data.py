#!/usr/bin/env python3
"""
원본 데이터 폴더를 retest/data/ 아래로 그대로 복사하고
각 인터페이스 HTML의 비디오 경로를 ../video/<VIDEO_ID>.mp4 로 갱신합니다.
데이터 폴더 이름은 변경하지 않습니다.
"""
import os
import shutil
import json
from pathlib import Path
from fnmatch import fnmatch

# 현재 스크립트의 디렉토리
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'  # 복사된 데이터가 저장될 위치 (retest/data/)

VIDEO_DIR_CANDIDATES = [
    SCRIPT_DIR / 'video',
    SCRIPT_DIR.parent / 'video',
    Path('/source/minsunkim/comment/usertest/video')
]

DEFAULT_DATASET_COUNT = 5
SKIP_FILE_PATTERNS = ['comment_corr.json']

def resolve_video_directory():
    """비디오 파일이 위치한 디렉토리와 retest 기준 상대 경로를 반환"""
    for candidate in VIDEO_DIR_CANDIDATES:
        candidate = candidate.resolve()
        if candidate.exists():
            rel_path = os.path.relpath(candidate, SCRIPT_DIR)
            rel_path = rel_path.replace(os.sep, '/')
            if not rel_path.startswith('.'):
                rel_path = f"./{rel_path}"
            return candidate, rel_path
    return None, None

VIDEO_DIR, _VIDEO_REL_PREFIX = resolve_video_directory()

def get_source_path():
    """원본 데이터 경로를 가져옵니다"""
    # 원본 경로를 직접 지정 (config.js의 원본 경로)
    # 또는 환경변수나 사용자 입력으로 받을 수 있습니다
    original_paths = [
        '/source/minsunkim/comment/main/12_add_customization/output/1127',
        Path('/source/minsunkim/comment/main/12_add_customization/output/1127'),
    ]
    
    # 먼저 절대 경로로 시도
    for path_str in original_paths:
        if isinstance(path_str, str):
            path = Path(path_str)
        else:
            path = path_str
        
        if path.exists():
            return path
    
    # config.js에서 읽기 시도 (원본 경로가 주석에 있을 수 있음)
    config_file = SCRIPT_DIR / 'config.js'
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 주석에서 원본 경로 찾기
            import re
            # 주석에 있는 경로 패턴 찾기
            patterns = [
                r"원본[:\s]+['\"](.+?)['\"]",
                r"source[:\s]+['\"](.+?)['\"]",
                r"original[:\s]+['\"](.+?)['\"]",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    path_str = match.group(1)
                    path = Path(path_str)
                    if path.exists():
                        return path
        except Exception as e:
            print(f"config.js 읽기 오류: {e}")
    
    return None

def update_video_paths_in_html(folder_path, folder_name):
    """HTML 파일들에서 비디오 경로를 데이터 폴더 기준 상대 경로로 변경"""
    import re
    
    video_id = folder_name.split('_')[0]
    
    if not VIDEO_DIR:
        print("   ⚠️  비디오 디렉토리를 찾을 수 없습니다.")
        return
    
    video_file = VIDEO_DIR / f"{video_id}.mp4"
    if not video_file.exists():
        print(f"   ⚠️  비디오 파일이 존재하지 않습니다: {video_file}")
        return
    
    try:
        relative_video_path = os.path.relpath(video_file, folder_path)
    except ValueError:
        relative_video_path = str(video_file)
    
    video_path = relative_video_path.replace(os.sep, '/')
    
    html_files = [
        'comvi_ui_default.html',
        'youtube_ui.html',
        'youtube_ui_one.html',
        'danmaku_ui_default.html',
        'danmaku_ui_one_default.html'
    ]
    
    updated_count = 0
    
    for html_file in html_files:
        html_path = folder_path / html_file
        if not html_path.exists():
            continue
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            patterns = [
                (r'(<source\s+src=["\'])/source/minsunkim/comment/source/videos/[^"\']+\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(src=["\'])/source/[^"\']+videos/[^"\']+\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(<source\s+src=["\'])\./video/[^"\']+\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(src=["\'])\./video/[^"\']+\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(<source\s+src=["\'])\./[A-Za-z]\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(src=["\'])\./[A-Za-z]\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(src=["\'])/?video/[^"\']+\.mp4(["\'])', rf'\1{video_path}\2'),
                (r'(src=["\'])\.\./video/[^"\']+\.mp4(["\'])', rf'\1{video_path}\2')
            ]
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_count += 1
                print(f"   📹 비디오 경로 업데이트: {html_file} -> {video_path}")
        except Exception as e:
            print(f"   ⚠️  {html_file} 업데이트 실패: {e}")
    
    if updated_count > 0:
        print(f"   ✅ {updated_count}개 HTML 파일의 비디오 경로 업데이트 완료")

def remove_unwanted_files(folder_path):
    """Remove files that should not be included in the dataset."""
    if not SKIP_FILE_PATTERNS:
        return
    removed = 0
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if any(fnmatch(file_name, pattern) for pattern in SKIP_FILE_PATTERNS):
                file_path = Path(root) / file_name
                try:
                    file_path.unlink()
                    removed += 1
                    rel = file_path.relative_to(folder_path)
                    print(f"   🧾 불필요 파일 제거: {rel}")
                except FileNotFoundError:
                    continue
    if removed > 0:
        print(f"   ✅ {removed}개 파일을 제외했습니다.")

def copy_data_folders(source_path, target_dir, folder_names):
    """소스 경로의 폴더들을 타겟 디렉토리로 복사 (폴더명을 유지)"""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 기존에 남아있는 폴더 정리
    existing_dirs = {item.name for item in target_dir.iterdir() if item.is_dir()}
    for leftover in existing_dirs - set(folder_names):
        leftover_path = target_dir / leftover
        print(f"🧹 불필요한 폴더 삭제: {leftover_path}")
        shutil.rmtree(leftover_path, ignore_errors=True)
    
    copied_folders = []
    failed_folders = []
    
    for folder_name in folder_names:
        source_folder = source_path / folder_name
        target_folder = target_dir / folder_name
        
        if not source_folder.exists():
            print(f"⚠️  소스 폴더가 존재하지 않습니다: {source_folder}")
            failed_folders.append(folder_name)
            continue
        
        try:
            if target_folder.exists():
                print(f"🗑️  기존 폴더 삭제 중: {target_folder}")
                shutil.rmtree(target_folder)
            
            print(f"📁 복사 중: {source_folder} -> {target_folder}")
            if SKIP_FILE_PATTERNS:
                shutil.copytree(
                    source_folder,
                    target_folder,
                    ignore=shutil.ignore_patterns(*SKIP_FILE_PATTERNS)
                )
            else:
                shutil.copytree(source_folder, target_folder)
            
            update_video_paths_in_html(target_folder, folder_name)
            remove_unwanted_files(target_folder)
            
            copied_folders.append(folder_name)
            print(f"✅ 복사 완료: {folder_name}")
        except Exception as e:
            print(f"❌ 복사 실패 ({folder_name}): {e}")
            failed_folders.append(folder_name)
    
    return copied_folders, failed_folders

def get_folder_names_from_data_folders_json(source_path):
    """data_folders.json에서 폴더 이름 목록 가져오기 (존재 여부 확인)"""
    json_file = SCRIPT_DIR / 'data_folders.json'
    
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                folders = json.load(f)
            missing = [name for name in folders if not (source_path / name).exists()]
            if missing:
                print("⚠️  data_folders.json에 존재하지 않는 폴더가 포함되어 있습니다:")
                for name in missing:
                    print(f"   - {name}")
                return None
            return folders
        except Exception as e:
            print(f"경고: data_folders.json을 읽을 수 없습니다: {e}")
    
    return None

def detect_source_folders(source_path, limit=DEFAULT_DATASET_COUNT):
    """소스 경로에서 사용 가능한 폴더 이름을 자동으로 감지"""
    candidates = [
        item.name for item in source_path.iterdir()
        if item.is_dir() and not item.name.startswith('.')
    ]
    candidates.sort()
    if limit:
        candidates = candidates[:limit]
    return candidates

def write_data_folders_json(folder_names):
    """data_folders.json 파일을 갱신"""
    json_file = SCRIPT_DIR / 'data_folders.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(folder_names, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 60)
    print("데이터 폴더 복사 스크립트")
    print("=" * 60)
    print()
    
    # 원본 경로 가져오기
    source_path = get_source_path()
    if source_path is None:
        print("❌ 원본 데이터 경로를 찾을 수 없습니다.")
        print()
        print("해결 방법:")
        print("1. setup_data.py의 get_source_path() 함수에서 원본 경로를 직접 지정하세요")
        print("2. 또는 아래에 원본 경로를 입력하세요:")
        user_input = input("원본 경로를 입력하세요 (또는 Enter로 기본값 사용): ").strip()
        if user_input:
            source_path = Path(user_input)
        else:
            # 기본값
            source_path = Path('/source/minsunkim/comment/main/12_add_customization/output/1124')
    
    if not source_path.exists():
        print(f"❌ 소스 경로가 존재하지 않습니다: {source_path}")
        print("경로를 확인하고 다시 시도하세요.")
        return
    
    print(f"📂 소스 경로: {source_path}")
    
    if not VIDEO_DIR:
        print("⚠️  비디오 폴더를 찾을 수 없습니다. /usertest/video 에 mp4 파일이 있는지 확인하세요.")
    
    
    folder_names = get_folder_names_from_data_folders_json(source_path)
    if not folder_names:
        folder_names = detect_source_folders(source_path, DEFAULT_DATASET_COUNT)
        if not folder_names:
            print("❌ 복사할 폴더를 찾을 수 없습니다.")
            return
        write_data_folders_json(folder_names)
        print("💾 data_folders.json을 자동으로 생성했습니다.")
    
    print(f"📋 복사할 폴더: {', '.join(folder_names)}")
    print()
    
    # 사용자 확인
    response = input(f"다음 폴더들을 {DATA_DIR}로 복사하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("취소되었습니다.")
        return
    
    print()
    print("복사 시작...")
    print()
    
    # 폴더 복사
    copied, failed = copy_data_folders(source_path, DATA_DIR, folder_names)
    
    print()
    print("=" * 60)
    print("복사 결과")
    print("=" * 60)
    print(f"✅ 성공: {len(copied)}개")
    for folder_name in copied:
        print(f"   - {folder_name}")
    
    if failed:
        print(f"❌ 실패: {len(failed)}개")
        for folder in failed:
            print(f"   - {folder}")
    
    print()
    print(f"📁 복사된 데이터 위치: {DATA_DIR}")
    print()
    print("✅ 완료! 다음 단계:")
    print("1. config.js의 dataBasePath가 'data'로 설정되어 있는지 확인하세요")
    print("2. get_data_folders.py를 실행하여 data_folders.json을 업데이트하세요")
    print("3. 웹 서버를 실행하세요: python3 -m http.server 8000")
    print()
    print("💡 이미 복사된 파일의 비디오 경로만 업데이트하려면:")
    print("   update_video_paths_only() 함수를 호출하세요")

def update_video_paths_only():
    """이미 복사된 HTML 파일들의 비디오 경로만 업데이트"""
    print("=" * 60)
    print("비디오 경로 업데이트만 수행")
    print("=" * 60)
    print()
    
    data_dir = SCRIPT_DIR / 'data'
    if not data_dir.exists():
        print("❌ data 폴더가 존재하지 않습니다.")
        print("먼저 setup_data.py를 실행하여 데이터를 복사하세요.")
        return
    
    folder_paths = [p for p in data_dir.iterdir() if p.is_dir()]
    
    if not folder_paths:
        print("⚠️  업데이트할 폴더가 없습니다.")
        return
    
    updated_folders = []
    for folder_path in folder_paths:
        print(f"📁 {folder_path.name} 폴더 처리 중...")
        update_video_paths_in_html(folder_path, folder_path.name)
        remove_unwanted_files(folder_path)
        updated_folders.append(folder_path.name)
    
    print()
    print("=" * 60)
    print(f"✅ {len(updated_folders)}개 폴더의 비디오 경로 업데이트 완료")
    print("=" * 60)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--update-video-only':
        update_video_paths_only()
    else:
        main()

