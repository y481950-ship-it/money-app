import os
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>스마트 가계부</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#2563eb">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-100 text-gray-800 pb-20">
    <div class="max-w-md mx-auto min-h-screen bg-white shadow-md flex flex-col">
        <header class="bg-blue-600 text-white p-4 sticky top-0 z-10 flex justify-between items-center shadow">
            <h1 class="text-lg font-bold">💳 스마트 가계부</h1>
            <span id="current-month" class="text-xs bg-blue-700 px-2 py-1 rounded"></span>
        </header>

        <div class="p-4 grid grid-cols-3 gap-2 bg-blue-50 border-b">
            <div class="bg-white p-2.5 rounded-lg shadow-sm text-center">
                <span class="text-[11px] text-gray-500 font-medium">총수입</span>
                <p id="total-income" class="text-sm font-bold text-blue-600 truncate mt-1">0원</p>
            </div>
            <div class="bg-white p-2.5 rounded-lg shadow-sm text-center">
                <span class="text-[11px] text-gray-500 font-medium">총지출</span>
                <p id="total-expense" class="text-sm font-bold text-red-500 truncate mt-1">0원</p>
            </div>
            <div class="bg-white p-2.5 rounded-lg shadow-sm text-center">
                <span class="text-[11px] text-gray-500 font-medium">잔액</span>
                <p id="balance" class="text-sm font-bold text-gray-800 truncate mt-1">0원</p>
            </div>
        </div>

        <div class="p-4 border-b bg-gray-50">
            <form id="tx-form" class="space-y-2.5">
                <input type="hidden" id="tx-id">
                <div class="grid grid-cols-2 gap-2">
                    <select id="tx-type" class="border p-2 rounded text-sm bg-white font-semibold">
                        <option value="expense">지출 (-)</option>
                        <option value="income">수입 (+)</option>
                    </select>
                    <input type="number" id="tx-amount" placeholder="금액 (원)" required class="border p-2 rounded text-sm bg-white">
                </div>
                <div class="grid grid-cols-3 gap-2">
                    <input type="date" id="tx-date" required class="border p-2 rounded text-xs bg-white">
                    <select id="tx-category" class="border p-2 rounded text-xs bg-white">
                        <option value="식비">식비</option>
                        <option value="주유/교통">주유/교통</option>
                        <option value="마트/쇼핑">마트/쇼핑</option>
                        <option value="생활/문화">생활/문화</option>
                        <option value="주거/통신">주거/통신</option>
                        <option value="급여/용돈">급여/용돈</option>
                        <option value="기타">기타</option>
                    </select>
                    <select id="tx-payment" class="border p-2 rounded text-xs bg-white">
                        <option value="카드">카드</option>
                        <option value="현금">현금</option>
                        <option value="계좌이체">계좌이체</option>
                    </select>
                </div>
                <input type="text" id="tx-memo" placeholder="메모" class="w-full border p-2 rounded text-sm bg-white">
                <div class="flex gap-2">
                    <button type="submit" id="btn-submit" class="flex-1 bg-blue-600 text-white py-2 rounded text-sm font-bold shadow hover:bg-blue-700">추가하기</button>
                    <button type="button" id="btn-cancel-edit" class="hidden px-3 bg-gray-300 text-gray-700 py-2 rounded text-sm font-bold">취소</button>
                </div>
            </form>
        </div>

        <div class="p-4 flex-1 space-y-5">
            <div class="bg-white p-3 rounded-lg border shadow-sm">
                <h2 class="font-bold text-xs text-gray-600 mb-2">📊 카테고리별 지출 요약</h2>
                <div class="w-full h-44 flex justify-center items-center">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>

            <div class="bg-gradient-to-r from-emerald-50 to-teal-50 p-3.5 rounded-lg border border-emerald-200 shadow-sm">
                <div class="flex justify-between items-center mb-2">
                    <span class="font-bold text-xs text-emerald-800">🤖 Gemini AI 소비 코칭</span>
                    <span class="text-[10px] bg-emerald-200 text-emerald-800 px-1.5 py-0.5 rounded">gemini-3.6-flash</span>
                </div>
                <button id="btn-ai-analyze" class="w-full bg-emerald-600 text-white py-2 rounded text-xs font-bold hover:bg-emerald-700 shadow transition">
                    이번 달 소비 패턴 분석 및 절약 팁 받기
                </button>
                <div id="ai-result" class="hidden mt-2.5 p-3 bg-white border border-emerald-200 rounded text-xs leading-relaxed text-gray-700 whitespace-pre-line"></div>
            </div>

            <div>
                <div class="flex justify-between items-center mb-2">
                    <h2 class="font-bold text-xs text-gray-600">📝 상세 내역 (<span id="tx-count">0</span>건)</h2>
                    <button id="btn-export-csv" class="text-xs text-blue-600 hover:underline">엑셀(CSV) 저장</button>
                </div>
                <ul id="tx-list" class="space-y-2"></ul>
            </div>
        </div>
    </div>

    <script>
        let transactions = JSON.parse(localStorage.getItem('money_app_txs') || '[]');
        let chartInstance = null;

        document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
        document.getElementById('current-month').innerText = `${new Date().getMonth() + 1}월 현황`;

        function saveAndRender() {
            localStorage.setItem('money_app_txs', JSON.stringify(transactions));
            renderSummary();
            renderList();
            renderChart();
        }

        function renderSummary() {
            let income = 0, expense = 0;
            transactions.forEach(t => {
                if (t.type === 'income') income += Number(t.amount);
                else expense += Number(t.amount);
            });
            document.getElementById('total-income').innerText = income.toLocaleString() + '원';
            document.getElementById('total-expense').innerText = expense.toLocaleString() + '원';
            const bal = income - expense;
            const balEl = document.getElementById('balance');
            balEl.innerText = bal.toLocaleString() + '원';
            balEl.className = `text-sm font-bold truncate mt-1 ${bal < 0 ? 'text-red-500' : 'text-gray-800'}`;
            document.getElementById('tx-count').innerText = transactions.length;
        }

        function renderList() {
            const listEl = document.getElementById('tx-list');
            listEl.innerHTML = '';
            if (transactions.length === 0) {
                listEl.innerHTML = '<li class="text-center text-xs text-gray-400 py-6">등록된 내역이 없습니다.</li>';
                return;
            }

            const sorted = [...transactions].map((t, i) => ({ ...t, originalIndex: i }))
                                            .sort((a, b) => new Date(b.date) - new Date(a.date));

            sorted.forEach(t => {
                const li = document.createElement('li');
                li.className = 'p-3 bg-white rounded-lg border border-gray-100 shadow-sm flex justify-between items-center';
                const isExp = t.type === 'expense';
                li.innerHTML = `
                    <div class="min-w-0 pr-2">
                        <div class="flex items-center gap-1.5">
                            <span class="font-bold text-xs text-gray-800">${t.category}</span>
                            <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">${t.payment}</span>
                        </div>
                        <div class="text-[11px] text-gray-500 truncate mt-0.5">${t.memo ? t.memo + ' · ' : ''}${t.date}</div>
                    </div>
                    <div class="text-right flex-shrink-0">
                        <div class="font-bold text-sm ${isExp ? 'text-red-500' : 'text-blue-600'}">
                            ${isExp ? '-' : '+'}${Number(t.amount).toLocaleString()}원
                        </div>
                        <div class="space-x-1.5 mt-0.5">
                            <button onclick="editTx(${t.originalIndex})" class="text-[10px] text-blue-500 hover:underline">수정</button>
                            <button onclick="deleteTx(${t.originalIndex})" class="text-[10px] text-red-400 hover:underline">삭제</button>
                        </div>
                    </div>
                `;
                listEl.appendChild(li);
            });
        }

        function renderChart() {
            const ctx = document.getElementById('categoryChart').getContext('2d');
            const totals = {};
            transactions.filter(t => t.type === 'expense').forEach(t => {
                totals[t.category] = (totals[t.category] || 0) + Number(t.amount);
            });

            const labels = Object.keys(totals);
            const data = Object.values(totals);

            if (chartInstance) chartInstance.destroy();

            chartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels.length ? labels : ['지출 내역 없음'],
                    datasets: [{
                        data: data.length ? data : [1],
                        backgroundColor: ['#f87171', '#fb923c', '#facc15', '#4ade80', '#60a5fa', '#a78bfa', '#9ca3af']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { boxWidth: 8, font: { size: 10 } } } }
                }
            });
        }

        document.getElementById('tx-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const id = document.getElementById('tx-id').value;
            const txData = {
                type: document.getElementById('tx-type').value,
                amount: document.getElementById('tx-amount').value,
                date: document.getElementById('tx-date').value,
                category: document.getElementById('tx-category').value,
                payment: document.getElementById('tx-payment').value,
                memo: document.getElementById('tx-memo').value
            };

            if (id !== '') {
                transactions[parseInt(id)] = txData;
                resetForm();
            } else {
                transactions.push(txData);
                document.getElementById('tx-amount').value = '';
                document.getElementById('tx-memo').value = '';
            }
            saveAndRender();
        });

        function editTx(index) {
            const t = transactions[index];
            document.getElementById('tx-id').value = index;
            document.getElementById('tx-type').value = t.type;
            document.getElementById('tx-amount').value = t.amount;
            document.getElementById('tx-date').value = t.date;
            document.getElementById('tx-category').value = t.category;
            document.getElementById('tx-payment').value = t.payment;
            document.getElementById('tx-memo').value = t.memo || '';

            document.getElementById('btn-submit').innerText = '수정 완료';
            document.getElementById('btn-submit').className = 'flex-1 bg-amber-600 text-white py-2 rounded text-sm font-bold shadow hover:bg-amber-700';
            document.getElementById('btn-cancel-edit').classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        document.getElementById('btn-cancel-edit').addEventListener('click', resetForm);

        function resetForm() {
            document.getElementById('tx-id').value = '';
            document.getElementById('tx-amount').value = '';
            document.getElementById('tx-memo').value = '';
            document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
            document.getElementById('btn-submit').innerText = '추가하기';
            document.getElementById('btn-submit').className = 'flex-1 bg-blue-600 text-white py-2 rounded text-sm font-bold shadow hover:bg-blue-700';
            document.getElementById('btn-cancel-edit').classList.add('hidden');
        }

        function deleteTx(index) {
            if (confirm('이 내역을 삭제하시겠습니까?')) {
                transactions.splice(index, 1);
                saveAndRender();
            }
        }

        document.getElementById('btn-export-csv').addEventListener('click', () => {
            if (!transactions.length) return alert('저장할 내역이 없습니다.');
            let csv = "날짜,구분,카테고리,금액,결제수단,메모\\n";
            transactions.forEach(t => {
                csv += `"${t.date}","${t.type === 'expense' ? '지출' : '수입'}","${t.category}",${t.amount},"${t.payment}","${t.memo || ''}"\\n`;
            });
            const blob = new Blob(["\\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `스마트가계부_${new Date().toISOString().slice(0,10)}.csv`;
            link.click();
        });

        document.getElementById('btn-ai-analyze').addEventListener('click', async () => {
            if (!transactions.length) return alert('분석할 내역이 없습니다.');
            const resEl = document.getElementById('ai-result');
            resEl.classList.remove('hidden');
            resEl.innerText = 'Gemini 3.6 Flash 모델이 분석 중입니다... ⏳';

            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ transactions })
                });
                const data = await res.json();
                resEl.innerText = data.analysis || '분석을 완료하지 못했습니다.';
            } catch (err) {
                resEl.innerText = '통신 에러: ' + err.message;
            }
        });

        saveAndRender();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "short_name": "스마트가계부",
        "name": "스마트 가계부 (money-app)",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/2331/2331941.png",
                "type": "image/png",
                "sizes": "512x512"
            }
        ],
        "start_url": "/",
        "background_color": "#ffffff",
        "theme_color": "#2563eb",
        "display": "standalone"
    })

@app.route("/api/analyze", methods=["POST"])
def analyze():
    if not GEMINI_API_KEY:
        return jsonify({"analysis": "GEMINI_API_KEY가 설정되지 않았습니다."})

    data = request.get_json() or {}
    txs = data.get("transactions", [])
    if not txs:
        return jsonify({"analysis": "분석할 데이터가 없습니다."})

    summary_lines = [
        f"[{t['date']}] {t['type']}: {t['category']} {t['amount']}원 ({t.get('payment','')}) / 메모: {t.get('memo','')}"
        for t in txs
    ]
    prompt = f"""
당신은 똑똑하고 직관적인 가계부 재정 코치입니다.
사용자의 가계부 거래 내역을 보고 아래 형식으로 핵심만 간결하게 조언해 주세요:

[거래 내역]
{chr(10).join(summary_lines)}

[분석 요청]
1. 지출 비중 요약 (가장 많이 쓴 항목 1~2개)
2. 소비 패턴 진단 및 낭비 요인 짚기
3. 바로 실천할 수 있는 구체적인 절약 조언 (2~3개 불릿 포인트)
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, json=payload, timeout=20)
        res_json = res.json()
        text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"analysis": text})
    except Exception as e:
        return jsonify({"analysis": f"AI 분석 오류 ({str(e)})"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
