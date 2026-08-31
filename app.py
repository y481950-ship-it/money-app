<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>우리 부부 가계부</title>
  <!-- Bootstrap 5 CDN -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    .card-stat { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
    .btn-custom { border-radius: 8px; font-weight: 600; }
    .nav-pills .nav-link { color: #555; border-radius: 8px; font-weight: 600; }
    .nav-pills .nav-link.active { background-color: #0d6efd; color: #fff; }
    .badge-fixed { background-color: #6c757d; color: white; font-size: 0.75rem; }
    .tx-item { transition: background-color 0.2s; }
    .tx-item:hover { background-color: #f8f9fa; }
  </style>
</head>
<body class="pb-5">

<!-- 비밀번호 잠금 화면 -->
<div id="pinScreen" class="container d-flex flex-column justify-content-center align-items-center vh-100" style="display: none;">
  <div class="card p-4 shadow-sm text-center" style="max-width: 340px; width: 100%; border-radius: 16px;">
    <h4 class="fw-bold mb-3">🔒 부부 가계부</h4>
    <p class="text-muted small mb-4">비밀번호(PIN)를 입력하세요</p>
    <input type="password" id="pinInput" class="form-control form-control-lg text-center mb-3" placeholder="PIN 입력" maxlength="8">
    <button class="btn btn-primary btn-lg w-100 btn-custom" onclick="unlockApp()">열기</button>
    <div id="pinError" class="text-danger small mt-2" style="display: none;">비밀번호가 올바르지 않습니다.</div>
  </div>
</div>

<!-- 메인 컨텐츠 영역 -->
<div id="mainScreen" class="container py-3" style="max-width: 600px; display: none;">

  <!-- 상단 헤더 & 월 이동 -->
  <div class="bg-primary text-white p-3 rounded-4 shadow-sm mb-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="m-0 fw-bold">💳 우리 부부 가계부</h5>
      <div>
        <button class="btn btn-sm btn-outline-light me-1" onclick="openFixedModal()">고정지출 관리</button>
        <button class="btn btn-sm btn-light text-primary fw-bold" onclick="lockApp()">잠금</button>
      </div>
    </div>
    
    <!-- ◀ 월 이동 ▶ -->
    <div class="d-flex justify-content-center align-items-center gap-3">
      <button class="btn btn-sm btn-outline-light px-3 fw-bold" onclick="changeMonth(-1)">◀</button>
      <h5 class="m-0 fw-bold" id="currentMonthLabel">2026년 8월</h5>
      <button class="btn btn-sm btn-outline-light px-3 fw-bold" onclick="changeMonth(1)">▶</button>
    </div>
  </div>

  <!-- 상단 요약 카드 (4칸) -->
  <div class="row g-2 text-center mb-3">
    <div class="col-3">
      <div class="card p-2 shadow-sm border-0 bg-white">
        <small class="text-muted" style="font-size: 0.75rem;">총수입</small>
        <div class="fw-bold text-primary mt-1" style="font-size: 0.85rem;" id="sumIncome">0원</div>
      </div>
    </div>
    <div class="col-3">
      <div class="card p-2 shadow-sm border-0 bg-white">
        <small class="text-muted" style="font-size: 0.75rem;">고정지출</small>
        <div class="fw-bold text-danger mt-1" style="font-size: 0.85rem;" id="sumFixed">0원</div>
      </div>
    </div>
    <div class="col-3">
      <div class="card p-2 shadow-sm border-0 bg-white">
        <small class="text-muted" style="font-size: 0.75rem;">변동지출</small>
        <div class="fw-bold text-danger mt-1" style="font-size: 0.85rem;" id="sumVariable">0원</div>
      </div>
    </div>
    <div class="col-3">
      <div class="card p-2 shadow-sm border-0 bg-white">
        <small class="text-muted" style="font-size: 0.75rem;">남은잔액</small>
        <div class="fw-bold text-dark mt-1" style="font-size: 0.85rem;" id="sumBalance">0원</div>
      </div>
    </div>
  </div>

  <!-- 📊 지난달 대비 소비 추이 비교 카드 -->
  <div class="card p-3 shadow-sm border-0 bg-white mb-3" id="comparisonCard">
    <h6 class="fw-bold mb-2 text-secondary">📊 지난달 대비 소비 추이</h6>
    <div class="small" id="comparisonContent">
      데이터를 계산 중입니다...
    </div>
  </div>

  <!-- 영수증 촬영/OCR 버튼 -->
  <div class="mb-3">
    <label class="btn btn-warning w-100 py-2 fw-bold text-white shadow-sm" style="border-radius: 10px; cursor: pointer; background-color: #f59f00; border: none;">
      📷 영수증 촬영 / 갤러리 선택
      <input type="file" id="receiptFileInput" accept="image/*" style="display: none;" onchange="handleReceiptUpload(event)">
    </label>
    <div id="ocrLoading" class="text-center text-muted small mt-1" style="display: none;">
      <span class="spinner-border spinner-border-sm text-warning" role="status"></span> 영수증을 분석하고 있습니다...
    </div>
  </div>

  <!-- 거래 내역 입력 폼 카드 -->
  <div class="card p-3 shadow-sm border-0 bg-white mb-3" style="border-radius: 12px;">
    <div class="btn-group w-100 mb-3" role="group">
      <input type="radio" class="btn-check" name="txType" id="typeExpense" value="expense" checked onchange="toggleTypeUI()">
      <label class="btn btn-outline-danger fw-bold" for="typeExpense">지출 (-)</label>

      <input type="radio" class="btn-check" name="txType" id="typeIncome" value="income" onchange="toggleTypeUI()">
      <label class="btn btn-outline-primary fw-bold" for="typeIncome">수입 (+)</label>
    </div>

    <form id="txForm" onsubmit="handleFormSubmit(event)">
      <div class="mb-2">
        <input type="number" id="txAmount" class="form-control form-control-lg text-end fw-bold" placeholder="금액 입력 (원)" required>
      </div>

      <div class="row g-2 mb-2">
        <div class="col-6">
          <input type="date" id="txDate" class="form-control" required>
        </div>
        <div class="col-6">
          <select id="txCategory" class="form-select" required>
            <option value="식비">식비</option>
            <option value="외식">외식</option>
            <option value="교통/차량">교통/차량</option>
            <option value="마트/생필품">마트/생필품</option>
            <option value="의료/건강">의료/건강</option>
            <option value="문화/여가">문화/여가</option>
            <option value="경조사/선물">경조사/선물</option>
            <option value="급여">급여</option>
            <option value="상여금">상여금</option>
            <option value="기타">기타</option>
          </select>
        </div>
      </div>

      <div class="row g-2 mb-2">
        <div class="col-6">
          <select id="txPayment" class="form-select">
            <option value="카드">카드</option>
            <option value="현금">현금</option>
            <option value="계좌이체">계좌이체</option>
          </select>
        </div>
        <div class="col-6">
          <input type="text" id="txMemo" class="form-control" placeholder="메모 / 사용처">
        </div>
      </div>

      <button type="submit" class="btn btn-primary w-100 fw-bold py-2 mt-2" style="border-radius: 8px;">내역 등록</button>
    </form>
  </div>

  <!-- AI 부부 재정 코칭 버튼 및 결과창 -->
  <div class="card p-3 shadow-sm border-0 bg-white mb-3" style="border-radius: 12px;">
    <button class="btn btn-outline-info w-100 fw-bold py-2" onclick="fetchAIAnalysis()">
      🤖 AI 재정 코치 분석 받기
    </button>
    <div id="aiLoading" class="text-center text-muted small mt-2" style="display: none;">
      <span class="spinner-border spinner-border-sm text-info"></span> AI가 가계부를 꼼꼼히 분석하고 있습니다...
    </div>
    <div id="aiResultBox" class="mt-3 p-3 bg-light rounded text-dark small" style="display: none; white-space: pre-wrap; line-height: 1.6;"></div>
  </div>

  <!-- 탭 메뉴 (내역 목록 / 소비 통계 차트) -->
  <ul class="nav nav-pills nav-fill mb-3" id="pills-tab" role="tablist">
    <li class="nav-item">
      <button class="nav-link active" id="tab-list-btn" data-bs-toggle="pill" data-bs-target="#tab-list">거래 목록</button>
    </li>
    <li class="nav-item">
      <button class="nav-link" id="tab-chart-btn" data-bs-toggle="pill" data-bs-target="#tab-chart" onclick="renderCategoryChart()">소비 분석 차트</button>
    </li>
  </ul>

  <!-- 탭 본문 -->
  <div class="tab-content" id="pills-tabContent">
    <!-- 1. 거래 내역 리스트 -->
    <div class="tab-pane fade show active" id="tab-list">
      <div class="card border-0 shadow-sm bg-white p-2" style="border-radius: 12px;">
        <div id="transactionList" class="list-group list-group-flush">
          <!-- 동적 렌더링 -->
        </div>
      </div>
    </div>

    <!-- 2. 카테고리별 차트 -->
    <div class="tab-pane fade" id="tab-chart">
      <div class="card border-0 shadow-sm bg-white p-3 text-center" style="border-radius: 12px;">
        <h6 class="fw-bold mb-3">카테고리별 지출 비율</h6>
        <div style="position: relative; height:260px;">
          <canvas id="categoryChart"></canvas>
        </div>
      </div>
    </div>
  </div>

</div>

<!-- 고정지출 관리 모달 -->
<div class="modal fade" id="fixedModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content" style="border-radius: 16px;">
      <div class="modal-header">
        <h5 class="modal-title fw-bold">📌 매월 고정지출 관리</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <form id="fixedExpenseForm" class="row g-2 mb-3" onsubmit="handleAddFixed(event)">
          <div class="col-4">
            <input type="text" id="fixedName" class="form-control" placeholder="항목명 (예: 관리비)" required>
          </div>
          <div class="col-4">
            <input type="number" id="fixedAmount" class="form-control" placeholder="금액 (원)" required>
          </div>
          <div class="col-2">
            <input type="number" id="fixedDay" class="form-control" placeholder="날짜" min="1" max="31">
          </div>
          <div class="col-2">
            <button type="submit" class="btn btn-danger w-100 fw-bold">추가</button>
          </div>
        </form>
        <hr>
        <div id="fixedExpenseList" class="list-group list-group-flush" style="max-height: 280px; overflow-y: auto;">
          <!-- 고정지출 항목들 동적 표시 -->
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Bootstrap 5 JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
let currentPin = sessionStorage.getItem("app_pin") || "";
let allTransactions = [];
let fixedExpenses = [];
let viewDate = new Date();
let chartInstance = null;
let fixedModalInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  fixedModalInstance = new bootstrap.Modal(document.getElementById('fixedModal'));
  document.getElementById('txDate').value = new Date().toISOString().substring(0, 10);
  
  if (currentPin) {
    checkPinAndLoad(currentPin);
  } else {
    document.getElementById("pinScreen").style.display = "flex";
  }
});

function unlockApp() {
  const pin = document.getElementById("pinInput").value.trim();
  checkPinAndLoad(pin);
}

function checkPinAndLoad(pin) {
  fetch("/api/data?pin=" + encodeURIComponent(pin))
    .then(res => {
      if (!res.ok) throw new Error("인증 실패");
      return res.json();
    })
    .then(data => {
      currentPin = pin;
      sessionStorage.setItem("app_pin", pin);
      document.getElementById("pinScreen").style.display = "none";
      document.getElementById("mainScreen").style.display = "block";
      allTransactions = data.transactions || [];
      fixedExpenses = data.fixed_expenses || [];
      renderDashboard();
    })
    .catch(() => {
      document.getElementById("pinError").style.display = "block";
      document.getElementById("pinScreen").style.display = "flex";
      document.getElementById("mainScreen").style.display = "none";
    });
}

function lockApp() {
  sessionStorage.removeItem("app_pin");
  currentPin = "";
  document.getElementById("pinInput").value = "";
  document.getElementById("pinError").style.display = "none";
  document.getElementById("mainScreen").style.display = "none";
  document.getElementById("pinScreen").style.display = "flex";
}

// ◀ ▶ 월 이동 함수
function changeMonth(offset) {
  viewDate.setMonth(viewDate.getMonth() + offset);
  renderDashboard();
}

function renderDashboard() {
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth() + 1;
  const curPrefix = `${year}-${String(month).padStart(2, '0')}`;
  
  // 이전 달 prefix
  const prevDate = new Date(viewDate);
  prevDate.setMonth(prevDate.getMonth() - 1);
  const prevPrefix = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;

  document.getElementById('currentMonthLabel').innerText = `${year}년 ${month}월`;

  // 이번 달 / 지난달 데이터 필터링
  const curTxs = allTransactions.filter(t => (t.date || '').startsWith(curPrefix));
  const prevTxs = allTransactions.filter(t => (t.date || '').startsWith(prevPrefix));

  // 고정지출 총합
  const fixedTotal = fixedExpenses.reduce((acc, cur) => acc + parseInt(cur.amount || 0), 0);

  // 이번 달 계산
  const curIncome = curTxs.filter(t => t.type === 'income').reduce((acc, cur) => acc + parseInt(cur.amount || 0), 0);
  const curVariable = curTxs.filter(t => t.type === 'expense' && !t.is_fixed).reduce((acc, cur) => acc + parseInt(cur.amount || 0), 0);
  const curBalance = curIncome - (fixedTotal + curVariable);

  // 지난달 변동지출 / 식비 계산
  const prevVariable = prevTxs.filter(t => t.type === 'expense' && !t.is_fixed).reduce((acc, cur) => acc + parseInt(cur.amount || 0), 0);
  const curFood = curTxs.filter(t => t.type === 'expense' && !t.is_fixed && (t.category === '식비' || t.category === '외식')).reduce((acc, cur) => acc + parseInt(cur.amount || 0), 0);
  const prevFood = prevTxs.filter(t => t.type === 'expense' && !t.is_fixed && (t.category === '식비' || t.category === '외식')).reduce((acc, cur) => acc + parseInt(cur.amount || 0), 0);

  // 상단 요약 카드 숫자 세팅
  document.getElementById('sumIncome').innerText = curIncome.toLocaleString() + '원';
  document.getElementById('sumFixed').innerText = fixedTotal.toLocaleString() + '원';
  document.getElementById('sumVariable').innerText = curVariable.toLocaleString() + '원';
  document.getElementById('sumBalance').innerText = curBalance.toLocaleString() + '원';

  // 지난달 비교 카드 내용 생성
  const diffVar = curVariable - prevVariable;
  const diffFood = curFood - prevFood;

  let varText = diffVar <= 0 
    ? `지난달(${prevVariable.toLocaleString()}원) 대비 <span class="text-success fw-bold">${Math.abs(diffVar).toLocaleString()}원 절약 중 ▼</span>` 
    : `지난달(${prevVariable.toLocaleString()}원) 대비 <span class="text-danger fw-bold">${diffVar.toLocaleString()}원 초과 중 ▲</span>`;

  let foodText = diffFood <= 0
    ? `지난달(${prevFood.toLocaleString()}원) 대비 <span class="text-success fw-bold">${Math.abs(diffFood).toLocaleString()}원 절약 중 ▼</span>`
    : `지난달(${prevFood.toLocaleString()}원) 대비 <span class="text-danger fw-bold">${diffFood.toLocaleString()}원 초과 중 ▲</span>`;

  document.getElementById('comparisonContent').innerHTML = `
    <div class="mb-1">• <strong>변동지출:</strong> ${curVariable.toLocaleString()}원 (${varText})</div>
    <div>• <strong>식비/외식:</strong> ${curFood.toLocaleString()}원 (${foodText})</div>
  `;

  renderTransactionList(curTxs);
  if (document.getElementById('tab-chart').classList.contains('active')) {
    renderCategoryChart();
  }
}

function renderTransactionList(txs) {
  const container = document.getElementById("transactionList");
  container.innerHTML = "";

  if (txs.length === 0) {
    container.innerHTML = '<div class="text-center text-muted py-4 small">등록된 내역이 없습니다.</div>';
    return;
  }

  // 날짜 내림차순 정렬
  const sorted = [...txs].sort((a, b) => new Date(b.date) - new Date(a.date));

  sorted.forEach(t => {
    const isInc = t.type === 'income';
    const amountColor = isInc ? 'text-primary' : 'text-danger';
    const sign = isInc ? '+' : '-';
    const fixedBadge = t.is_fixed ? '<span class="badge badge-fixed me-1">고정</span>' : '';

    const item = document.createElement("div");
    item.className = "list-group-item d-flex justify-content-between align-items-center py-2 px-1 border-0 border-bottom tx-item";
    item.innerHTML = `
      <div>
        <div class="d-flex align-items-center">
          ${fixedBadge}
          <span class="fw-bold small me-2">${t.category}</span>
          <span class="text-muted" style="font-size: 0.75rem;">${t.memo || ''}</span>
        </div>
        <small class="text-muted" style="font-size: 0.7rem;">${t.date} · ${t.payment || '기타'}</small>
      </div>
      <div class="text-end">
        <span class="fw-bold ${amountColor}" style="font-size: 0.9rem;">${sign}${parseInt(t.amount).toLocaleString()}원</span>
        <button class="btn btn-sm text-muted p-0 ms-2" onclick="deleteTransaction('${t.id}')" style="font-size: 0.8rem;">✕</button>
      </div>
    `;
    container.appendChild(item);
  });
}

function toggleTypeUI() {
  const isExp = document.getElementById("typeExpense").checked;
  const cat = document.getElementById("txCategory");
  if (isExp) {
    cat.innerHTML = `
      <option value="식비">식비</option>
      <option value="외식">외식</option>
      <option value="교통/차량">교통/차량</option>
      <option value="마트/생필품">마트/생필품</option>
      <option value="의료/건강">의료/건강</option>
      <option value="문화/여가">문화/여가</option>
      <option value="경조사/선물">경조사/선물</option>
      <option value="기타">기타</option>
    `;
  } else {
    cat.innerHTML = `
      <option value="급여">급여</option>
      <option value="상여금">상여금</option>
      <option value="부수입">부수입</option>
      <option value="기타">기타</option>
    `;
  }
}

function handleFormSubmit(e) {
  e.preventDefault();
  const txType = document.querySelector('input[name="txType"]:checked').value;
  const payload = {
    pin: currentPin,
    type: txType,
    amount: parseInt(document.getElementById("txAmount").value),
    date: document.getElementById("txDate").value,
    category: document.getElementById("txCategory").value,
    payment: document.getElementById("txPayment").value,
    memo: document.getElementById("txMemo").value
  };

  fetch("/api/transaction", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    allTransactions = data.transactions;
    renderDashboard();
    document.getElementById("txAmount").value = "";
    document.getElementById("txMemo").value = "";
  });
}

function deleteTransaction(id) {
  if (!confirm("해당 내역을 삭제하시겠습니까?")) return;
  fetch("/api/transaction/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin: currentPin, id: id })
  })
  .then(res => res.json())
  .then(data => {
    allTransactions = data.transactions;
    renderDashboard();
  });
}

function handleReceiptUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("pin", currentPin);

  document.getElementById("ocrLoading").style.display = "block";

  fetch("/api/receipt_ocr", {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("ocrLoading").style.display = "none";
    if (data.amount) document.getElementById("txAmount").value = data.amount;
    if (data.date) document.getElementById("txDate").value = data.date;
    if (data.category) document.getElementById("txCategory").value = data.category;
    if (data.memo) document.getElementById("txMemo").value = data.memo;
    if (data.payment) document.getElementById("txPayment").value = data.payment;
    alert("영수증 정보가 자동으로 입력되었습니다. 내역을 확인하고 등록을 눌러주세요.");
  })
  .catch(() => {
    document.getElementById("ocrLoading").style.display = "none";
    alert("영수증 인식에 실패했습니다.");
  });
}

function fetchAIAnalysis() {
  document.getElementById("aiLoading").style.display = "block";
  document.getElementById("aiResultBox").style.display = "none";

  fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin: currentPin })
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("aiLoading").style.display = "none";
    const box = document.getElementById("aiResultBox");
    box.innerText = data.analysis;
    box.style.display = "block";
  })
  .catch(() => {
    document.getElementById("aiLoading").style.display = "none";
    alert("AI 분석 요청 중 오류가 발생했습니다.");
  });
}

function openFixedModal() {
  renderFixedExpenseList();
  fixedModalInstance.show();
}

function renderFixedExpenseList() {
  const list = document.getElementById("fixedExpenseList");
  list.innerHTML = "";
  if (fixedExpenses.length === 0) {
    list.innerHTML = '<div class="text-center text-muted py-2 small">등록된 고정지출이 없습니다.</div>';
    return;
  }
  fixedExpenses.forEach(f => {
    const item = document.createElement("div");
    item.className = "list-group-item d-flex justify-content-between align-items-center py-2 px-1";
    item.innerHTML = `
      <div>
        <strong>${f.name}</strong> <span class="badge bg-light text-dark border ms-1">${f.day ? f.day + '일' : '매월'}</span>
      </div>
      <div>
        <span class="text-danger fw-bold me-2">${parseInt(f.amount).toLocaleString()}원</span>
        <button class="btn btn-sm btn-outline-danger p-0 px-1" onclick="deleteFixed('${f.id}')">✕</button>
      </div>
    `;
    list.appendChild(item);
  });
}

function handleAddFixed(e) {
  e.preventDefault();
  const payload = {
    pin: currentPin,
    name: document.getElementById("fixedName").value,
    amount: parseInt(document.getElementById("fixedAmount").value),
    day: document.getElementById("fixedDay").value
  };

  fetch("/api/fixed_expense", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    fixedExpenses = data.fixed_expenses;
    renderFixedExpenseList();
    renderDashboard();
    document.getElementById("fixedName").value = "";
    document.getElementById("fixedAmount").value = "";
    document.getElementById("fixedDay").value = "";
  });
}

function deleteFixed(id) {
  if (!confirm("고정지출 항목을 삭제하시겠습니까?")) return;
  fetch("/api/fixed_expense/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin: currentPin, id: id })
  })
  .then(res => res.json())
  .then(data => {
    fixedExpenses = data.fixed_expenses;
    renderFixedExpenseList();
    renderDashboard();
  });
}

function renderCategoryChart() {
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth() + 1;
  const curPrefix = `${year}-${String(month).padStart(2, '0')}`;
  const curTxs = allTransactions.filter(t => (t.date || '').startsWith(curPrefix) && t.type === 'expense');

  const catMap = {};
  curTxs.forEach(t => {
    catMap[t.category] = (catMap[t.category] || 0) + parseInt(t.amount);
  });

  const labels = Object.keys(catMap);
  const data = Object.values(catMap);

  const ctx = document.getElementById("categoryChart").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  if (labels.length === 0) {
    labels.push("내역 없음");
    data.push(1);
  }

  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: ['#ff6384', '#36a2eb', '#ffcd56', '#4bc0c0', '#9966ff', '#ff9f40', '#c9cbcf']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });
}
</script>
</body>
</html>
