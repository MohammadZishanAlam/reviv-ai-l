// Reviv-AI-l Frontend Client
let socket = null;
let isConnected = false;

async function init() {
    setupWebSocket();
    await refreshData();
}

function setupWebSocket() {
    if (window.location.protocol === "file:") {
        showServerOfflineBanner("You opened this file directly from File Explorer. Please run 'start.bat' and open http://localhost:8000 to connect to the Python backend.");
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            isConnected = true;
            hideServerOfflineBanner();
            document.getElementById("wsStatus").innerText = "Agent Active";
            document.getElementById("wsPing").classList.remove("hidden");
        };
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("WebSocket event received:", data);
            refreshData();
        };
        
        socket.onclose = () => {
            isConnected = false;
            document.getElementById("wsStatus").innerText = "Reconnecting...";
            document.getElementById("wsPing").classList.add("hidden");
            setTimeout(setupWebSocket, 3000);
        };

        socket.onerror = (e) => {
            console.warn("WebSocket connection error:", e);
        };
    } catch (e) {
        console.error("Socket error:", e);
    }
}

function showServerOfflineBanner(message) {
    let banner = document.getElementById("serverOfflineBanner");
    if (!banner) {
        banner = document.createElement("div");
        banner.id = "serverOfflineBanner";
        banner.className = "bg-rose-950/90 border border-rose-700 text-rose-200 text-xs px-4 py-3 text-center sticky top-16 z-30 flex items-center justify-center space-x-2";
        document.body.prepend(banner);
    }
    banner.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-rose-400"></i> <span><strong>Backend Offline:</strong> ${message}</span>`;
    banner.classList.remove("hidden");
}

function hideServerOfflineBanner() {
    const banner = document.getElementById("serverOfflineBanner");
    if (banner) banner.classList.add("hidden");
}

async function handleManualRefresh() {
    const btn = document.getElementById("refreshBtn");
    const icon = document.getElementById("refreshIcon");
    const text = document.getElementById("refreshText");
    
    if (icon) icon.classList.add("fa-spin");
    if (text) text.innerText = "Refreshing...";
    if (btn) {
        btn.disabled = true;
        btn.style.opacity = "0.75";
    }

    try {
        await refreshData();
        if (text) text.innerText = "Updated ✓";
        setTimeout(() => {
            if (text) text.innerText = "Refresh";
        }, 1200);
    } catch (e) {
        console.error("Refresh error:", e);
        if (text) text.innerText = "Failed ⚠️";
        setTimeout(() => {
            if (text) text.innerText = "Refresh";
        }, 1500);
    } finally {
        if (icon) icon.classList.remove("fa-spin");
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "1";
        }
    }
}

async function refreshData() {
    await Promise.all([
        fetchStats(),
        fetchTransactions(),
        fetchTelemetry()
    ]);
}

async function fetchStats() {
    try {
        const res = await fetch("/api/stats");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const stats = await res.json();
        hideServerOfflineBanner();
        
        document.getElementById("atRiskAmount").innerText = `₹${stats.total_at_risk_inr.toLocaleString('en-IN')}`;
        document.getElementById("recoveredAmount").innerText = `₹${stats.total_recovered_inr.toLocaleString('en-IN')}`;
        document.getElementById("failedCount").innerText = stats.total_failed_count;
        document.getElementById("recoveredCount").innerText = stats.total_recovered_count;
        document.getElementById("recoveryRate").innerText = `${stats.recovery_rate_pct}%`;
        document.getElementById("rateProgressBar").style.width = `${Math.min(stats.recovery_rate_pct, 100)}%`;
        document.getElementById("activeInterventions").innerText = stats.active_interventions;
    } catch (e) {
        console.warn("Could not fetch stats:", e);
        showServerOfflineBanner("FastAPI backend is not reachable. Ensure 'start.bat' is running.");
    }
}

async function fetchTelemetry() {
    try {
        const res = await fetch("/api/telemetry");
        if (!res.ok) return;
        const banks = await res.json();
        const container = document.getElementById("telemetryGrid");
        
        if (!banks || banks.length === 0) return;
        
        container.innerHTML = banks.map(b => {
            const isDown = b.health_status === "DOWN";
            const isDegraded = b.health_status === "DEGRADED";
            
            const badgeClass = isDown 
                ? "bg-rose-500/20 text-rose-300 border-rose-600/40" 
                : (isDegraded ? "bg-amber-500/20 text-amber-300 border-amber-600/40" : "bg-emerald-500/20 text-emerald-300 border-emerald-600/40");
            
            const dotClass = isDown ? "bg-rose-500" : (isDegraded ? "bg-amber-400 animate-pulse" : "bg-emerald-500");
            
            return `
            <div class="bg-gray-800/40 border border-gray-700/50 p-3 rounded-xl flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                    <span class="w-2 h-2 rounded-full ${dotClass}"></span>
                    <div>
                        <div class="text-xs font-semibold text-gray-200">${b.bank_name}</div>
                        <div class="text-[10px] text-gray-400">${b.bank_code} • ${b.avg_latency_ms}ms avg</div>
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-[10px] border px-2 py-0.5 rounded font-mono ${badgeClass}">${b.health_status}</span>
                    <div class="text-[10px] text-gray-400 mt-1">${b.success_rate}% success</div>
                </div>
            </div>
            `;
        }).join("");
    } catch (e) {
        console.warn("Could not fetch telemetry:", e);
    }
}

async function fetchTransactions() {
    try {
        const res = await fetch("/api/transactions");
        if (!res.ok) return;
        const txs = await res.json();
        const container = document.getElementById("transactionStream");
        document.getElementById("txCountLabel").innerText = `${txs.length} events logged`;
        
        if (!txs || txs.length === 0) {
            container.innerHTML = `
            <div class="text-center py-16 border border-dashed border-gray-800 rounded-xl">
                <i class="fa-solid fa-radar text-3xl text-gray-600 mb-3"></i>
                <p class="text-sm text-gray-400 font-medium">Awaiting payment events...</p>
                <p class="text-xs text-gray-500 mt-1">Click any scenario on the left to trigger autonomous diagnosis!</p>
            </div>`;
            return;
        }
        
        container.innerHTML = txs.map(tx => {
            const isRecovered = tx.status === "recovered";
            const recovery = tx.recovery;
            
            let statusBadge = isRecovered
                ? `<span class="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] px-2 py-0.5 rounded-full font-semibold flex items-center space-x-1"><i class="fa-solid fa-check"></i><span>RECOVERED</span></span>`
                : `<span class="bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[10px] px-2 py-0.5 rounded-full font-semibold">FAILED</span>`;
                
            let taxonomyBadge = recovery && recovery.failure_class
                ? `<span class="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] px-2 py-0.5 rounded font-mono">${recovery.failure_class}</span>`
                : "";

            let delayBadge = recovery && recovery.delay_minutes > 0
                ? `<span class="text-[10px] text-amber-400 bg-amber-950/60 border border-amber-800/50 px-2 py-0.5 rounded flex items-center space-x-1"><i class="fa-regular fa-clock text-[9px]"></i><span>Delay: ${recovery.delay_minutes}m (Bank Down)</span></span>`
                : "";

            let discountBadge = recovery && recovery.discount_pct > 0
                ? `<span class="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-2 py-0.5 rounded font-bold">🎁 +${recovery.discount_pct}% Incentive</span>`
                : "";

            return `
            <div class="bg-gray-800/40 border border-gray-700/60 rounded-xl p-4 transition hover:border-gray-600 animate-fadeIn">
                <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center space-x-2">
                        <span class="text-xs font-mono font-bold text-gray-200">${tx.id}</span>
                        ${statusBadge}
                        ${taxonomyBadge}
                    </div>
                    <div class="text-right">
                        <div class="text-sm font-bold text-white">₹${tx.amount_inr.toLocaleString('en-IN')}</div>
                        <div class="text-[10px] text-gray-400">${tx.created_at}</div>
                    </div>
                </div>

                <!-- AI Diagnostic Rationale -->
                ${recovery ? `
                <div class="mt-3 bg-gray-900/80 border border-indigo-900/40 rounded-lg p-3">
                    <div class="flex items-center space-x-2 text-[11px] font-semibold text-indigo-400 mb-1">
                        <i class="fa-solid fa-brain"></i>
                        <span>AI Diagnostic Rationale</span>
                    </div>
                    <p class="text-xs text-gray-300 leading-relaxed">${recovery.root_cause}</p>
                    <div class="mt-2 flex flex-wrap items-center gap-2">
                        ${delayBadge}
                        ${discountBadge}
                    </div>
                </div>
                ` : ''}

                <!-- Action Controls -->
                <div class="mt-4 pt-3 border-t border-gray-700/50 flex flex-wrap items-center justify-between gap-3">
                    <div class="text-xs text-gray-400">
                        <span class="font-medium text-gray-300">${tx.customer_name}</span> • <span class="uppercase">${tx.method}</span> (${tx.bank || 'Unknown'})
                    </div>
                    
                    <div class="flex items-center space-x-2">
                        ${recovery && recovery.payment_link_url ? `
                        <button onclick="openWhatsAppModal('${encodeURIComponent(recovery.message || '')}', '${recovery.payment_link_url}')" class="bg-emerald-900/50 hover:bg-emerald-800/60 text-emerald-300 border border-emerald-700/50 text-xs px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition">
                            <i class="fa-brands fa-whatsapp text-sm"></i>
                            <span>Preview Outreach</span>
                        </button>
                        ` : ''}

                        ${!isRecovered ? `
                        <button onclick="simulateRecovery('${tx.id}')" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition shadow-sm active:scale-95">
                            <i class="fa-solid fa-check"></i>
                            <span>Simulate Customer Pay</span>
                        </button>
                        ` : `
                        <span class="text-xs text-emerald-400 font-medium flex items-center space-x-1">
                            <i class="fa-solid fa-circle-check"></i>
                            <span>GMV Rescued</span>
                        </span>
                        `}
                    </div>
                </div>
            </div>
            `;
        }).join("");
    } catch (e) {
        console.warn("Could not fetch transactions:", e);
    }
}

async function triggerSimulation(scenario) {
    const btn = event?.currentTarget;
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.style.opacity = "0.7";
    }

    try {
        const res = await fetch("/api/simulate/failure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario })
        });
        const data = await res.json();
        console.log("Simulated failure generated:", data);
        await refreshData();
    } catch (e) {
        alert("Failed to connect to backend server. Make sure 'start.bat' is running.");
        console.error("Simulation failed:", e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "1";
        }
    }
}

async function simulateRecovery(txId) {
    try {
        const res = await fetch(`/api/simulate/recover/${txId}`, {
            method: "POST"
        });
        const data = await res.json();
        console.log("Simulated customer recovery:", data);
        await refreshData();
    } catch (e) {
        console.error("Recovery simulation failed:", e);
    }
}

function openWhatsAppModal(encodedMsg, link) {
    const msg = decodeURIComponent(encodedMsg);
    document.getElementById("modalMessageText").innerText = msg;
    document.getElementById("modalLinkBtn").href = link;
    document.getElementById("whatsappModal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("whatsappModal").classList.add("hidden");
}

async function triggerBatchBenchmark() {
    const btn = document.getElementById("batchBenchmarkBtn");
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.style.opacity = "0.75";
        btn.innerHTML = `
            <div class="flex items-center space-x-3 text-left w-full justify-center">
                <i class="fa-solid fa-spinner fa-spin text-white text-base"></i>
                <span class="text-xs font-bold text-white">Simulating traffic surge across 25 orders...</span>
            </div>
        `;
    }

    try {
        const res = await fetch("/api/simulate/batch", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        console.log("Batch simulation completed:", data);

        // Populate Batch Modal
        document.getElementById("batchAtRisk").innerText = `₹${data.total_at_risk_inr.toLocaleString('en-IN')}`;
        document.getElementById("batchRecovered").innerText = `₹${data.total_recovered_inr.toLocaleString('en-IN')}`;
        document.getElementById("batchRate").innerText = `${data.recovery_rate_pct}%`;
        document.getElementById("batchStopping").innerText = `${data.stopping_rules_enforced} blocked (zero outreach)`;
        document.getElementById("batchDowntime").innerText = `${data.bank_downtime_delays} queued (15m delay)`;
        document.getElementById("batchAudit").innerText = `${data.audit_trail_entries_created} immutable logs recorded`;

        // Display Modal
        document.getElementById("batchModal").classList.remove("hidden");

        // Refresh entire UI
        await refreshData();
    } catch (e) {
        alert("Batch benchmark simulation failed. Ensure 'start.bat' is running.");
        console.error("Batch benchmark error:", e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "1";
            btn.innerHTML = origHtml;
        }
    }
}

function closeBatchModal() {
    document.getElementById("batchModal").classList.add("hidden");
}

// Initial launch
document.addEventListener("DOMContentLoaded", init);
