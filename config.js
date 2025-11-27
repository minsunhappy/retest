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

const INTERFACE_ORDER = ['C', 'D', 'D1', 'Y', 'Y1'];
const FAIR_DATA_PERMUTATIONS = [
    [0, 1, 2, 3, 4],
    [1, 2, 3, 4, 0],
    [2, 3, 4, 0, 1],
    [3, 4, 0, 1, 2],
    [4, 0, 1, 2, 3]
];
const FAIR_PAIR_STORAGE_KEY = 'fairPairScheduleIndex';

function getNextFairPermutationIndex(length) {
    if (!length || length <= 0) {
        return 0;
    }
    if (typeof localStorage === 'undefined') {
        return 0;
    }
    const stored = parseInt(localStorage.getItem(FAIR_PAIR_STORAGE_KEY), 10);
    const current = Number.isInteger(stored) && stored >= 0 ? stored % length : 0;
    const next = (current + 1) % length;
    localStorage.setItem(FAIR_PAIR_STORAGE_KEY, next.toString());
    return current;
}

function shuffleArray(items) {
    const arr = [...items];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

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
    const interfaces = [...INTERFACE_ORDER];
    
    // 데이터 폴더 이름 로드
    const dataFolders = await loadDataFolders();
    
    if (dataFolders.length < interfaces.length) {
        console.error(`오류: 데이터 폴더가 ${interfaces.length}개 이상 필요합니다. (현재: ${dataFolders.length}개)`);
        throw new Error('데이터 폴더가 부족합니다.');
    }
    
    const normalizedData = dataFolders.slice(0, interfaces.length);
    let permutation = null;
    const eligiblePermutations = FAIR_DATA_PERMUTATIONS.filter(p => p.length === interfaces.length);
    
    if (eligiblePermutations.length > 0 && typeof localStorage !== 'undefined') {
        const scheduleIndex = getNextFairPermutationIndex(eligiblePermutations.length);
        permutation = eligiblePermutations[scheduleIndex];
    } else {
        permutation = interfaces.map((_, idx) => idx);
    }
    
    const pairedList = interfaces.map((interfaceId, index) => {
        const dataIndex = permutation[index] % normalizedData.length;
        const dataFolder = normalizedData[dataIndex];
        return {
            interface: interfaceId,
            data: dataFolder,
            htmlFile: CONFIG.interfaces[interfaceId],
            dataPath: `${CONFIG.dataBasePath}/${dataFolder}/${CONFIG.interfaces[interfaceId]}`
        };
    });
    
    return shuffleArray(pairedList);
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

let interfaceDescriptionsCache = null;

function getDefaultInterfaceDescriptions() {
    return [
        {
            id: 'C',
            title: '인터페이스 A',
            media: 'preview/C.MP4',
            description: '영상 <strong>하단</strong>에 자동으로 댓글이 표시됩니다.'
        },
        {
            id: 'D',
            title: '인터페이스 B',
            media: 'preview/D.MP4',
            description: '영상 <strong>하단</strong>에 댓글 목록이 고정되어 있으며, <strong>스크롤을 직접 조작</strong>하며 읽어 주시면 됩니다.'
        },
        {
            id: 'D1',
            title: '인터페이스 C',
            media: 'preview/D1.MP4',
            description: '영상의 <strong>오른쪽</strong>에서 댓글이 흘러나오는 또 다른 형태의 실시간 댓글 인터페이스입니다.'
        },
        {
            id: 'Y',
            title: '인터페이스 D',
            media: 'preview/Y.MP4',
            description: '영상 <strong>오른쪽</strong>에서 댓글이 흘러나오듯 자동으로 표시됩니다.'
        },
        {
            id: 'Y1',
            title: '인터페이스 E',
            media: 'preview/Y1.MP4',
            description: '영상 <strong>하단</strong>에 댓글이 1개씩 표시되고, <strong>스크롤</strong>로 조작하여 댓글을 넘길 수 있습니다.'
        }
    ];
}

function parseInterfaceDescriptionsMarkdown(text) {
    const blocks = text.split(/\n(?=##\s*Interface\s+)/).filter(block => block.trim());
    const parsed = [];

    blocks.forEach(block => {
        const idMatch = block.match(/##\s*Interface\s+([A-Za-z0-9]+)/i);
        if (!idMatch) {
            return;
        }
        const id = idMatch[1].trim();
        const titleMatch = block.match(/\*\*Title:\*\*\s*(.+)/);
        const mediaMatch = block.match(/\*\*Media:\*\*\s*(.+)/);
        const descMatch = block.match(/\*\*Description:\*\*\s*([\s\S]+)/);

        parsed.push({
            id,
            title: titleMatch ? titleMatch[1].trim() : `인터페이스 ${id}`,
            media: mediaMatch ? mediaMatch[1].trim() : '',
            description: descMatch ? descMatch[1].trim() : ''
        });
    });

    return parsed;
}

async function loadInterfaceDescriptions() {
    if (interfaceDescriptionsCache) {
        return interfaceDescriptionsCache;
    }

    try {
        const response = await fetch('interfaces.md', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const text = await response.text();
        const parsed = parseInterfaceDescriptionsMarkdown(text);
        if (!parsed || parsed.length === 0) {
            throw new Error('인터페이스 설명을 파싱할 수 없습니다.');
        }
        const order = ['C', 'D', 'D1', 'Y', 'Y1'];
        const map = {};
        parsed.forEach(item => {
            if (item && item.id) {
                map[item.id.toUpperCase()] = item;
            }
        });
        interfaceDescriptionsCache = order
            .map(key => map[key] || getDefaultInterfaceDescriptions().find(def => def.id === key))
            .filter(Boolean);
    } catch (error) {
        console.warn('interfaces.md를 불러오지 못했습니다. 기본 값을 사용합니다.', error);
        interfaceDescriptionsCache = getDefaultInterfaceDescriptions();
    }

    return interfaceDescriptionsCache;
}

let questionDefinitionsCache = null;

function getDefaultQuestionDefinitions() {
    return [
        {
            id: 'Q1',
            title: 'Mental Demand',
            text: '<strong>[Mental Demand]</strong> 이 인터페이스에서 댓글을 제시하는 방식이 영상 시청 과정에 <u><strong>정신적으로 부담</strong></u>을 주었나요?',
            scaleLeft: '전혀 부담을 주지 않았다',
            scaleRight: '매우 부담을 주었다'
        },
        {
            id: 'Q2',
            title: 'Physical Demand',
            text: '<strong>[Physical Demand]</strong> 이 인터페이스에서 댓글을 제시하는 방식이 영상 시청 과정에 <u><strong>신체적/물리적으로 부담</strong></u>을 주었나요?',
            scaleLeft: '전혀 신체적/물리적 부담을 주지 않았다',
            scaleRight: '매우 신체적/물리적 부담을 주었다'
        },
        {
            id: 'Q3',
            title: 'Temporal Alignment',
            text: '<strong>[Contextual Alignment]</strong> 이 인터페이스에서 재생 중에 제시되는 댓글이 해당 장면과 <u><strong>잘 어울렸나요</strong></u>?',
            scaleLeft: '전혀 어울리지 않는다',
            scaleRight: '매우 잘 어울린다'
        },
        {
            id: 'Q4',
            title: 'Overall Engagement',
            text: '<strong>[Overall Engagement]</strong> <span style="color: red; font-weight: bold; text-decoration: underline;">영상 자체의 재미와 내용과는 별개로</span> 이 인터페이스에서 댓글을 제시하는 방식이 영상 시청 경험에 <u><strong>즐거움/흥미/참여감 (engagement) 측면에서 만족</strong></u>스러웠나요?',
            scaleLeft: '전혀 만족스럽지 않다',
            scaleRight: '매우 만족스럽다'
        }
    ];
}

function parseQuestionDefinitionsMarkdown(text) {
    const regex = /## 질문\s+(\d+):\s*([^\n]+)\s*\n([\s\S]*?)(?=## 질문|\Z)/g;
    const results = [];
    let match;

    while ((match = regex.exec(text)) !== null) {
        const idx = match[1].trim();
        const title = match[2].trim();
        const block = match[3];
        const questionStart = block.indexOf('**질문 텍스트:**');
        const scaleStart = block.indexOf('**척도:**');

        let questionText = '';
        if (questionStart !== -1 && scaleStart !== -1) {
            questionText = block
                .substring(questionStart + '**질문 텍스트:**'.length, scaleStart)
                .replace(/\r?\n+/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
        }

        let scaleLeft = '';
        let scaleRight = '';
        if (scaleStart !== -1) {
            const scaleBlock = block.substring(scaleStart + '**척도:**'.length);
            const leftMatch = scaleBlock.match(/- 1:\s*(.+)/);
            const rightMatch = scaleBlock.match(/- 7:\s*(.+)/);
            scaleLeft = leftMatch ? leftMatch[1].trim() : '';
            scaleRight = rightMatch ? rightMatch[1].trim() : '';
        }

        results.push({
            id: `Q${idx}`,
            title,
            text: questionText || `[${title}] 항목`,
            scaleLeft: scaleLeft || '전혀 그렇지 않다',
            scaleRight: scaleRight || '매우 그렇다'
        });
    }

    return results;
}

async function loadQuestionDefinitions() {
    if (questionDefinitionsCache) {
        return questionDefinitionsCache;
    }

    try {
        const response = await fetch('questions.md', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const text = await response.text();
        const parsed = parseQuestionDefinitionsMarkdown(text);
        if (!parsed || parsed.length === 0) {
            throw new Error('질문 데이터를 파싱할 수 없습니다.');
        }
        const defaults = getDefaultQuestionDefinitions();
        const map = {};
        parsed.forEach(item => {
            if (item && item.id) {
                map[item.id.toUpperCase()] = item;
            }
        });
        questionDefinitionsCache = defaults.map(def => ({
            ...def,
            ...(map[def.id.toUpperCase()] || {})
        }));
    } catch (error) {
        console.warn('questions.md를 불러오지 못했습니다. 기본 질문을 사용합니다.', error);
        questionDefinitionsCache = getDefaultQuestionDefinitions();
    }

    return questionDefinitionsCache;
}

