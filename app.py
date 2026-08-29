import os
import sqlite3
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Gemini API 및 DB 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_FILE = "money_app.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_pin TEXT NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            payment TEXT NOT NULL,
            memo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>부부 스마트 가계부</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#2563eb">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .category-chip.active {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: 700;
            border-color: #2563eb;
        }
        .type-tab.active-expense {
            background-color: #ef4444;
            color: #ffffff;
            font-weight: 700;
        }
        .type-tab.active-income {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: 700;
        }
    </style>
</head>
<body class="bg-gray-100 text-gray-800 pb-20">

    <!-- 1. 6자리 PIN 번호 인증 모달 (보안 잠금) -->
    <div id="pin-modal" class="fixed inset-0 bg-gray-900 bg-opacity-95 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl p-6 w-full max-w-xs shadow-2xl text-center">
            <div class="text-3xl mb-2">🔒</div>
            <h2 class="text-base font-bold text-gray-800">가족 비밀번호 입력</h2>
            <p class="text-xs text-gray-500 mt-1 mb-4">두 분만의 6자리 PIN을 입력하세요.<br>(처음 입력한 번호가 가족 암호가 됩니다)</p>
            <input type="password" id="input-pin" maxlength="6" pattern="[0-9]*" inputmode="numeric" placeholder="6자리 숫자"
                   class="w-full text-center tracking-widest text-2xl font-bold border-2 border-blue-400 rounded-lg p-2.5 mb-4 focus:outline-none focus:border-blue-600 bg-gray-50">
            <button onclick="loginWithPin()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 rounded-lg text-sm transition">
                가계부 열기
            </button>
        </div>
    </div>

    <!-- 2. 메인 가계부 앱 UI -->
    <div id="app-container" class="max-w-md mx-auto min-h-screen bg-white shadow-md flex flex-col hidden">
        <header class="bg-blue-600 text-white p-4 sticky top-0 z-10 flex justify-between items-center shadow">
            <div class="flex items-center gap-2">
                <h1 class="text-lg font-bold">💑 우리 부부 가계부</h1>
            </div>
            <div class="flex items-center gap-2">
                <span id="current-month" class="text-xs bg-blue-700 px-2 py-1 rounded"></span>
                <button onclick="logoutPin()" class="text-[11px] bg-blue-800 px-2 py-1 rounded hover:bg-blue-900">잠금</button>
            </div>
        </header>

        <!-- 요약 현황판 -->
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

        <!-- 입력 폼 -->
        <div class="p-4 border-b bg-gray-50">
            <form id="tx-form" class="space-y-3">
                <input type="hidden" id="tx-id">

                <!-- 1) 수입 / 지출 큰 토글 탭 -->
                <div class="grid grid-cols-2 gap-2 bg-gray-200 p-1 rounded-xl text-center">
                    <button type="button" id="tab-expense" onclick="setType('expense')" class="type-tab active-expense py-2 rounded-lg text-xs font-bold transition">
                        지출 (-)
                    </button>
                    <button type="button" id="tab-income" onclick="setType('income')" class="type-tab py-2 rounded-lg text-xs font-bold transition">
                        수입 (+)
                    </button>
                </div>

                <!-- 2) 카테고리 태그 칩 버튼들 -->
                <div>
                    <div class="text-[11px] font-semibold text-gray-500 mb-1.5 flex justify-between">
                        <span>카테고리 선택</span>
                        <span id="selected-cat-label" class="text-blue-600 font-bold">식비</span>
                    </div>
                    
                    <!-- 지출 카테고리 칩 -->
                    <div id="expense-categories" class="flex flex-wrap gap-1.5">
                        <button type="button" onclick="selectCategory('식비')" class="category-chip active text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">🍚 식비</button>
                        <button type="button" onclick="selectCategory('주유/교통')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">🚗 주유/교통</button>
                        <button type="button" onclick="selectCategory('마트/쇼핑')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">🛒 마트/쇼핑</button>
                        <button type="button" onclick="selectCategory('생활/문화')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">☕ 생활/문화</button>
                        <button type="button" onclick="selectCategory('주거/통신')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">🏠 주거/통신</button>
                        <button type="button" onclick="selectCategory('기타')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">✏️ 직접입력</button>
                    </div>

                    <!-- 수입 카테고리 칩 (내 급여 10일, 아내 급여 30일 반영) -->
                    <div id="income-categories" class="flex flex-wrap gap-1.5 hidden">
                        <button type="button" onclick="selectCategory('내 급여(10일)')" class="category-chip active text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">💼 내 급여(10일)</button>
                        <button type="button" onclick="selectCategory('아내 급여(30일)')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">🌸 아내 급여(30일)</button>
                        <button type="button" onclick="selectCategory('기타 수입')" class="category-chip text-xs border border-gray-300 px-2.5 py-1.5 rounded-lg bg-white">🎁 기타 수입</button>
                    </div>

                    <!-- 카테고리 직접 입력 칸 (기타/직접입력 선택 시 또는 추가 수정) -->
                    <div id="custom-cat-wrapper" class="hidden mt-2">
                        <input type="text" id="tx-custom-category" placeholder="직접 입력할 카테고리명" class="w-full border p-2 rounded text-xs bg-white">
                    </div>
                </div>

                <!-- 3) 금액 및 결제수단 / 날짜 -->
                <div class="grid grid-cols-2 gap-2">
                    <input type="number" id="tx-amount" placeholder="금액 (원)" required class="border p-2 rounded text-sm bg-white font-bold">
                    <input type="date" id="tx-date" required class="border p-2 rounded text-xs bg-white">
                </div>

                <div class="grid grid-cols-2 gap-2">
                    <select id="tx-payment" class="border p-2 rounded text-xs bg-white font-medium">
                        <option value="카드">💳 카드 결제</option>
                        <option value="현금">💵 현금 결제</option>
                        <option value="계좌이체">🏦 계좌이체</option>
                    </select>
                    <input type="text" id="tx-memo" placeholder="상세 메모 (선택)" class="border p-2 rounded text-xs bg-white">
                </div>

                <!-- 4) 버튼 -->
                <div class="flex gap-2 pt-1">
                    <button type="submit" id="btn-submit" class="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-bold shadow hover:bg-blue-700">
                        기록 추가하기
                    </button>
                    <button type="button" id="btn-cancel-edit" onclick="resetForm()" class="hidden px-4 bg-gray-300 text-gray-700 py-2.5 rounded-lg text-sm font-bold">
                        취소
                    </button>
                </div>
            </form>
        </div>

        <!-- 분석 & 목록 영역 -->
        <div class="p-4 flex-1 space-y-5">
            <!-- 차트 -->
            <div class="bg-white p-3 rounded-lg border shadow-sm">
                <h2 class="font-bold text-xs text-gray-600 mb-2">📊 지출 비중 분석</h2>
                <div class="w-full h-44 flex justify-center items-center">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>

            <!-- AI 분석 코칭 -->
            <div class="bg-gradient-to-r from-emerald-50 to-teal-50 p-3.5 rounded-lg border border-emerald-200 shadow-sm">
                <div class="flex justify-between items-center mb-2">
                    <span class="font-bold text-xs text-emerald-800">🤖 부부 가계부 AI 코칭</span>
                    <span class="text-[10px] bg-emerald-200 text-emerald-800 px-1.5 py-0.5 rounded">Gemini</span>
                </div>
                <button id="btn-ai-analyze" onclick="analyzeBudget()" class="w-full bg-emerald-600 text-white py-2 rounded text-xs font-bold hover:bg-emerald-700 shadow transition">
                    이번 달 지출 패턴 분석 및 절약 팁
                </button>
                <div id="ai-result" class="hidden mt-2.5 p-3 bg-white border border-emerald-200 rounded text-xs leading-relaxed text-gray-700 whitespace-pre-line"></div>
            </div>

            <!-- 내역 목록 -->
            <div>
                <div class="flex justify-between items-center mb-2">
                    <h2 class="font-bold text-xs text-gray-600">📝 공동 가계부 내역 (<span id="tx-count">0</span>건)</h2>
                    <button onclick="exportCSV()" class="text-xs text-blue-600 hover:underline">엑셀(CSV) 다운로드</button>
                </div>
                <ul id="tx-list" class="space-y-2"></ul>
            </div>
        </div>
    </div>

    <script>
        let currentPin = localStorage.getItem('family_money_pin') || '';
        let currentType = 'expense';
        let currentCategory = '식비';
        let transactions = [];
        let chartInstance = null;

        document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
        document.getElementById('current-month').innerText = `${new Date().getMonth() + 1}월 현황`;

        window.onload = () => {
            if (currentPin && currentPin.length === 6) {
                document.getElementById('pin-modal').classList.add('hidden');
                document.getElementById('app-container').classList.remove('hidden');
                loadTransactions();
            } else {
                document.getElementById('pin-modal').classList.remove('hidden');
            }
        };

        function loginWithPin() {
            const pin = document.getElementById('input-pin').value.trim();
            if (pin.length !== 6 || isNaN(pin)) {
                alert('숫자 6자리를 정확하게 입력해주세요.');
                return;
            }
            currentPin = pin;
            localStorage.setItem('family_money_pin', currentPin);
            document.getElementById('pin-modal').classList.add('hidden');
            document.getElementById('app-container').classList.remove('hidden');
            loadTransactions();
        }

        function logoutPin() {
            if (confirm('가계부를 잠그시겠습니까?')) {
                localStorage.removeItem('family_money_pin');
                location.reload();
            }
        }

        function setType(type) {
            currentType = type;
            const expTab = document.getElementById('tab-expense');
            const incTab = document.getElementById('tab-income');
            const expCats = document.getElementById('expense-categories');
            const incCats = document.getElementById('income-categories');

            if (type === 'expense') {
                expTab.className = 'type-tab active-expense py-2 rounded-lg text-xs font-bold transition';
                incTab.className = 'type-tab py-2 rounded-lg text-xs font-bold transition';
                expCats.classList.remove('hidden');
                incCats.classList.add('hidden');
                selectCategory('식비');
            } else {
                expTab.className = 'type-tab py-2 rounded-lg text-xs font-bold transition';
                incTab.className = 'type-tab active-income py-2 rounded-lg text-xs font-bold transition';
                expCats.classList.add('hidden');
                incCats.classList.remove('hidden');
                selectCategory('내 급여(10일)');
            }
        }

        function selectCategory(cat) {
            currentCategory = cat;
            document.getElementById('selected-cat-label').innerText = cat;
            
            const chips = document.querySelectorAll('.category-chip');
            chips.forEach(c => {
                if (c.innerText.includes(cat) || (cat === '기타' && c.innerText.includes('직접입력'))) {
                    c.classList.add('active');
                } else {
                    c.classList.remove('active');
                }
            });

            const customWrapper = document.getElementById('custom-cat-wrapper');
            if (cat === '기타') {
                customWrapper.classList.remove('hidden');
                document.getElementById('tx-custom-category').focus();
            } else {
                customWrapper.classList.add('hidden');
            }
        }

        async function loadTransactions() {
            try {
                const res = await fetch(`/api/transactions?pin=${currentPin}`);
                transactions = await res.json();
                renderAll();
            } catch (err) {
                console.error(err);
            }
        }

        function renderAll() {
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

            transactions.forEach(t => {
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
                            <button onclick="editTx(${t.id})" class="text-[10px] text-blue-500 hover:underline">수정</button>
                            <button onclick="deleteTx(${t.id})" class="text-[10px] text-red-400 hover:underline">삭제</button>
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

        document.getElementById('tx-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('tx-id').value;
            let finalCategory = currentCategory;
            if (currentCategory === '기타') {
                const customVal = document.getElementById('tx-custom-category').value.trim();
                if (customVal) finalCategory = customVal;
            }

            const payload = {
                pin: currentPin,
                type: currentType,
                amount: parseInt(document.getElementById('tx-amount').value),
                date: document.getElementById('tx-date').value,
                category: finalCategory,
                payment: document.getElementById('tx-payment').value,
                memo: document.getElementById('tx-memo').value
            };

            if (id) {
                await fetch(`/api/transactions/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                await fetch('/api/transactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            resetForm();
            loadTransactions();
        });

        function editTx(id) {
            const t = transactions.find(item => item.id === id);
            if (!t) return;

            document.getElementById('tx-id').value = t.id;
            setType(t.type);
            selectCategory(t.category);
            document.getElementById('tx-amount').value = t.amount;
            document.getElementById('tx-date').value = t.date;
            document.getElementById('tx-payment').value = t.payment;
            document.getElementById('tx-memo').value = t.memo || '';

            document.getElementById('btn-submit').innerText = '수정 저장';
            document.getElementById('btn-submit').className = 'flex-1 bg-amber-600 text-white py-2.5 rounded-lg text-sm font-bold shadow hover:bg-amber-700';
            document.getElementById('btn-cancel-edit').classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function resetForm() {
            document.getElementById('tx-id').value = '';
            document.getElementById('tx-amount').value = '';
            document.getElementById('tx-memo').value = '';
            document.getElementById('tx-custom-category').value = '';
            document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
            document.getElementById('btn-submit').innerText = '기록 추가하기';
            document.getElementById('btn-submit').className = 'flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-bold shadow hover:bg-blue-700';
            document.getElementById('btn-cancel-edit').classList.add('hidden');
            setType('expense');
        }

        async function deleteTx(id) {
            if (confirm('이 내역을 삭제하시겠습니까?')) {
                await fetch(`/api/transactions/${id}?pin=${currentPin}`, { method: 'DELETE' });
                loadTransactions();
            }
        }

        function exportCSV() {
            if (!transactions.length) return alert('저장할 내역이 없습니다.');
            let csv = "날짜,구분,카테고리,금액,결제수단,메모\\n";
            transactions.forEach(t => {
                csv += `"${t.date}","${t.type === 'expense' ? '지출' : '수입'}","${t.category}",${t.amount},"${t.payment}","${t.memo || ''}"\\n`;
            });
            const blob = new Blob(["\\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `부부가계부_${new Date().toISOString().slice(0,10)}.csv`;
            link.click();
        }

        async function analyzeBudget() {
            if (!transactions.length) return alert('분석할 내역이 없습니다.');
            const resEl = document.getElementById('ai-result');
            resEl.classList.remove('hidden');
            resEl.innerText = 'Gemini AI가 부부 공동 지출을 분석 중입니다... ⏳';

            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pin: currentPin, transactions })
                });
                const data = await res.json();
                resEl.innerText = data.analysis || '분석을 완료하지 못했습니다.';
            } catch (err) {
                resEl.innerText = '통신 에러: ' + err.message;
            }
        }
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
        "short_name": "부부가계부",
        "name": "우리 부부 스마트 가계부",
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

# --- CRUD API with PIN Security ---
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    pin = request.args.get("pin", "")
    if not pin or len(pin) != 6:
        return jsonify([])
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, type, amount, date, category, payment, memo FROM transactions WHERE family_pin = ? ORDER BY date DESC, id DESC", (pin,))
    rows = c.fetchall()
    conn.close()
    return jsonify([
        {"id": r[0], "type": r[1], "amount": r[2], "date": r[3], "category": r[4], "payment": r[5], "memo": r[6]}
        for r in rows
    ])

@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json() or {}
    pin = data.get("pin", "")
    if not pin or len(pin) != 6:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO transactions (family_pin, type, amount, date, category, payment, memo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (pin, data["type"], data["amount"], data["date"], data["category"], data["payment"], data.get("memo", "")))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/transactions/<int:tx_id>", methods=["PUT"])
def update_transaction(tx_id):
    data = request.get_json() or {}
    pin = data.get("pin", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE transactions 
        SET type = ?, amount = ?, date = ?, category = ?, payment = ?, memo = ?
        WHERE id = ? AND family_pin = ?
    """, (data["type"], data["amount"], data["date"], data["category"], data["payment"], data.get("memo", ""), tx_id, pin))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/transactions/<int:tx_id>", methods=["DELETE"])
def delete_transaction(tx_id):
    pin = request.args.get("pin", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ? AND family_pin = ?", (tx_id, pin))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

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
당신은 부부 재정 및 가계부를 전문적으로 코칭해주는 AI 매니저입니다.
남편(급여일 10일)과 아내(급여일 30일)의 공동 가계부 거래 내역을 기반으로 아래 항목을 간결하게 분석해 주세요:

[거래 내역]
{chr(10).join(summary_lines)}

[분석 요청]
1. 이번 달 총수입(각 급여일 반영) 및 총지출 요약
2. 지출 비중이 가장 높은 항목 진단
3. 부부를 위한 실천적이고 따뜻한 절약 및 예산 관리 팁 3가지
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
