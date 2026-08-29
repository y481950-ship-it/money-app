import os
import json
import sqlite3
import datetime
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

CORRECT_PIN = "771306"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_PATH = "family_money.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            payment TEXT NOT NULL,
            memo TEXT,
            is_fixed INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fixed_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            due_day INTEGER NOT NULL,
            category TEXT NOT NULL,
            payment TEXT NOT NULL,
            memo TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def sync_fixed_expenses_for_current_month():
    today = datetime.date.today()
    year = today.year
    month = today.month

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, amount, due_day, category, payment, memo FROM fixed_expenses")
    fixed_list = cursor.fetchall()

    for item in fixed_list:
        name, amount, due_day, category, payment, memo = item
        try:
            target_date = datetime.date(year, month, due_day).strftime("%Y-%m-%d")
        except ValueError:
            target_date = datetime.date(year, month, 28).strftime("%Y-%m-%d")

        unique_memo = f"[고정지출] {name}" + (f" ({memo})" if memo else "")
        cursor.execute("SELECT id FROM transactions WHERE is_fixed = 1 AND memo = ? AND date = ?", (unique_memo, target_date))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("""
                INSERT INTO transactions (type, amount, date, category, payment, memo, is_fixed)
                VALUES ('expense', ?, ?, ?, ?, ?, 1)
            """, (amount, target_date, category, payment, unique_memo))

    conn.commit()
    conn.close()

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
</head>
<body class="bg-gray-100 text-gray-800 pb-20">

    <!-- 1. PIN 잠금 화면 -->
    <div id="pin-screen" class="fixed inset-0 bg-white z-50 flex flex-col justify-center items-center p-6">
        <div class="w-full max-w-xs text-center space-y-4">
            <div class="text-4xl">🔒</div>
            <h2 class="text-xl font-bold text-gray-800">부부 가계부 잠금</h2>
            <p class="text-xs text-gray-500">지정된 6자리 비밀번호를 입력하세요.</p>
            <input type="password" id="input-pin" maxlength="6" pattern="[0-9]*" inputmode="numeric" placeholder="6자리 숫자" class="w-full text-center text-2xl tracking-widest border-2 border-blue-500 rounded-lg py-3 focus:outline-none focus:ring-2 focus:ring-blue-600 bg-gray-50 font-bold">
            <button id="btn-unlock" class="w-full bg-blue-600 text-white font-bold py-3 rounded-lg shadow hover:bg-blue-700 transition">입장하기</button>
            <p id="pin-error" class="hidden text-xs text-red-500 font-bold">비밀번호가 일치하지 않습니다.</p>
        </div>
    </div>

    <!-- 2. 본 화면 -->
    <div id="main-app" class="hidden max-w-md mx-auto min-h-screen bg-white shadow-md flex flex-col">
        <header class="bg-blue-600 text-white p-4 sticky top-0 z-10 flex justify-between items-center shadow">
            <div>
                <h1 class="text-base font-bold">💳 우리 부부 가계부</h1>
                <span id="current-month" class="text-[11px] text-blue-200"></span>
            </div>
            <div class="flex gap-2">
                <button id="btn-toggle-view" class="text-xs bg-blue-500 hover:bg-blue-700 px-2.5 py-1 rounded font-semibold">고정지출 관리</button>
                <button id="btn-lock" class="text-xs bg-blue-700 hover:bg-blue-800 px-2 py-1 rounded">잠금</button>
            </div>
        </header>

        <!-- 상단 4분할 상세 요약 카드 -->
        <div class="p-3 grid grid-cols-4 gap-1.5 bg-blue-50 border-b">
            <div class="bg-white p-2 rounded shadow-sm text-center">
                <span class="text-[10px] text-gray-500 font-medium">총수입</span>
                <p id="total-income" class="text-xs font-bold text-blue-600 truncate mt-0.5">0원</p>
            </div>
            <div class="bg-white p-2 rounded shadow-sm text-center">
                <span class="text-[10px] text-gray-500 font-medium">고정지출</span>
                <p id="total-fixed" class="text-xs font-bold text-orange-600 truncate mt-0.5">0원</p>
            </div>
            <div class="bg-white p-2 rounded shadow-sm text-center">
                <span class="text-[10px] text-gray-500 font-medium">변동지출</span>
                <p id="total-variable" class="text-xs font-bold text-red-500 truncate mt-0.5">0원</p>
            </div>
            <div class="bg-white p-2 rounded shadow-sm text-center">
                <span class="text-[10px] text-gray-500 font-medium">남은잔액</span>
                <p id="balance" class="text-xs font-bold text-gray-800 truncate mt-0.5">0원</p>
            </div>
        </div>

        <!-- [메인 탭: 일반 가계부 뷰] -->
        <div id="view-transactions" class="flex-1 flex flex-col">
            <div class="px-4 pt-3 pb-1 bg-gray-50 flex items-center gap-2">
                <input type="file" id="receipt-camera" accept="image/*" capture="environment" class="hidden">
                <button type="button" id="btn-camera" class="flex-1 bg-amber-500 hover:bg-amber-600 text-white py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 shadow transition">
                    <span>📷 영수증 바로 촬영 / 스캔</span>
                </button>
            </div>
            <div id="ocr-loading" class="hidden px-4 text-center text-xs text-amber-700 font-semibold py-1 bg-amber-50 animate-pulse">
                Gemini AI가 영수증을 분석하고 있습니다... ⏳
            </div>

            <!-- 거래 입력 폼 -->
            <div class="p-4 border-b bg-gray-50 space-y-3">
                <div class="grid grid-cols-2 gap-2 bg-gray-200 p-1 rounded-lg">
                    <button type="button" id="tab-expense" class="py-2 text-sm font-bold rounded-md bg-red-500 text-white transition">지출 (-)</button>
                    <button type="button" id="tab-income" class="py-2 text-sm font-bold rounded-md text-gray-600 transition">수입 (+)</button>
                </div>

                <form id="tx-form" class="space-y-3">
                    <input type="hidden" id="tx-id">
                    
                    <div>
                        <input type="number" id="tx-amount" placeholder="금액 입력 (원)" required class="w-full text-base border p-2.5 rounded-lg bg-white font-bold text-right">
                    </div>

                    <div>
                        <label class="block text-[11px] font-bold text-gray-600 mb-1.5">카테고리 선택</label>
                        <div id="category-chips" class="flex flex-wrap gap-1.5"></div>
                        <input type="text" id="tx-custom-category" placeholder="원하는 카테고리 직접 입력 가능" class="w-full mt-2 border p-2 rounded text-xs bg-white">
                    </div>

                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label class="block text-[11px] text-gray-500 mb-0.5">날짜</label>
                            <input type="date" id="tx-date" required class="w-full border p-2 rounded text-xs bg-white">
                        </div>
                        <div>
                            <label class="block text-[11px] text-gray-500 mb-0.5">결제수단</label>
                            <div class="flex gap-1">
                                <button type="button" class="pay-chip flex-1 py-1.5 text-xs font-semibold rounded border border-blue-600 bg-blue-600 text-white" data-pay="카드">카드</button>
                                <button type="button" class="pay-chip flex-1 py-1.5 text-xs font-semibold rounded border border-gray-300 bg-white text-gray-600" data-pay="현금">현금</button>
                                <button type="button" class="pay-chip flex-1 py-1.5 text-xs font-semibold rounded border border-gray-300 bg-white text-gray-600" data-pay="이체">이체</button>
                            </div>
                        </div>
                    </div>

                    <input type="text" id="tx-memo" placeholder="메모 (예: 점심 식사, 장보기)" class="w-full border p-2 rounded text-xs bg-white">

                    <div class="flex gap-2 pt-1">
                        <button type="submit" id="btn-submit" class="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-bold shadow hover:bg-blue-700 transition">추가하기</button>
                        <button type="button" id="btn-cancel-edit" class="hidden px-4 bg-gray-300 text-gray-700 py-2.5 rounded-lg text-sm font-bold">취소</button>
                    </div>
                </form>
            </div>

            <!-- 대시보드 및 목록 -->
            <div class="p-4 flex-1 space-y-5">
                <div class="bg-white p-3 rounded-lg border shadow-sm">
                    <h2 class="font-bold text-xs text-gray-600 mb-2">📊 지출 요약 차트</h2>
                    <div class="w-full h-44 flex justify-center items-center">
                        <canvas id="categoryChart"></canvas>
                    </div>
                </div>

                <div class="bg-gradient-to-r from-emerald-50 to-teal-50 p-3.5 rounded-lg border border-emerald-200 shadow-sm">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-xs text-emerald-800">🤖 부부 재정 AI 코칭</span>
                        <span class="text-[10px] bg-emerald-200 text-emerald-800 px-1.5 py-0.5 rounded">gemini-3.6-flash</span>
                    </div>
                    <button id="btn-ai-analyze" class="w-full bg-emerald-600 text-white py-2 rounded text-xs font-bold hover:bg-emerald-700 shadow transition">
                        이번 달 지출 패턴 분석 및 절약 조언 받기
                    </button>
                    <div id="ai-result" class="hidden mt-2.5 p-3 bg-white border border-emerald-200 rounded text-xs leading-relaxed text-gray-700 whitespace-pre-line"></div>
                </div>

                <div>
                    <div class="flex justify-between items-center mb-2">
                        <h2 class="font-bold text-xs text-gray-600">📝 내역 목록 (<span id="tx-count">0</span>건)</h2>
                        <button id="btn-export-csv" class="text-xs text-blue-600 hover:underline">CSV 내보내기</button>
                    </div>
                    <ul id="tx-list" class="space-y-2"></ul>
                </div>
            </div>
        </div>

        <!-- [서브 탭: 고정지출 상세 관리 뷰] -->
        <div id="view-fixed" class="hidden flex-1 p-4 space-y-4">
            <div class="bg-orange-50 border border-orange-200 p-3 rounded-lg text-xs text-orange-800">
                📌 <strong>고정지출 관리</strong><br>
                등록된 고정지출은 상단 요약 카드에 즉시 합산되며, 매월 날짜에 맞춰 가계부 내역에도 자동 반영됩니다.
            </div>

            <form id="fixed-form" class="bg-white p-3.5 border rounded-lg shadow-sm space-y-3">
                <input type="hidden" id="fixed-id">
                <h3 class="font-bold text-xs text-gray-700 border-b pb-1">고정지출 항목 등록 / 수정</h3>
                
                <div class="grid grid-cols-2 gap-2">
                    <input type="text" id="fixed-name" placeholder="항목명 (예: 관리비, 대출)" required class="border p-2 rounded text-xs bg-gray-50">
                    <input type="number" id="fixed-amount" placeholder="금액 (원)" required class="border p-2 rounded text-xs bg-gray-50 font-bold">
                </div>

                <div class="grid grid-cols-3 gap-2">
                    <div>
                        <label class="block text-[10px] text-gray-500 mb-0.5">매월 출금일</label>
                        <select id="fixed-day" class="w-full border p-1.5 rounded text-xs bg-gray-50"></select>
                    </div>
                    <div>
                        <label class="block text-[10px] text-gray-500 mb-0.5">카테고리</label>
                        <select id="fixed-category" class="w-full border p-1.5 rounded text-xs bg-gray-50">
                            <option value="주거/통신">주거/통신</option>
                            <option value="금융/대출">금융/대출</option>
                            <option value="보험/세금">보험/세금</option>
                            <option value="생활/문화">생활/문화</option>
                            <option value="기타">기타</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-[10px] text-gray-500 mb-0.5">결제방식</label>
                        <select id="fixed-payment" class="w-full border p-1.5 rounded text-xs bg-gray-50">
                            <option value="계좌이체">계좌이체</option>
                            <option value="카드">카드</option>
                            <option value="현금">현금</option>
                        </select>
                    </div>
                </div>

                <input type="text" id="fixed-memo" placeholder="세부 메모 (예: 국민은행 자동이체)" class="w-full border p-2 rounded text-xs bg-gray-50">

                <div class="flex gap-2">
                    <button type="submit" id="btn-fixed-submit" class="flex-1 bg-orange-600 text-white py-2 rounded text-xs font-bold hover:bg-orange-700 shadow">고정지출 저장</button>
                    <button type="button" id="btn-fixed-cancel" class="hidden px-3 bg-gray-300 text-gray-700 py-2 rounded text-xs font-bold">취소</button>
                </div>
            </form>

            <div>
                <h3 class="font-bold text-xs text-gray-700 mb-2">📋 등록된 고정지출 목록 (출금일순)</h3>
                <ul id="fixed-list" class="space-y-2"></ul>
            </div>
        </div>
    </div>

    <script>
        let currentPin = localStorage.getItem('family_pin') || '';
        let currentType = 'expense';
        let currentCategory = '식비';
        let currentPayment = '카드';
        let transactions = [];
        let fixedExpenses = [];
        let chartInstance = null;
        let isFixedView = false;

        const expenseCategories = ['식비', '주유/교통', '마트/쇼핑', '생활/문화', '주거/통신', '금융/대출', '기타'];
        const incomeCategories = ['내 급여(10일)', '아내 급여(30일)', '기타 수입'];

        const daySelect = document.getElementById('fixed-day');
        for (let d = 1; d <= 31; d++) {
            const opt = document.createElement('option');
            opt.value = d;
            opt.innerText = `매월 ${d}일`;
            daySelect.appendChild(opt);
        }

        document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
        document.getElementById('current-month').innerText = `${new Date().getFullYear()}년 ${new Date().getMonth() + 1}월`;

        async function verifyAndEnter(pin) {
            const res = await fetch('/api/verify-pin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pin: pin })
            });
            const data = await res.json();
            if (data.valid) {
                currentPin = pin;
                localStorage.setItem('family_pin', pin);
                document.getElementById('pin-error').classList.add('hidden');
                document.getElementById('pin-screen').classList.add('hidden');
                document.getElementById('main-app').classList.remove('hidden');
                loadAllData();
            } else {
                localStorage.removeItem('family_pin');
                document.getElementById('pin-error').classList.remove('hidden');
                document.getElementById('pin-screen').classList.remove('hidden');
                document.getElementById('main-app').classList.add('hidden');
            }
        }

        if (currentPin) verifyAndEnter(currentPin);

        document.getElementById('btn-unlock').addEventListener('click', () => {
            const val = document.getElementById('input-pin').value.trim();
            if (val.length !== 6) return alert('6자리 숫자를 입력해 주세요.');
            verifyAndEnter(val);
        });

        document.getElementById('btn-lock').addEventListener('click', () => {
            localStorage.removeItem('family_pin');
            currentPin = '';
            document.getElementById('input-pin').value = '';
            document.getElementById('pin-error').classList.add('hidden');
            document.getElementById('pin-screen').classList.remove('hidden');
            document.getElementById('main-app').classList.add('hidden');
        });

        document.getElementById('btn-toggle-view').addEventListener('click', () => {
            isFixedView = !isFixedView;
            if (isFixedView) {
                document.getElementById('view-transactions').classList.add('hidden');
                document.getElementById('view-fixed').classList.remove('hidden');
                document.getElementById('btn-toggle-view').innerText = '가계부 메인';
            } else {
                document.getElementById('view-transactions').classList.remove('hidden');
                document.getElementById('view-fixed').classList.add('hidden');
                document.getElementById('btn-toggle-view').innerText = '고정지출 관리';
            }
            loadAllData();
        });

        function renderCategoryChips() {
            const container = document.getElementById('category-chips');
            container.innerHTML = '';
            const list = currentType === 'expense' ? expenseCategories : incomeCategories;
            
            if (!list.includes(currentCategory)) {
                currentCategory = list[0];
            }

            list.forEach(cat => {
                const btn = document.createElement('button');
                btn.type = 'button';
                const isSelected = cat === currentCategory;
                btn.className = `px-2.5 py-1.5 rounded text-xs font-semibold transition border ${
                    isSelected ? 'bg-blue-600 text-white border-blue-600 shadow-sm' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                }`;
                btn.innerText = cat;
                btn.addEventListener('click', () => {
                    currentCategory = cat;
                    document.getElementById('tx-custom-category').value = '';
                    renderCategoryChips();
                });
                container.appendChild(btn);
            });
        }

        document.getElementById('tab-expense').addEventListener('click', () => {
            currentType = 'expense';
            document.getElementById('tab-expense').className = 'py-2 text-sm font-bold rounded-md bg-red-500 text-white transition';
            document.getElementById('tab-income').className = 'py-2 text-sm font-bold rounded-md text-gray-600 transition';
            renderCategoryChips();
        });

        document.getElementById('tab-income').addEventListener('click', () => {
            currentType = 'income';
            document.getElementById('tab-income').className = 'py-2 text-sm font-bold rounded-md bg-blue-600 text-white transition';
            document.getElementById('tab-expense').className = 'py-2 text-sm font-bold rounded-md text-gray-600 transition';
            renderCategoryChips();
        });

        document.querySelectorAll('.pay-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                currentPayment = btn.getAttribute('data-pay');
                document.querySelectorAll('.pay-chip').forEach(b => {
                    b.className = 'pay-chip flex-1 py-1.5 text-xs font-semibold rounded border border-gray-300 bg-white text-gray-600';
                });
                btn.className = 'pay-chip flex-1 py-1.5 text-xs font-semibold rounded border border-blue-600 bg-blue-600 text-white';
            });
        });

        document.getElementById('btn-camera').addEventListener('click', () => {
            document.getElementById('receipt-camera').click();
        });

        document.getElementById('receipt-camera').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const loadingEl = document.getElementById('ocr-loading');
            loadingEl.classList.remove('hidden');

            const reader = new FileReader();
            reader.onload = async () => {
                const base64Data = reader.result.split(',')[1];
                const mimeType = file.type || 'image/jpeg';

                try {
                    const res = await fetch('/api/receipt-ocr', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: base64Data, mimeType: mimeType, pin: currentPin })
                    });
                    const data = await res.json();
                    loadingEl.classList.add('hidden');

                    if (data.amount) document.getElementById('tx-amount').value = data.amount;
                    if (data.date) document.getElementById('tx-date').value = data.date;
                    if (data.memo) document.getElementById('tx-memo').value = data.memo;

                    document.getElementById('tab-expense').click();

                    if (data.category && expenseCategories.includes(data.category)) {
                        currentCategory = data.category;
                        document.getElementById('tx-custom-category').value = '';
                    } else if (data.category) {
                        currentCategory = '기타';
                        document.getElementById('tx-custom-category').value = data.category;
                    }
                    renderCategoryChips();
                    alert('영수증 인식이 완료되었습니다. 확인 후 [추가하기]를 눌러주세요.');
                } catch (err) {
                    loadingEl.classList.add('hidden');
                    alert('영수증 인식 실패: ' + err.message);
                }
            };
            reader.readAsDataURL(file);
            e.target.value = '';
        });

        async function loadAllData() {
            try {
                const [txRes, fixedRes] = await Promise.all([
                    fetch(`/api/transactions?pin=${currentPin}`),
                    fetch(`/api/fixed-expenses?pin=${currentPin}`)
                ]);
                transactions = await txRes.json();
                fixedExpenses = await fixedRes.json();
                renderSummary();
                renderList();
                renderFixedList();
                renderChart();
            } catch (err) {
                console.error(err);
            }
        }

        function renderSummary() {
            let income = 0;
            let variableSum = 0;

            transactions.forEach(t => {
                if (t.type === 'income') {
                    income += Number(t.amount);
                } else if (t.type === 'expense' && t.is_fixed === 0) {
                    variableSum += Number(t.amount);
                }
            });

            // 등록된 고정지출 총합을 직접 계산하여 상단에 즉시 표시
            let fixedSum = 0;
            fixedExpenses.forEach(f => {
                fixedSum += Number(f.amount);
            });

            document.getElementById('total-income').innerText = income.toLocaleString() + '원';
            document.getElementById('total-fixed').innerText = fixedSum.toLocaleString() + '원';
            document.getElementById('total-variable').innerText = variableSum.toLocaleString() + '원';
            
            const bal = income - (fixedSum + variableSum);
            const balEl = document.getElementById('balance');
            balEl.innerText = bal.toLocaleString() + '원';
            balEl.className = `text-xs font-bold truncate mt-0.5 ${bal < 0 ? 'text-red-500' : 'text-gray-800'}`;
            document.getElementById('tx-count').innerText = transactions.length;
        }

        function renderList() {
            const listEl = document.getElementById('tx-list');
            listEl.innerHTML = '';
            if (!transactions.length) {
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
                            ${t.is_fixed === 1 ? '<span class="text-[9px] bg-orange-100 text-orange-700 px-1 py-0.5 rounded font-bold">고정</span>' : ''}
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

        function renderFixedList() {
            const listEl = document.getElementById('fixed-list');
            listEl.innerHTML = '';
            if (!fixedExpenses.length) {
                listEl.innerHTML = '<li class="text-center text-xs text-gray-400 py-6">등록된 매월 고정지출이 없습니다.</li>';
                return;
            }

            fixedExpenses.forEach(f => {
                const li = document.createElement('li');
                li.className = 'p-3 bg-white rounded-lg border border-orange-100 shadow-sm flex justify-between items-center';
                li.innerHTML = `
                    <div class="min-w-0 pr-2">
                        <div class="flex items-center gap-1.5">
                            <span class="text-xs font-bold text-orange-700 bg-orange-50 px-1.5 py-0.5 rounded border border-orange-200">매월 ${f.due_day}일</span>
                            <span class="font-bold text-xs text-gray-800">${f.name}</span>
                            <span class="text-[10px] text-gray-500">${f.category} · ${f.payment}</span>
                        </div>
                        <div class="text-[11px] text-gray-400 truncate mt-0.5">${f.memo || '메모 없음'}</div>
                    </div>
                    <div class="text-right flex-shrink-0">
                        <div class="font-bold text-sm text-red-500">-${Number(f.amount).toLocaleString()}원</div>
                        <div class="space-x-1.5 mt-0.5">
                            <button onclick="editFixed(${f.id})" class="text-[10px] text-blue-500 hover:underline">수정</button>
                            <button onclick="deleteFixed(${f.id})" class="text-[10px] text-red-400 hover:underline">삭제</button>
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
            const customCat = document.getElementById('tx-custom-category').value.trim();
            const category = customCat || currentCategory;

            const payload = {
                pin: currentPin,
                type: currentType,
                amount: parseInt(document.getElementById('tx-amount').value, 10),
                date: document.getElementById('tx-date').value,
                category: category,
                payment: currentPayment,
                memo: document.getElementById('tx-memo').value
            };

            if (id) {
                await fetch(`/api/transactions/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                resetForm();
            } else {
                await fetch('/api/transactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                document.getElementById('tx-amount').value = '';
                document.getElementById('tx-memo').value = '';
                document.getElementById('tx-custom-category').value = '';
            }
            loadAllData();
        });

        function editTx(id) {
            const t = transactions.find(item => item.id === id);
            if (!t) return;
            document.getElementById('tx-id').value = t.id;
            document.getElementById('tx-amount').value = t.amount;
            document.getElementById('tx-date').value = t.date;
            document.getElementById('tx-memo').value = t.memo || '';

            if (t.type === 'expense') document.getElementById('tab-expense').click();
            else document.getElementById('tab-income').click();

            const list = t.type === 'expense' ? expenseCategories : incomeCategories;
            if (list.includes(t.category)) {
                currentCategory = t.category;
                document.getElementById('tx-custom-category').value = '';
            } else {
                document.getElementById('tx-custom-category').value = t.category;
            }
            renderCategoryChips();

            document.querySelectorAll('.pay-chip').forEach(b => {
                if (b.getAttribute('data-pay') === t.payment) b.click();
            });

            document.getElementById('btn-submit').innerText = '수정 완료';
            document.getElementById('btn-submit').className = 'flex-1 bg-amber-600 text-white py-2.5 rounded-lg text-sm font-bold shadow hover:bg-amber-700';
            document.getElementById('btn-cancel-edit').classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        document.getElementById('btn-cancel-edit').addEventListener('click', resetForm);

        function resetForm() {
            document.getElementById('tx-id').value = '';
            document.getElementById('tx-amount').value = '';
            document.getElementById('tx-memo').value = '';
            document.getElementById('tx-custom-category').value = '';
            document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
            document.getElementById('btn-submit').innerText = '추가하기';
            document.getElementById('btn-submit').className = 'flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-bold shadow hover:bg-blue-700';
            document.getElementById('btn-cancel-edit').classList.add('hidden');
        }

        async function deleteTx(id) {
            if (confirm('이 내역을 삭제하시겠습니까?')) {
                await fetch(`/api/transactions/${id}?pin=${currentPin}`, { method: 'DELETE' });
                loadAllData();
            }
        }

        document.getElementById('fixed-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('fixed-id').value;
            const payload = {
                pin: currentPin,
                name: document.getElementById('fixed-name').value.trim(),
                amount: parseInt(document.getElementById('fixed-amount').value, 10),
                due_day: parseInt(document.getElementById('fixed-day').value, 10),
                category: document.getElementById('fixed-category').value,
                payment: document.getElementById('fixed-payment').value,
                memo: document.getElementById('fixed-memo').value.trim()
            };

            if (id) {
                await fetch(`/api/fixed-expenses/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                resetFixedForm();
            } else {
                await fetch('/api/fixed-expenses', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                resetFixedForm();
            }
            await loadAllData();
            alert('고정지출이 저장되었으며 상단 합계 및 이번 달 내역에 즉시 반영되었습니다.');
        });

        function editFixed(id) {
            const f = fixedExpenses.find(item => item.id === id);
            if (!f) return;
            document.getElementById('fixed-id').value = f.id;
            document.getElementById('fixed-name').value = f.name;
            document.getElementById('fixed-amount').value = f.amount;
            document.getElementById('fixed-day').value = f.due_day;
            document.getElementById('fixed-category').value = f.category;
            document.getElementById('fixed-payment').value = f.payment;
            document.getElementById('fixed-memo').value = f.memo || '';

            document.getElementById('btn-fixed-submit').innerText = '고정지출 수정 완료';
            document.getElementById('btn-fixed-cancel').classList.remove('hidden');
        }

        document.getElementById('btn-fixed-cancel').addEventListener('click', resetFixedForm);

        function resetFixedForm() {
            document.getElementById('fixed-id').value = '';
            document.getElementById('fixed-name').value = '';
            document.getElementById('fixed-amount').value = '';
            document.getElementById('fixed-memo').value = '';
            document.getElementById('fixed-day').value = 1;
            document.getElementById('btn-fixed-submit').innerText = '고정지출 저장';
            document.getElementById('btn-fixed-cancel').classList.add('hidden');
        }

        async function deleteFixed(id) {
            if (confirm('이 고정지출을 삭제하시겠습니까?')) {
                await fetch(`/api/fixed-expenses/${id}?pin=${currentPin}`, { method: 'DELETE' });
                loadAllData();
            }
        }

        document.getElementById('btn-export-csv').addEventListener('click', () => {
            if (!transactions.length) return alert('저장할 내역이 없습니다.');
            let csv = "날짜,구분,카테고리,금액,결제수단,메모,고정여부\\n";
            transactions.forEach(t => {
                csv += `"${t.date}","${t.type === 'expense' ? '지출' : '수입'}","${t.category}",${t.amount},"${t.payment}","${t.memo || ''}","${t.is_fixed ? '고정지출' : '일반'}"\\n`;
            });
            const blob = new Blob(["\\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('link');
            link.href = URL.createObjectURL(blob);
            link.download = `부부가계부_${new Date().toISOString().slice(0,10)}.csv`;
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
                    body: JSON.stringify({ transactions, pin: currentPin })
                });
                const data = await res.json();
                resEl.innerText = data.analysis || '분석을 완료하지 못했습니다.';
            } catch (err) {
                resEl.innerText = '통신 에러: ' + err.message;
            }
        });

        renderCategoryChips();
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
        "name": "부부 스마트 가계부 (money-app)",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/2331/2331941.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ],
        "start_url": "/",
        "background_color": "#ffffff",
        "theme_color": "#2563eb",
        "display": "standalone"
    })

@app.route("/api/verify-pin", methods=["POST"])
def verify_pin():
    data = request.get_json() or {}
    pin = data.get("pin", "")
    return jsonify({"valid": (pin == CORRECT_PIN)})

@app.route("/api/transactions", methods=["GET", "POST"])
def handle_transactions():
    pin = request.args.get("pin") if request.method == "GET" else (request.get_json() or {}).get("pin")
    if pin != CORRECT_PIN:
        return jsonify({"error": "인증 실패"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "GET":
        sync_fixed_expenses_for_current_month()
        cursor.execute("SELECT id, type, amount, date, category, payment, memo, is_fixed FROM transactions ORDER BY date DESC, id DESC")
        rows = cursor.fetchall()
        data = [
            {"id": r[0], "type": r[1], "amount": r[2], "date": r[3], "category": r[4], "payment": r[5], "memo": r[6], "is_fixed": r[7]}
            for r in rows
        ]
        conn.close()
        return jsonify(data)

    elif request.method == "POST":
        req = request.get_json() or {}
        cursor.execute("""
            INSERT INTO transactions (type, amount, date, category, payment, memo, is_fixed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (req.get("type"), req.get("amount"), req.get("date"), req.get("category"), req.get("payment"), req.get("memo", "")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})

@app.route("/api/transactions/<int:tx_id>", methods=["PUT", "DELETE"])
def modify_transaction(tx_id):
    pin = request.args.get("pin") if request.method == "DELETE" else (request.get_json() or {}).get("pin")
    if pin != CORRECT_PIN:
        return jsonify({"error": "인증 실패"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "PUT":
        req = request.get_json() or {}
        cursor.execute("""
            UPDATE transactions
            SET type = ?, amount = ?, date = ?, category = ?, payment = ?, memo = ?
            WHERE id = ?
        """, (req.get("type"), req.get("amount"), req.get("date"), req.get("category"), req.get("payment"), req.get("memo", ""), tx_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "updated"})

    elif request.method == "DELETE":
        cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"})

@app.route("/api/fixed-expenses", methods=["GET", "POST"])
def handle_fixed_expenses():
    pin = request.args.get("pin") if request.method == "GET" else (request.get_json() or {}).get("pin")
    if pin != CORRECT_PIN:
        return jsonify({"error": "인증 실패"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "GET":
        cursor.execute("SELECT id, name, amount, due_day, category, payment, memo FROM fixed_expenses ORDER BY due_day ASC")
        rows = cursor.fetchall()
        data = [
            {"id": r[0], "name": r[1], "amount": r[2], "due_day": r[3], "category": r[4], "payment": r[5], "memo": r[6]}
            for r in rows
        ]
        conn.close()
        return jsonify(data)

    elif request.method == "POST":
        req = request.get_json() or {}
        cursor.execute("""
            INSERT INTO fixed_expenses (name, amount, due_day, category, payment, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.get("name"), req.get("amount"), req.get("due_day"), req.get("category"), req.get("payment"), req.get("memo", "")))
        conn.commit()
        conn.close()
        sync_fixed_expenses_for_current_month()
        return jsonify({"status": "success"})

@app.route("/api/fixed-expenses/<int:item_id>", methods=["PUT", "DELETE"])
def modify_fixed_expenses(item_id):
    pin = request.args.get("pin") if request.method == "DELETE" else (request.get_json() or {}).get("pin")
    if pin != CORRECT_PIN:
        return jsonify({"error": "인증 실패"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "PUT":
        req = request.get_json() or {}
        cursor.execute("""
            UPDATE fixed_expenses
            SET name = ?, amount = ?, due_day = ?, category = ?, payment = ?, memo = ?
            WHERE id = ?
        """, (req.get("name"), req.get("amount"), req.get("due_day"), req.get("category"), req.get("payment"), req.get("memo", ""), item_id))
        conn.commit()
        conn.close()
        sync_fixed_expenses_for_current_month()
        return jsonify({"status": "updated"})

    elif request.method == "DELETE":
        cursor.execute("DELETE FROM fixed_expenses WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"})

@app.route("/api/receipt-ocr", methods=["POST"])
def receipt_ocr():
    data = request.get_json() or {}
    if data.get("pin") != CORRECT_PIN:
        return jsonify({"error": "인증 실패"}), 403

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY가 없습니다."}), 500

    image_base64 = data.get("image")
    mime_type = data.get("mimeType", "image/jpeg")

    if not image_base64:
        return jsonify({"error": "이미지 데이터가 없습니다."}), 400

    prompt = """
이 영수증 사진을 분석하여 아래 JSON 형식으로만 응답해 주세요. Markdown 코드 블록(```json 등) 없이 순수 JSON 텍스트만 반환하세요:
{
  "amount": 총 결제금액(숫자만, 예: 15000),
  "date": "결제일자(YYYY-MM-DD 형식, 확인 불가 시 오늘 날짜)",
  "memo": "상호명 또는 주요 품목(예: 스타벅스, 이마트)",
  "category": "식비" | "주유/교통" | "마트/쇼핑" | "생활/문화" | "주거/통신" | "금융/대출" | "기타" 중 하나
}
"""
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=){GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_base64
                        }
                    }
                ]
            }
        ]
    }

    try:
        res = requests.post(url, json=payload, timeout=25)
        res_json = res.json()
        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
        parsed = json.loads(raw_text)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": f"OCR 처리 실패: {str(e)}"}), 500

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}
    if data.get("pin") != CORRECT_PIN:
        return jsonify({"error": "인증 실패"}), 403

    if not GEMINI_API_KEY:
        return jsonify({"analysis": "GEMINI_API_KEY가 등록되지 않았습니다."})

    txs = data.get("transactions", [])
    if not txs:
        return jsonify({"analysis": "분석할 데이터가 없습니다."})

    summary_lines = [
        f"[{t['date']}] {t['type']}: {t['category']} {t['amount']}원 ({t.get('payment','')}) / 메모: {t.get('memo','')}"
        for t in txs
    ]
    prompt = f"""
당신은 부부 재정 관리 전문 코치입니다.
부부의 가계부 수입/고정지출/변동지출 내역을 보고 핵심만 직관적으로 피드백해 주세요:

[거래 내역]
{chr(10).join(summary_lines)}

[답변 형식]
1. 이번 달 재정 요약 (총수입 대비 고정비/변동비 흐름)
2. 주요 지출 항목 분석 및 낭비 요인
3. 부부를 위한 실천적 절약 조언 2~3가지
"""
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=){GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, json=payload, timeout=20)
        res_json = res.json()
        text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"analysis": text})
    except Exception as e:
        return jsonify({"analysis": f"AI 분석 실패 ({str(e)})"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
