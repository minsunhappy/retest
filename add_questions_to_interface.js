// 이 스크립트는 인터페이스 HTML 파일에 질문 폼을 추가하는 유틸리티입니다.
// Node.js 환경에서 실행하여 모든 인터페이스 HTML 파일을 수정할 수 있습니다.

const fs = require('fs');
const path = require('path');

// 질문 HTML 템플릿
function generateQuestionsHTML(questionsData) {
    let html = `
    <div id="survey-questions" style="margin-top: 40px; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
        <h2 style="font-size: 18px; margin-bottom: 20px;">다음 질문에 답해주세요:</h2>
    `;

    questionsData.forEach((question, index) => {
        html += `
        <div class="question-group" style="margin-bottom: 30px; padding: 15px; background-color: white; border-radius: 4px;">
            <div class="question-title" style="font-size: 16px; font-weight: bold; margin-bottom: 15px;">
                <strong><span style="font-size:16px;">${question.text}</span></strong>
            </div>
            <div class="scale-container" style="margin: 15px 0;">
                <div class="scale-labels" style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 12px; color: #666;">${question.scaleLeft}</span>
                    <span style="font-size: 12px; color: #666;">${question.scaleRight}</span>
                </div>
                <div class="scale-options" style="display: flex; justify-content: space-between; gap: 5px;">
        `;

        for (let i = 1; i <= 7; i++) {
            html += `
                    <div class="scale-option" style="flex: 1;">
                        <input type="radio" name="question-${index}" id="q${index}-opt${i}" value="${i}" required style="display: none;">
                        <label for="q${index}-opt${i}" style="display: block; padding: 10px; text-align: center; background-color: #fff; border: 2px solid #ddd; border-radius: 4px; cursor: pointer; font-size: 18px; font-weight: bold; transition: all 0.3s;">${i}</label>
                    </div>
            `;
        }

        html += `
                </div>
            </div>
        </div>
        `;
    });

    html += `
        <div style="text-align: center; margin-top: 30px;">
            <button id="submit-survey" style="background-color: #3498db; color: white; padding: 12px 40px; font-size: 18px; border: none; border-radius: 4px; cursor: pointer;">제출</button>
        </div>
    </div>

    <script>
        // 라디오 버튼 스타일링
        document.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.addEventListener('change', function() {
                document.querySelectorAll('input[name="' + this.name + '"]').forEach(r => {
                    r.nextElementSibling.style.backgroundColor = '#fff';
                    r.nextElementSibling.style.color = '#666';
                    r.nextElementSibling.style.borderColor = '#ddd';
                });
                if (this.checked) {
                    this.nextElementSibling.style.backgroundColor = '#3498db';
                    this.nextElementSibling.style.color = 'white';
                    this.nextElementSibling.style.borderColor = '#3498db';
                }
            });
        });

        document.getElementById('submit-survey').addEventListener('click', function() {
            const answers = [];
            const questions = document.querySelectorAll('.question-group');
            let allAnswered = true;

            questions.forEach((q, index) => {
                const selected = q.querySelector('input[type="radio"]:checked');
                if (!selected) {
                    allAnswered = false;
                } else {
                    answers.push({
                        questionIndex: index,
                        answer: parseInt(selected.value)
                    });
                }
            });

            if (!allAnswered) {
                alert('모든 질문에 답해주세요.');
                return;
            }

            // 결과 저장 (부모 페이지로 전달)
            if (window.parent && window.parent !== window) {
                window.parent.postMessage({
                    type: 'survey-completed',
                    answers: answers
                }, '*');
            } else {
                console.log('Survey answers:', answers);
            }
        });
    </script>
    `;

    return html;
}

// HTML 파일에 질문 추가
function addQuestionsToHTML(htmlFilePath, questionsData) {
    try {
        let htmlContent = fs.readFileSync(htmlFilePath, 'utf8');
        
        // </body> 태그 앞에 질문 HTML 추가
        const questionsHTML = generateQuestionsHTML(questionsData);
        htmlContent = htmlContent.replace('</body>', questionsHTML + '\n</body>');
        
        // 수정된 HTML 저장
        fs.writeFileSync(htmlFilePath, htmlContent, 'utf8');
        console.log(`질문이 추가되었습니다: ${htmlFilePath}`);
    } catch (error) {
        console.error(`오류 발생 (${htmlFilePath}):`, error.message);
    }
}

// 사용 예시:
// const questionsData = [
//     { text: '질문 1', scaleLeft: '매우 적다', scaleRight: '매우 많다' },
//     // ...
// ];
// addQuestionsToHTML('path/to/interface.html', questionsData);

module.exports = { addQuestionsToHTML, generateQuestionsHTML };

