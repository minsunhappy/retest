#!/usr/bin/env python3
"""
config.js의 dataBasePath에 지정된 경로 내의 하위 폴더 목록을 JSON 파일로 생성하는 스크립트
이 스크립트를 실행하면 data_folders.json 파일이 생성됩니다.
config.js의 dataBasePath를 자동으로 읽어옵니다.
"""
import os
import json
import re
from pathlib import Path

# 현재 스크립트의 디렉토리
SCRIPT_DIR = Path(__file__).parent

def get_data_base_path_from_config():
    """config.js에서 dataBasePath를 읽어옵니다"""
    config_file = SCRIPT_DIR / 'config.js'
    
    if not config_file.exists():
        print(f"경고: {config_file} 파일이 존재하지 않습니다.")
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # dataBasePath: '경로' 또는 dataBasePath: "경로" 패턴 찾기
        match = re.search(r"dataBasePath:\s*['\"](.+?)['\"]", content)
        if match:
            path_str = match.group(1)
            # 절대 경로인지 확인
            if os.path.isabs(path_str):
                return Path(path_str)
            else:
                # 상대 경로인 경우 스크립트 디렉토리 기준으로 변환
                return SCRIPT_DIR / path_str
        else:
            print("경고: config.js에서 dataBasePath를 찾을 수 없습니다.")
            return None
    except Exception as e:
        print(f"오류: config.js를 읽는 중 문제가 발생했습니다: {e}")
        return None

# data 폴더 경로 (config.js에서 자동으로 읽어옴)
DATA_BASE_PATH = get_data_base_path_from_config() 

def get_data_folders():
    """dataBasePath에 지정된 경로 내의 하위 폴더 목록을 반환"""
    if DATA_BASE_PATH is None:
        print("오류: dataBasePath를 찾을 수 없습니다.")
        print("config.js 파일에서 dataBasePath를 확인하세요.")
        return []
    
    if not DATA_BASE_PATH.exists():
        print(f"경고: {DATA_BASE_PATH} 폴더가 존재하지 않습니다.")
        print("config.js의 dataBasePath 경로를 확인하세요.")
        return []
    
    # 하위 폴더만 필터링 (파일 제외)
    folders = [
        item.name for item in DATA_BASE_PATH.iterdir()
        if item.is_dir() and not item.name.startswith('.')
    ]
    
    # 정렬
    folders.sort()
    
    return folders

def main():
    if DATA_BASE_PATH is None:
        print("오류: dataBasePath를 찾을 수 없습니다.")
        return
    
    print(f"📂 dataBasePath 경로: {DATA_BASE_PATH}")
    print()
    
    folders = get_data_folders()
    
    if not folders:
        print("경고: 지정된 경로에 하위 폴더가 없습니다.")
        print(f"경로: {DATA_BASE_PATH}")
        return
    
    # JSON 파일로 저장
    output_file = SCRIPT_DIR / 'data_folders.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(folders, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(folders)}개의 폴더를 찾았습니다:")
    for folder in folders:
        print(f"  - {folder}")
    print(f"\n📄 결과가 {output_file}에 저장되었습니다.")

if __name__ == '__main__':
    main()

