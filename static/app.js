const API_BASE = '/api/fund';
let chartInstance = null;
let selectedFund = null;

// --- Search ---
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const searchDropdown = document.getElementById('search-dropdown');

async function doSearch() {
    const keyword = searchInput.value.trim();
    if (!keyword) return;
    const resp = await fetch(`${API_BASE}/search?keyword=${encodeURIComponent(keyword)}`);
    const funds = await resp.json();
    renderDropdown(funds);
}

function renderDropdown(funds) {
    if (!funds.length) {
        searchDropdown.innerHTML = '<div class="dropdown-item">无匹配结果</div>';
        searchDropdown.classList.remove('hidden');
        return;
    }
    searchDropdown.innerHTML = funds.map(f =>
        `<div class="dropdown-item" data-code="${f.code}" data-name="${f.name}" data-category="${f.category_name}">
            <span><span class="code">${f.code}</span> ${f.name}</span>
            <span class="category">${f.category_name}</span>
        </div>`
    ).join('');
    searchDropdown.classList.remove('hidden');

    searchDropdown.querySelectorAll('.dropdown-item[data-code]').forEach(item => {
        item.addEventListener('click', () => {
            selectedFund = {
                code: item.dataset.code,
                name: item.dataset.name,
                category: item.dataset.category
            };
            searchInput.value = `${selectedFund.code} ${selectedFund.name}`;
            searchDropdown.classList.add('hidden');
            queryPerformance();
        });
    });
}

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
document.addEventListener('click', e => {
    if (!searchDropdown.contains(e.target) && e.target !== searchInput) {
        searchDropdown.classList.add('hidden');
    }
});

// --- Load categories ---
async function loadCategories() {
    const resp = await fetch(`${API_BASE}/categories`);
    const cats = await resp.json();
    const select = document.getElementById('category-select');
    cats.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });
}

loadCategories();

// --- Set default dates (last 3 months) ---
function setDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 3);
    document.getElementById('end-date').value = formatDate(end);
    document.getElementById('start-date').value = formatDate(start);
}

function formatDate(d) {
    return d.toISOString().split('T')[0];
}

setDefaultDates();

// --- Query performance ---
async function queryPerformance() {
    if (!selectedFund) return;
    const start = document.getElementById('start-date').value;
    const end = document.getElementById('end-date').value;
    if (!start || !end) return;

    const resp = await fetch(`${API_BASE}/performance?code=${selectedFund.code}&start=${start}&end=${end}`);
    const data = await resp.json();
    renderFundResult(data);
}

function renderFundResult(weeklyData) {
    const area = document.getElementById('result-area');
    let html = `<div class="fund-card">
        <div class="fund-name">${selectedFund.name}</div>
        <div class="fund-meta">${selectedFund.code} | ${selectedFund.category}</div>
    </div>`;

    if (!weeklyData.length) {
        html += '<div class="empty-state">该时间段内无数据</div>';
        area.innerHTML = html;
        return;
    }

    html += '<table><thead><tr><th>周起始日</th><th>周结束日</th><th>周涨跌幅</th></tr></thead><tbody>';
    weeklyData.forEach(w => {
        const cls = w.change_pct >= 0 ? 'change-positive' : 'change-negative';
        const sign = w.change_pct >= 0 ? '+' : '';
        html += `<tr><td>${w.week_start}</td><td>${w.week_end}</td><td class="${cls}">${sign}${w.change_pct.toFixed(2)}%</td></tr>`;
    });
    html += '</tbody></table>';
    html += '<div class="chart-container"><canvas id="weekly-chart"></canvas></div>';
    area.innerHTML = html;

    renderChart(weeklyData);
}

function renderChart(weeklyData) {
    if (chartInstance) chartInstance.destroy();
    const ctx = document.getElementById('weekly-chart').getContext('2d');
    const labels = weeklyData.map(w => w.week_start);
    const values = weeklyData.map(w => w.change_pct);

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: '周涨跌幅(%)',
                data: values,
                borderColor: '#1677ff',
                backgroundColor: 'rgba(22,119,255,0.1)',
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    ticks: { callback: v => v + '%' }
                }
            }
        }
    });
}

// --- Query ranking ---
document.getElementById('query-rank-btn').addEventListener('click', queryRanking);

async function queryRanking() {
    const categoryId = document.getElementById('category-select').value;
    const start = document.getElementById('start-date').value;
    const end = document.getElementById('end-date').value;
    if (!categoryId || !start || !end) {
        alert('请选择分类和日期范围');
        return;
    }

    const resp = await fetch(`${API_BASE}/ranking?category_id=${categoryId}&start=${start}&end=${end}`);
    const data = await resp.json();
    renderRankingResult(data);
}

function renderRankingResult(ranking) {
    const area = document.getElementById('result-area');
    if (!ranking.length) {
        area.innerHTML = '<div class="empty-state">该分类在指定时间段内无数据</div>';
        return;
    }

    const selectedCode = selectedFund ? selectedFund.code : null;
    let html = `<table><thead><tr><th>排名</th><th>基金代码</th><th>基金名称</th><th>累计涨跌幅</th></tr></thead><tbody>`;
    ranking.forEach(r => {
        const isHighlight = r.code === selectedCode;
        const cls = r.change_pct >= 0 ? 'change-positive' : 'change-negative';
        const sign = r.change_pct >= 0 ? '+' : '';
        html += `<tr class="${isHighlight ? 'highlight' : ''}">
            <td>${r.rank}/${r.total_funds}</td>
            <td>${r.code}</td>
            <td>${r.name}</td>
            <td class="${cls}">${sign}${r.change_pct.toFixed(2)}%</td>
        </tr>`;
    });
    html += '</tbody></table>';
    area.innerHTML = html;
}
