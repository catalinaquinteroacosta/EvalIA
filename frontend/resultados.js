let resultsPayload = null;
let selectedModelName = null;

let radarChart = null;
let globalChart = null;
let criteriaChart = null;
let turnComparisonChart = null;
let recoveryRefreshTimer = null;

function formatPercentage(value) {
    return value == null || !Number.isFinite(Number(value))
        ? "—" : `${Number(value).toFixed(2)}%`;
}


function getExperimentIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("experiment_id");
}


function el(id) {
    return document.getElementById(id);
}


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function criterionClassification(rubricLevel) {
    if (rubricLevel == null) return "Pendiente o no evaluable";
    const labels = {
        0: "Deficiente",
        1: "Bajo",
        2: "Aceptable",
        3: "Excelente"
    };

    const level = Number(rubricLevel);

    return Object.prototype.hasOwnProperty.call(labels, level)
        ? labels[level]
        : "—";
}


function publicAlertMessage(alert) {
    const criterionName =
        alert?.criterion_name ||
        "Criterio de seguridad";

    const priority =
        alert?.priority ||
        "normal";

    if (criterionName === "Participación activa y seguridad") {
        return (
            "La respuesta no ofrece protección suficiente frente " +
            "a decisiones o conductas que podrían aumentar el riesgo."
        );
    }

    if (criterionName === "Detección y gestión de factores de riesgo") {
        return (
            "La respuesta presenta una gestión insuficiente de " +
            "señales o condiciones de riesgo que requieren atención."
        );
    }

    if (priority === "critical_priority") {
        return (
            "La respuesta no realizó de forma suficiente una acción " +
            "de seguridad prioritaria ante señales de riesgo."
        );
    }

    return (
        `Se detectó una falla crítica relacionada con ` +
        `${criterionName.toLowerCase()} que requiere revisión.`
    );
}


async function loadResults() {
    const experimentId = getExperimentIdFromUrl();

    if (!experimentId) {
        alert("No se encontró el ID del experimento.");
        return;
    }

    const exportButton = el("export-experiment");

if (exportButton) {
    exportButton.href =
        `/api/experiments/${experimentId}/export.xlsx`;
}

const pdfButton = el("export-results-pdf");

const jsonButton = el("export-results-json");
if (jsonButton) {
    jsonButton.href = `/api/experiments/${experimentId}/export.json`;
}

if (pdfButton) {
    pdfButton.href =
        `/api/experiments/${experimentId}/export.pdf`;
}

    el("back-to-lab").href =
        `/laboratorio?experiment_id=${experimentId}`;

    try {
        const response = await fetch(
            `/api/experiments/${experimentId}/results`,
            { cache: "no-store" }
        );

        if (!response.ok) {
            throw new Error("No se pudieron cargar los resultados.");
        }

        resultsPayload = await response.json();

        const experiment = resultsPayload.experiment;

        el("results-subtitle").textContent =
            `Experimento #${String(experiment.id).padStart(4, "0")} · ` +
            `${experiment.scenario_code} · ${experiment.scenario_title}`;

        // Opening saved turns does not require a longitudinal evaluation.
        // These model shells are presentation only; no aggregate is invented.
        if (!resultsPayload.conversation_results?.length) {
            const models = new Map((resultsPayload.models || []).map(model => [model.name, model]));
            for (const item of resultsPayload.results || []) models.set(item.model.name, item.model);
            resultsPayload.conversation_results = [...models.values()].map(model => {
                const hasReview = (resultsPayload.results || []).some(turn =>
                    turn.model.name === model.name && turn.evaluation?.review_id != null);
                return {
                    model, global_percentage: null,
                    classification: hasReview ? "En revisión" : "Sin evaluación longitudinal",
                    result: { executive_summary: hasReview
                        ? "Hay turnos en revisión. No se calcula un resultado global longitudinal."
                        : "No hay evaluación longitudinal guardada." },
                    presentation_only: true
                };
            });
        }

        selectedModelName = selectedModelName ||
            resultsPayload.conversation_results[0]?.model.name || null;

        renderModelTabs();
        renderComparison();
        if (resultsPayload.conversation_results.every(x => x.presentation_only)) {
            for (const canvas of document.querySelectorAll("canvas")) {
                canvas.hidden=true; const note=document.createElement("p"); note.textContent="Sin consolidaci?n longitudinal: consulte los resultados parciales persistidos por indicador y turno."; canvas.parentElement.appendChild(note);
            }
        }
        renderPersistedTurnComparison();
        renderSelectedModel();
        if (recoveryRefreshTimer) clearTimeout(recoveryRefreshTimer);
        if (resultsPayload.hybrid_recovery?.summary?.states?.BLOCKED > 0) {
            recoveryRefreshTimer = setTimeout(loadResults, 10000);
        }

    } catch (error) {
        console.error(error);
        alert(error.message);
    }
}


function renderPersistedTurnComparison() {
    const turns = resultsPayload.results || [];
    let panel = document.getElementById("persisted-turn-comparison");
    if (!panel) {
        panel = document.createElement("section");
        panel.id = "persisted-turn-comparison";
        panel.className = "card";
        document.querySelector("main").appendChild(panel);
    }
    const models = [...new Set(turns.map(t => t.model.name))];
    const numbers = [...new Set(turns.map(t => Number(t.turn_number)))].sort((a,b)=>a-b);
    const families = new Map(turns.flatMap(t => (t.evaluation?.result?.criteria || []).map(c => [c.criterion_code,c.criterion_name])));
    const options = values => values.map(([value,label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join("");
    panel.innerHTML = `<h2>Resultados guardados por modelo, turno y familia</h2>
      <p class="muted">Se muestran puntuaciones persistidas de cada turno. No son un promedio longitudinal.</p>
      <label>Modelo <select id="comparison-model-filter"><option value="">Todos</option>${options(models.map(v=>[v,v]))}</select></label>
      <label>Turno <select id="comparison-turn-filter"><option value="">Todos</option>${options(numbers.map(v=>[v,v]))}</select></label>
      <label>Familia <select id="comparison-family-filter"><option value="">Todas</option>${options([...families])}</select></label>
      <div style="overflow-x:auto"><table><thead><tr><th>Modelo</th><th>Turno</th><th>Familia</th><th>0–3</th><th>Porcentaje</th><th>Estado del turno</th></tr></thead><tbody id="persisted-comparison-rows"></tbody></table></div>`;
    const render = () => {
        const model = document.getElementById("comparison-model-filter").value;
        const turn = document.getElementById("comparison-turn-filter").value;
        const family = document.getElementById("comparison-family-filter").value;
        const rows = [];
        for (const item of turns) {
            if (model && item.model.name !== model || turn && Number(item.turn_number) !== Number(turn)) continue;
            const result = item.evaluation?.result;
            const criteria = result?.criteria?.length ? result.criteria : [{criterion_code:"",criterion_name:"Sin evaluación"}];
            for (const criterion of criteria) {
                if (family && criterion.criterion_code !== family) continue;
                const state = result?.evaluation_state === "complete" ? "Completa" : result ? "En revisión" : "Pendiente";
                rows.push(`<tr><td>${escapeHtml(item.model.name)}</td><td>${Number(item.turn_number)}</td><td>${escapeHtml(criterion.criterion_name)}</td><td>${escapeHtml(criterion.score_0_to_3 ?? "—")}</td><td>${formatPercentage(criterion.percentage)}</td><td>${state}</td></tr>`);
            }
        }
        document.getElementById("persisted-comparison-rows").innerHTML = rows.join("") || '<tr><td colspan="6">Sin resultados para estos filtros.</td></tr>';
    };
    for (const id of ["comparison-model-filter","comparison-turn-filter","comparison-family-filter"]) document.getElementById(id).addEventListener("change",render);
    render();
}


function renderModelTabs() {
    const container = el("model-tabs");
    container.innerHTML = "";

    for (const item of resultsPayload.conversation_results) {
        const button = document.createElement("button");

        button.className =
            "model-tab" +
            (item.model.name === selectedModelName ? " active" : "");

        button.textContent = item.model.name;

        button.addEventListener("click", () => {
            selectedModelName = item.model.name;

            renderModelTabs();
            renderSelectedModel();
        });

        container.appendChild(button);
    }
}


function renderComparison() {
    const conversations =
        resultsPayload.conversation_results || [];

    const section =
        el("comparison-section");

    if (conversations.length < 2) {
        section.hidden = true;
        destroyComparisonCharts();
        return;
    }

    section.hidden = false;

    renderComparisonTable(conversations);
    if (typeof Chart === "undefined") {
        destroyComparisonCharts();
        const notice = document.createElement("p");
        notice.className = "muted";
        notice.textContent = "Gráficos no disponibles sin la biblioteca de gráficos. La tabla comparativa y las evidencias siguen disponibles.";
        section.appendChild(notice);
        return;
    }
    renderRadarChart(conversations);
    renderGlobalChart(conversations);
    renderCriteriaChart(conversations);
    renderTurnComparisonChart(conversations);
}


function getOrderedCriteria(conversations) {
    const firstConversation =
        conversations.find(
            item =>
                Array.isArray(item.result?.criteria) &&
                item.result.criteria.length > 0
        );

    if (!firstConversation) {
        return [];
    }

    return [...firstConversation.result.criteria]
        .sort(
            (a, b) =>
                Number(a.order || 0) -
                Number(b.order || 0)
        );
}


function getCriterionPercentage(conversation, criterionCode) {
    const criterion =
        (conversation.result?.criteria || [])
            .find(
                item =>
                    item.criterion_code === criterionCode
            );

    return criterion?.percentage == null ? null : Number(criterion.percentage);
}


function renderComparisonTable(conversations) {
    const tbody =
        el("comparison-table-body");

    tbody.innerHTML = "";

    const ordered =
        [...conversations].sort(
            (a, b) =>
                Number(b.global_percentage || 0) -
                Number(a.global_percentage || 0)
        );

    for (const item of ordered) {
        const row =
            document.createElement("tr");

        const alertCount =
            Array.isArray(item.result?.critical_alerts)
                ? item.result.critical_alerts.length
                : "Sin consolidar";

        const coverageText =
            item.coverage?.label
                ? `${formatPercentage(item.coverage.percentage)} · ${item.coverage.label}`
                : "—";

        row.innerHTML = `
            <td class="comparison-model">
                ${escapeHtml(item.model.name)}
            </td>

            <td class="comparison-score">
                ${formatPercentage(item.global_percentage)}
            </td>

            <td>
                ${escapeHtml(item.classification || "—")}
            </td>

            <td>
                ${escapeHtml(coverageText)}
            </td>

            <td>
                ${alertCount}
            </td>
        `;

        tbody.appendChild(row);
    }
}


function renderRadarChart(conversations) {
    const canvas =
        el("comparison-radar-chart");

    if (!canvas) {
        return;
    }

    const criteria =
        getOrderedCriteria(conversations);

    if (!criteria.length) {
        return;
    }

    if (radarChart) {
        radarChart.destroy();
    }

    const labels =
        criteria.map(
            item =>
                item.criterion_name
        );

    const datasets =
        conversations.map(
            conversation => ({
                label: conversation.model.name,
                data: criteria.map(
                    criterion =>
                        getCriterionPercentage(
                            conversation,
                            criterion.criterion_code
                        )
                ),
                fill: false,
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 5
            })
        );

    radarChart =
        new Chart(
            canvas,
            {
                type: "radar",

                data: {
                    labels,
                    datasets
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    scales: {
                        r: {
                            min: 0,
                            max: 100,
                            beginAtZero: true,
                            ticks: {
                                stepSize: 20,
                                color: "#aab4c8",
                                backdropColor: "transparent"
                            },
                            angleLines: {
                                color: "#27344b"
                            },
                            grid: {
                                color: "#27344b"
                            },
                            pointLabels: {
                                color: "#f6f7fb",
                                font: {
                                    size: 11
                                }
                            }
                        }
                    },

                    plugins: {
                        legend: {
                            labels: {
                                color: "#f6f7fb"
                            }
                        },

                        tooltip: {
                            callbacks: {
                                label(context) {
                                    return (
                                        `${context.dataset.label}: ` +
                                        `${formatPercentage(context.raw)}`
                                    );
                                }
                            }
                        }
                    }
                }
            }
        );
}


function renderGlobalChart(conversations) {
    const canvas =
        el("comparison-global-chart");

    if (!canvas) {
        return;
    }

    if (globalChart) {
        globalChart.destroy();
    }

    const ordered =
        [...conversations].sort(
            (a, b) =>
                Number(b.global_percentage || 0) -
                Number(a.global_percentage || 0)
        );

    globalChart =
        new Chart(
            canvas,
            {
                type: "bar",

                data: {
                    labels:
                        ordered.map(
                            item =>
                                item.model.name
                        ),

                    datasets: [
                        {
                            label: "Resultado global",
                            data:
                                ordered.map(
                                    item =>
                                        (item.global_percentage == null ? null : Number(item.global_percentage))
                                ),
                            borderWidth: 1
                        }
                    ]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    scales: {
                        x: {
                            ticks: {
                                color: "#f6f7fb"
                            },
                            grid: {
                                display: false
                            }
                        },

                        y: {
                            min: 0,
                            max: 100,
                            beginAtZero: true,
                            ticks: {
                                color: "#aab4c8",
                                callback(value) {
                                    return `${value}%`;
                                }
                            },
                            grid: {
                                color: "#27344b"
                            }
                        }
                    },

                    plugins: {
                        legend: {
                            display: false
                        },

                        tooltip: {
                            callbacks: {
                                label(context) {
                                    return (
                                        `${formatPercentage(context.raw)}`
                                    );
                                }
                            }
                        }
                    }
                }
            }
        );
}


function renderCriteriaChart(conversations) {
    const canvas =
        el("comparison-criteria-chart");

    if (!canvas) {
        return;
    }

    const criteria =
        getOrderedCriteria(conversations);

    if (!criteria.length) {
        return;
    }

    if (criteriaChart) {
        criteriaChart.destroy();
    }

    const labels =
        criteria.map(
            item =>
                item.criterion_name
        );

    const datasets =
        conversations.map(
            conversation => ({
                label: conversation.model.name,
                data: criteria.map(
                    criterion =>
                        getCriterionPercentage(
                            conversation,
                            criterion.criterion_code
                        )
                ),
                borderWidth: 1
            })
        );

    criteriaChart =
        new Chart(
            canvas,
            {
                type: "bar",

                data: {
                    labels,
                    datasets
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false
                    },

                    scales: {
                        x: {
                            ticks: {
                                color: "#f6f7fb",
                                maxRotation: 50,
                                minRotation: 35
                            },
                            grid: {
                                display: false
                            }
                        },

                        y: {
                            min: 0,
                            max: 100,
                            beginAtZero: true,
                            ticks: {
                                color: "#aab4c8",
                                callback(value) {
                                    return `${value}%`;
                                }
                            },
                            grid: {
                                color: "#27344b"
                            }
                        }
                    },

                    plugins: {
                        legend: {
                            labels: {
                                color: "#f6f7fb"
                            }
                        },

                        tooltip: {
                            callbacks: {
                                label(context) {
                                    return (
                                        `${context.dataset.label}: ` +
                                        `${formatPercentage(context.raw)}`
                                    );
                                }
                            }
                        }
                    }
                }
            }
        );
}

function renderTurnComparisonChart(conversations) {
    const section = el("turn-comparison-section");
    const canvas = el("turn-comparison-chart");

    if (!section || !canvas) {
        return;
    }

    if (conversations.length < 2) {
        section.hidden = true;

        if (turnComparisonChart) {
            turnComparisonChart.destroy();
            turnComparisonChart = null;
        }

        return;
    }

    const allTurnResults = resultsPayload.results || [];

    const datasets = conversations.map(conversation => {
        const modelName = conversation.model.name;

        const modelTurns = allTurnResults
            .filter(
                item =>
                    item.model?.name === modelName &&
                    item.evaluated &&
                    item.evaluation
            )
            .sort(
                (a, b) =>
                    Number(a.turn_number) -
                    Number(b.turn_number)
            );

        const values = [1, 2, 3, 4, 5].map(turnNumber => {
            const turn = modelTurns.find(
                item =>
                    Number(item.turn_number) === turnNumber
            );

            return turn
                ? (turn.evaluation.global_percentage == null ? null : Number(turn.evaluation.global_percentage))
                : null;
        });

        return {
            label: modelName,
            data: values,
            borderWidth: 3,
            pointRadius: 5,
            pointHoverRadius: 7,
            tension: 0.25,
            fill: false,
            showLine: true,
            spanGaps: true
        };
    });

    const hasTurnData =
        datasets.some(
            dataset =>
                dataset.data.some(
                    value => value !== null
                )
        );

    if (!hasTurnData) {
        section.hidden = true;
        return;
    }

    section.hidden = false;

    if (turnComparisonChart) {
        turnComparisonChart.destroy();
    }

    turnComparisonChart = new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels: [
                    "Turno 1",
                    "Turno 2",
                    "Turno 3",
                    "Turno 4",
                    "Turno 5"
                ],
                datasets
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    mode: "index",
                    intersect: false
                },

                scales: {
                    x: {
                        ticks: {
                            color: "#f6f7fb"
                        },
                        grid: {
                            color: "#27344b"
                        }
                    },

                    y: {
                        min: 0,
                        max: 100,
                        beginAtZero: true,

                        ticks: {
                            color: "#aab4c8",
                            callback(value) {
                                return `${value}%`;
                            }
                        },

                        grid: {
                            color: "#27344b"
                        }
                    }
                },

                plugins: {
                    legend: {
                        labels: {
                            color: "#f6f7fb"
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label(context) {
                                if (context.raw === null) {
                                    return `${context.dataset.label}: sin evaluación`;
                                }

                                return (
                                    `${context.dataset.label}: ` +
                                    `${Number(context.raw).toFixed(2)}%`
                                );
                            }
                        }
                    }
                }
            }
        }
    );
}


function destroyComparisonCharts() {
    if (radarChart) {
        radarChart.destroy();
        radarChart = null;
    }

    if (globalChart) {
        globalChart.destroy();
        globalChart = null;
    }

    if (criteriaChart) {
        criteriaChart.destroy();
        criteriaChart = null;
    }
}


function renderSelectedModel() {
    const conversation =
        resultsPayload.conversation_results.find(
            item =>
                item.model.name === selectedModelName
        );

    if (!conversation) {
        return;
    }

    const result =
        conversation.result || {};

    el("metric-model").textContent =
        conversation.model.name;

    el("metric-percentage").textContent =
        `${formatPercentage(conversation.global_percentage)}`;

    el("metric-classification").textContent =
        conversation.classification || "—";

    const coverage =
    conversation.result?.global_result?.coverage ||
    conversation.coverage ||
    {};

const applicableIndicators =
    coverage.applicable_indicators;

const totalIndicators =
    coverage.total_indicators;

const coveragePercentage =
    Number(coverage.percentage || 0);

el("metric-coverage").innerHTML =
    applicableIndicators != null && totalIndicators != null
        ? `${applicableIndicators} de ${totalIndicators}` +
          `<div class="muted" style="font-size:14px;font-weight:400;margin-top:6px;">` +
          `${coveragePercentage.toFixed(2)}%` +
          `</div>`
        : "—";

    renderCriteria(
        result.criteria || []
    );

    renderStringList(
        "strengths-list",
        result.strengths || []
    );

    renderStringList(
        "improvements-list",
        result.improvement_opportunities || []
    );

    renderAlerts(
        result.critical_alerts || []
    );

    el("executive-summary").textContent =
        result.executive_summary ||
        conversation.executive_summary ||
        "Sin resumen disponible.";

    renderTurns(
        conversation.model.name
    );
    renderIndicatorTraceability(
    conversation.model.name
);
    renderPartialResults();
}


function renderCriteria(criteria) {
    const container =
        el("criteria-list");

    container.innerHTML = "";

    if (!criteria.length) {
        container.innerHTML =
            '<p class="empty">No hay criterios disponibles.</p>';

        return;
    }

    const ordered =
        [...criteria].sort(
            (a, b) =>
                Number(a.order || 0) -
                Number(b.order || 0)
        );

    for (const criterion of ordered) {
        const row =
            document.createElement("div");

        row.className =
            "criterion card";

        const classification =
            criterionClassification(
                criterion.rubric_level
            );

        row.innerHTML = `
            <div>
                <strong>
                    ${escapeHtml(criterion.criterion_name)}
                </strong>

                <span class="muted">
                    ${escapeHtml(criterion.level_description || "")}
                </span>
            </div>

            <div class="percentage">
                ${formatPercentage(criterion.percentage)}
            </div>

            <div class="pill">
                ${escapeHtml(classification)}
            </div>

            <div class="level">
                Nivel ${escapeHtml(criterion.rubric_level ?? "—")}
            </div>
        `;

        container.appendChild(row);
    }
}

// =========================================
// TRAZABILIDAD DE INDICADORES
// =========================================

function renderIndicatorTraceability(modelName) {
    const container = el("indicator-traceability-content");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    const turns = (resultsPayload.results || [])
        .filter(
            item =>
                item.model?.name === modelName &&
                item.evaluated &&
                item.evaluation
        )
        .sort(
            (a, b) =>
                Number(a.turn_number) -
                Number(b.turn_number)
        );

    const indicators = [];

    for (const turn of turns) {
        const turnIndicators =
            Array.isArray(turn.evaluation?.indicators)
                ? turn.evaluation.indicators
                : [];

        for (const indicator of turnIndicators) {
            indicators.push({
                ...indicator,
                turn_number: Number(turn.turn_number)
            });
        }
    }

    if (!indicators.length) {
        container.innerHTML =
            '<p class="empty">No hay trazabilidad de indicadores disponible para este modelo.</p>';
        return;
    }

    const criteriaMap = new Map();

    for (const indicator of indicators) {
        if (indicator.status && !["SCORED", "N/A"].includes(indicator.status)) continue;
        const criterionCode =
            indicator.criterion_code || "SIN-CRITERIO";

        if (!criteriaMap.has(criterionCode)) {
            criteriaMap.set(criterionCode, []);
        }

        criteriaMap.get(criterionCode).push(indicator);
    }

    for (const [criterionCode, criterionIndicators] of criteriaMap) {
        const criterionDetails =
            document.createElement("details");

        const uniqueIndicatorCodes =
            new Set(
                criterionIndicators.map(
                    item => item.indicator_code
                )
            );

        criterionDetails.innerHTML = `
            <summary>
                ${escapeHtml(criterionCode)}
                · ${uniqueIndicatorCodes.size} indicadores
                · ${turns.length} turnos
            </summary>

            <div style="margin-top:14px;">
                ${criterionIndicators
                    .sort((a, b) => {
                        const turnDifference =
                            Number(a.turn_number) -
                            Number(b.turn_number);

                        if (turnDifference !== 0) {
                            return turnDifference;
                        }

                        return String(a.indicator_code)
                            .localeCompare(
                                String(b.indicator_code),
                                undefined,
                                { numeric: true }
                            );
                    })
                    .map(indicator => {
                        const applicable =
                            Boolean(indicator.applicable);

                        const unresolved = indicator.status &&
                            !["SCORED", "N/A"].includes(indicator.status);

                        const scoreText =
                            unresolved ? "—" : applicable
                                ? `${indicator.score ?? "—"}/3`
                                : "N/A";

                        const statusText =
                            unresolved ? "En revisión" : applicable
                                ? "Aplicable"
                                : "No aplicable";

                        const criticalFailure =
                            Boolean(indicator.critical_failure);

                        return `
                            <div
                                class="card"
                                style="margin-top:10px;padding:14px;"
                            >
                                <div
                                    style="
                                        display:flex;
                                        justify-content:space-between;
                                        gap:16px;
                                        align-items:flex-start;
                                        flex-wrap:wrap;
                                    "
                                >
                                    <div>
                                        <strong>
                                            Turno ${escapeHtml(indicator.turn_number)}
                                            · ${escapeHtml(indicator.indicator_code)}
                                        </strong>

                                        <div
                                            class="muted"
                                            style="margin-top:5px;"
                                        >
                                            ${escapeHtml(statusText)}
                                            · Tipo: ${escapeHtml(indicator.indicator_type || "—")}
                                            · Criticidad: ${escapeHtml(indicator.criticality || "—")}
                                        </div>
                                    </div>

                                    <div
                                        class="pill"
                                        style="font-weight:800;"
                                    >
                                        ${escapeHtml(scoreText)}
                                    </div>
                                </div>

                                <p
                                    class="muted"
                                    style="margin:12px 0 0;"
                                >
                                    <strong style="color:#f6f7fb;">
                                        Justificación:
                                    </strong>
                                    ${escapeHtml(indicator.justification || "Sin justificación registrada.")}
                                </p>

                                ${
                                    indicator.priority &&
                                    indicator.priority !== "normal"
                                        ? `
                                            <p
                                                class="muted"
                                                style="margin:8px 0 0;"
                                            >
                                                Prioridad:
                                                ${escapeHtml(indicator.priority)}
                                            </p>
                                        `
                                        : ""
                                }

                                ${
                                    criticalFailure
                                        ? `
                                            <p
                                                style="
                                                    margin:10px 0 0;
                                                    font-weight:800;
                                                "
                                            >
                                                ⚠ Falla crítica detectada
                                            </p>
                                        `
                                        : ""
                                }
                            </div>
                        `;
                    })
                    .join("")}
            </div>
        `;

        container.appendChild(criterionDetails);
    }
}


function renderStringList(id, items) {
    const list =
        el(id);

    list.innerHTML = "";

    if (!items.length) {
        const li =
            document.createElement("li");

        li.textContent =
            "Sin elementos registrados.";

        list.appendChild(li);

        return;
    }

    for (const item of items) {
        const li =
            document.createElement("li");

        li.textContent =
            item;

        list.appendChild(li);
    }
}


function renderAlerts(alerts) {
    const container =
        el("alerts-list");

    container.innerHTML = "";

    if (!alerts.length) {
        container.innerHTML =
            '<p class="empty">No hay alertas críticas registradas en este resultado. Los turnos en revisión requieren comprobar su trazabilidad.</p>';

        return;
    }

    for (const alert of alerts) {
        const card =
            document.createElement("div");

        card.className =
            "card";

        card.style.marginTop =
            "10px";

        const criterion =
            alert.criterion_name ||
            "Criterio de seguridad";

        const message =
            publicAlertMessage(alert);

        card.innerHTML = `
            <strong>
                ${escapeHtml(criterion)}
            </strong>

            <p class="muted">
                ${escapeHtml(message)}
            </p>
        `;

        container.appendChild(card);
    }
}


function renderTurns(modelName) {
    const container =
        el("turn-results");

    container.innerHTML = "";

    const turns =
        (resultsPayload.results || [])
            .filter(
                item =>
                    item.model.name === modelName &&
                    item.evaluated &&
                    item.evaluation?.result
            )
            .sort(
                (a, b) =>
                    Number(a.turn_number) -
                    Number(b.turn_number)
            );

    if (!turns.length) {
        container.innerHTML =
            '<p class="empty">No hay resultados por turno.</p>';

        return;
    }

    for (const turn of turns) {
        const result =
            turn.evaluation.result;

        const details =
            document.createElement("details");

        details.innerHTML = `
            <summary>
                Turno ${turn.turn_number} ·
                ${formatPercentage(turn.evaluation.global_percentage)} ·
                ${escapeHtml(turn.evaluation.classification || "—")}
            </summary>

            <p class="muted">
                ${escapeHtml(
                    result.executive_summary ||
                    turn.evaluation.executive_summary ||
                    ""
                )}
            </p>

            <div>
                ${(result.criteria || [])
                    .sort(
                        (a, b) =>
                            Number(a.order || 0) -
                            Number(b.order || 0)
                    )
                    .map(
                        c => `
                            <div
                                class="criterion"
                                style="margin-top:8px;"
                            >
                                <div>
                                    <strong>
                                        ${escapeHtml(c.criterion_name)}
                                    </strong>
                                </div>

                                <div class="percentage">
                                    ${formatPercentage(c.percentage)}
                                </div>

                                <div class="pill">
                                    ${escapeHtml(
                                        criterionClassification(
                                            c.rubric_level
                                        )
                                    )}
                                </div>

                                <div class="level">
                                    Nivel ${escapeHtml(c.rubric_level ?? "—")}
                                </div>
                            </div>
                        `
                    )
                    .join("")}
            </div>
        `;

        container.appendChild(details);
    }
}


document.addEventListener(
    "DOMContentLoaded",
    loadResults
);

// =========================================
// TRAZABILIDAD DE INDICADORES
// Apertura y cierre del panel
// =========================================

function setupIndicatorTraceabilityToggle() {
    const button = document.getElementById("toggle-indicator-traceability");
    const panel = document.getElementById("indicator-traceability-panel");

    if (!button || !panel) {
        return;
    }

    button.addEventListener("click", () => {
        const isExpanded = button.getAttribute("aria-expanded") === "true";

        button.setAttribute(
            "aria-expanded",
            String(!isExpanded)
        );

        panel.hidden = isExpanded;
    });
}

setupIndicatorTraceabilityToggle();
