// 인터페이스와 데이터 매핑 설정
const CONFIG = {
    // 인터페이스 타입과 HTML 파일 매핑
    interfaces: {
        'C': 'comvi_ui_default.html',
        'Y': 'youtube_ui.html',
        'Y1': 'youtube_ui_one.html',
        'D': 'danmaku_ui_default.html',
        'D1': 'danmaku_ui_one_default.html'
    },
    
    // 데이터 폴더 경로 (사용자가 지정할 위치)
    // ⚠️ setup_data.py를 실행하여 데이터를 복사한 후 'data'로 설정하세요!
    // setup_data.py를 실행하면 원본 경로의 폴더들이 retest/data/ 아래로 복사됩니다
    dataBasePath: 'data',  // setup_data.py 실행 후 이 값으로 변경하세요
    
    // 데이터 폴더 이름 (dataBasePath 바로 아래의 폴더들)
    // null이면 data_folders.json 파일에서 자동으로 로드됩니다
    // 수동으로 설정하려면 배열을 지정하세요: ['folder1', 'folder2', ...]
    dataFolders: null,  // null이면 data_folders.json에서 자동 로드
    
    // 인터페이스 개수
    numInterfaces: 5,
    
    // 데이터 개수 (dataBasePath 바로 아래의 폴더 개수)
    numData: 5
};

// data_folders.json에서 폴더 목록 로드
async function loadDataFolders() {
    // 이미 설정되어 있으면 그대로 사용
    if (CONFIG.dataFolders && Array.isArray(CONFIG.dataFolders)) {
        return CONFIG.dataFolders;
    }
    
    // data_folders.json 파일에서 로드 시도
    try {
        const response = await fetch('data_folders.json');
        if (response.ok) {
            const folders = await response.json();
            if (Array.isArray(folders) && folders.length > 0) {
                return folders;
            }
        }
    } catch (error) {
        console.warn('data_folders.json을 불러올 수 없습니다:', error);
    }
    
    // 기본값 반환 (폴백)
    console.warn('기본 폴더 목록을 사용합니다. get_data_folders.py를 실행하여 data_folders.json을 생성하세요.');
    return ['A', 'B', 'C', 'D', 'E'];
}

// 인터페이스-데이터 쌍 생성 함수
// 모든 인터페이스를 경험하고, 데이터는 중복되지 않도록 함
async function generateInterfaceDataPairs() {
    const interfaces = ['C', 'Y', 'Y1', 'D', 'D1'];
    
    // 데이터 폴더 이름 로드
    const dataFolders = await loadDataFolders();
    
    if (dataFolders.length < interfaces.length) {
        console.error(`오류: 데이터 폴더가 ${interfaces.length}개 이상 필요합니다. (현재: ${dataFolders.length}개)`);
        throw new Error('데이터 폴더가 부족합니다.');
    }
    
    // 인터페이스를 랜덤하게 섞기
    const shuffledInterfaces = [...interfaces].sort(() => Math.random() - 0.5);
    
    // 데이터를 랜덤하게 섞기
    const shuffledData = [...dataFolders].sort(() => Math.random() - 0.5);
    
    // 인터페이스와 데이터를 1:1로 매핑
    const pairs = shuffledInterfaces.map((interface, index) => ({
        interface: interface,
        data: shuffledData[index],
        htmlFile: CONFIG.interfaces[interface],
        dataPath: `${CONFIG.dataBasePath}/${shuffledData[index]}/${CONFIG.interfaces[interface]}`
    }));
    
    return pairs;
}

// localStorage에 저장된 매핑이 없으면 새로 생성하고 저장
async function getOrCreateInterfaceDataPairs() {
    let pairs = JSON.parse(localStorage.getItem('interfaceDataPairs'));
    
    if (!pairs || pairs.length !== CONFIG.numInterfaces) {
        pairs = await generateInterfaceDataPairs();
        localStorage.setItem('interfaceDataPairs', JSON.stringify(pairs));
    }
    
    return pairs;
}

// 현재 테스트 단계 가져오기 (0부터 시작)
function getCurrentTestStep() {
    const step = localStorage.getItem('currentTestStep');
    return step ? parseInt(step) : 0;
}

// 다음 테스트 단계로 이동
function setCurrentTestStep(step) {
    localStorage.setItem('currentTestStep', step.toString());
}

// 테스트 결과 저장
async function saveTestResult(step, answers) {
    const results = JSON.parse(localStorage.getItem('testResults') || '[]');
    const pairs = await getOrCreateInterfaceDataPairs();
    const pair = pairs[step];
    
    if (!pair) {
        console.warn('saveTestResult: pair 정보를 찾을 수 없습니다.', { step, pairs });
        return;
    }
    
    results[step] = {
        interface: pair.interface,
        data: pair.data,
        answers,
        timestamp: new Date().toISOString()
    };
    
    localStorage.setItem('testResults', JSON.stringify(results));
}

// 모든 테스트 결과 가져오기
function getAllTestResults() {
    return JSON.parse(localStorage.getItem('testResults') || '[]');
}

