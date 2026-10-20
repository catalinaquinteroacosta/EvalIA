let currentExperiment = null;
let currentScenario = null;

let currentTurnIndex = 0;
let currentModelIndex = 0;

let selectedModels = [];
let evaluationInProgress = false;
let resultsReady = false;
let savingResponse = false;
let savedTurnsByModel = new Map();
let loadEpoch = 0;
const OFFICIAL_MODEL_ORDER = ['ChatGPT', 'Gemini', 'Claude', 'Copilot', 'Perplexity'];

function officialModelNames(models) {
    const rank = name => {
        const index = OFFICIAL_MODEL_ORDER.indexOf(name);
        return index < 0 ? OFFICIAL_MODEL_ORDER.length : index;
    };
    return [...new Set(models.map(model => model.name))].sort((a, b) => rank(a) - rank(b));
}

function localTurnNumber(turn, index) {
    const value = Number(turn.turn_number);
    return Number.isInteger(value) && value > 0 ? value : index + 1;
}


function getExperimentIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("experiment_id");
}


function getElement(id) {
    return document.getElementById(id);
}


function setExperimentHeader() {
    if (!currentExperiment) {
        return;
    }

    const number = getElement("experiment-number");
    if (number) {
        number.textContent =
            `Experimento #${String(currentExperiment.id).padStart(4, "0")}`;
    }
}


function setExperimentStatus(text) {
    const status = getElement("experiment-status");
    if (status) {
        status.textContent = text;
    }
}


async function safeReadError(response) {
    try {
        const payload = await response.json();
        if (payload.detail && typeof payload.detail === "object") {
            return payload.detail.message || payload.detail.status || "Evaluación detenida de forma segura.";
        }
        return (
            payload.detail ||
            payload.error ||
            payload.message ||
            ""
        );
    } catch {
        return "";
    }
}


async function getExperimentResults() {
    if (!currentExperiment) {
        throw new Error("No hay un experimento cargado.");
    }

    const response = await fetch(
        `/api/experiments/${currentExperiment.id}/results`,
        { cache: "no-store" }
    );

    if (!response.ok) {
        const detail = await safeReadError(response);
        throw new Error(
            detail || "No se pudo consultar el progreso del experimento."
        );
    }

    const data = await response.json();

    if (data.error) {
        throw new Error(data.error);
    }

    return data;
}


function getSavedTurnsByModel(resultsData) {
    const saved = new Map();

    selectedModels.forEach(modelName => {
        saved.set(modelName, new Set());
    });

    for (const item of resultsData.results || []) {
        const modelName = item?.model?.name;

        if (!saved.has(modelName)) {
            continue;
        }

        saved.get(modelName).add(Number(item.turn_number));
    }

    return saved;
}


function locateFirstPendingTurn(resultsData) {
    const saved = getSavedTurnsByModel(resultsData);

    for (
        let modelIndex = 0;
        modelIndex < selectedModels.length;
        modelIndex += 1
    ) {
        const modelName = selectedModels[modelIndex];
        const modelTurns = saved.get(modelName) || new Set();

        for (
            let turnIndex = 0;
            turnIndex < currentScenario.turns.length;
            turnIndex += 1
        ) {
            const turnId = localTurnNumber(currentScenario.turns[turnIndex], turnIndex);

            if (!modelTurns.has(turnId)) {
                return {
                    complete: false,
                    modelIndex,
                    turnIndex
                };
            }
        }
    }

    return {
        complete: true,
        modelIndex: Math.max(selectedModels.length - 1, 0),
        turnIndex: Math.max(currentScenario.turns.length - 1, 0)
    };
}


async function loadExperiment() {
    const epoch = ++loadEpoch;
    const experimentId = getExperimentIdFromUrl();

    if (!experimentId) {
        alert("No se encontró el ID del experimento.");
        return;
    }

    try {
        const experimentResponse = await fetch(
            `/api/experiments/${experimentId}`,
            { cache: "no-store" }
        );

        if (!experimentResponse.ok) {
            throw new Error("No se pudo obtener el experimento.");
        }

        const experiment = await experimentResponse.json();
        if (epoch !== loadEpoch) return;

        if (experiment.error) {
            throw new Error(experiment.error);
        }

        currentExperiment = experiment;
        selectedModels = officialModelNames(experiment.models);


        setExperimentHeader();

        /*
         * IMPORTANTE:
         * El backend ya devuelve el snapshot completo del escenario
         * dentro de experiment.scenario.
         *
         * Esto aplica tanto para escenarios canónicos como para LIBRE.
         * No volvemos a consultar /api/prompts/, porque hacerlo puede
         * provocar errores al cargar ansiedad/depresión y, además,
         * rompe la independencia del snapshot del experimento.
         */
        currentScenario = experiment.scenario;

        if (!currentScenario) {
            throw new Error("El experimento no contiene un escenario válido.");
        }

        if (experiment.historical_read_only || selectedModels.length === 0) {
            showResultsButton(false);
            return;
        }

        if (!Array.isArray(currentScenario.turns)) {
            currentScenario.turns = [];
        }
        currentScenario.turns.sort((a, b) => Number(a.turn_number) - Number(b.turn_number));

        const scenarioCode = String(
            currentScenario.code ??
            currentScenario.scenario ??
            ""
        ).trim();

        const isFree = scenarioCode.toUpperCase() === "LIBRE";

        configureMainButton();

        const resultsData = await getExperimentResults();
        if (epoch !== loadEpoch) return;
        savedTurnsByModel = getSavedTurnsByModel(resultsData);

        // LIBRE comienza sin turnos. El primer turno se escribe aquí,
        // directamente en el laboratorio, y después se envía a las IA.
        if (isFree && currentScenario.turns.length === 0) {
            currentModelIndex = 0;
            currentTurnIndex = 0;
            renderFreeTurnComposer();
            return;
        }

        const position = locateFirstPendingTurn(resultsData);

        currentModelIndex = position.modelIndex;
        currentTurnIndex = position.turnIndex;

        if (position.complete) {
            if (isFree) {
                const summary = resultsData.summary || {};
                const fullyEvaluated =
                    Number(summary.responses_pending_evaluation || 0) === 0 &&
                    currentScenario.turns.length > 0;

                if (fullyEvaluated) {
                    showResultsButton();
                } else {
                    renderFreeNextTurnChoice();
                }
                return;
            }

            // Merely opening a case must not trigger new paid evaluations.
            if (Number(resultsData.summary?.responses_pending_evaluation || 0) > 0) {
                renderAllConversationsCompleted();
                resultsReady = false;
                const retry = getElement("save-manual-response-btn");
                if (retry) {
                    retry.textContent = "EVALUAR EXPERIMENTO COMPLETO";
                    retry.onclick = evaluateWholeExperiment;
                }
            } else showResultsButton();
            return;
        }

        renderCurrentTurn();

    } catch (error) {
        console.error(error);
        alert(`Error al cargar el laboratorio: ${error.message}`);
    }
}


function configureMainButton() {
    const button = getElement("save-manual-response-btn");

    if (!button) {
        console.error(
            "No se encontró el botón save-manual-response-btn."
        );
        return;
    }

    button.onclick = saveResponseAndContinue;
}


function isFreeExperiment() {
    const code =
        currentScenario?.code ??
        currentScenario?.scenario ??
        currentExperiment?.scenario?.code ??
        "";

    return String(code).trim().toUpperCase() === "LIBRE";
}


function renderFreeTurnComposer() {
    const scenarioTitle = getElement("lab-scenario-title");
    const turnCounter = getElement("lab-turn-counter");
    const userMessage = getElement("lab-user-message");
    const currentModelName = getElement("current-model-name");
    const responseInput = getElement("manual-response-input");
    const helperText = getElement("lab-helper-text");
    const button = getElement("save-manual-response-btn");

    if (!userMessage) return;

    const nextTurn = currentScenario.turns.length + 1;

    if (scenarioTitle) {
        scenarioTitle.textContent = "LIBRE · Experimento libre";
    }

    if (turnCounter) {
        turnCounter.textContent = `Nuevo turno ${nextTurn} de 10`;
    }

    if (currentModelName) {
        currentModelName.textContent = "👤 Usuario";
    }

    if (helperText) {
        helperText.textContent =
            "Escribe el mensaje del usuario para iniciar este turno. Después podrás pegar la respuesta de cada IA.";
    }

    userMessage.innerHTML = `
        <div class="free-user-composer">
            <textarea
                id="free-user-turn-input"
                rows="4"
                placeholder="Escribe aquí el mensaje del usuario..."
                aria-label="Mensaje del usuario"
            ></textarea>
            <button
                type="button"
                class="secondary free-user-turn-btn"
                id="free-user-turn-btn"
            >
                Guardar mensaje y continuar
            </button>
        </div>
    `;

    const input = getElement("free-user-turn-input");
    const saveButton = getElement("free-user-turn-btn");

    if (input) {
        input.focus();
        input.addEventListener("keydown", event => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                saveFreeTurnAndContinue();
            }
        });
    }

    if (saveButton) {
        saveButton.onclick = saveFreeTurnAndContinue;
    }

    if (responseInput) {
        responseInput.value = "";
        responseInput.disabled = true;
        responseInput.placeholder = "Primero escribe el mensaje del usuario.";
    }

    if (button) {
        button.disabled = true;
        button.textContent = "Esperando mensaje del usuario...";
        button.onclick = null;
    }

    resultsReady = false;
    setExperimentStatus("● Preparando turno");
    updateModelSidebar();
}


async function saveFreeTurnAndContinue() {
    if (!currentExperiment || !isFreeExperiment()) return;

    const input = getElement("free-user-turn-input");
    const saveButton = getElement("free-user-turn-btn");

    if (!input) return;

    const userMessage = input.value.trim();
    if (!userMessage) {
        alert("Escribe el mensaje del usuario antes de continuar.");
        input.focus();
        return;
    }

    if (currentScenario.turns.length >= 10) {
        alert("Un experimento LIBRE puede contener máximo 10 turnos.");
        return;
    }

    if (saveButton) {
        saveButton.disabled = true;
        saveButton.textContent = "Guardando turno...";
    }

    try {
        const response = await fetch(
            `/api/experiments/${currentExperiment.id}/free-turns`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_message: userMessage })
            }
        );

        if (!response.ok) {
            const detail = await safeReadError(response);
            throw new Error(detail || "No se pudo guardar el turno.");
        }

        const data = await response.json();
        const turn = data.turn;

        if (!turn || !turn.id) {
            throw new Error("El servidor no devolvió el turno creado.");
        }

        currentScenario.turns.push({
            id: Number(turn.id),
            turn_number: Number(turn.turn_number) || currentScenario.turns.length + 1,
            user_message: turn.user,
            user: turn.user
        });

        currentTurnIndex = currentScenario.turns.length - 1;
        currentModelIndex = 0;

        renderCurrentTurn();

    } catch (error) {
        console.error(error);
        alert(`No se pudo guardar el mensaje: ${error.message}`);
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.textContent = "Guardar mensaje y continuar";
        }
    }
}


function renderFreeNextTurnChoice() {
    const scenarioTitle = getElement("lab-scenario-title");
    const turnCounter = getElement("lab-turn-counter");
    const userMessage = getElement("lab-user-message");
    const currentModelName = getElement("current-model-name");
    const responseInput = getElement("manual-response-input");
    const helperText = getElement("lab-helper-text");
    const button = getElement("save-manual-response-btn");

    if (!userMessage) return;

    const nextTurn = currentScenario.turns.length + 1;
    const canAdd = nextTurn <= 10;

    if (scenarioTitle) {
        scenarioTitle.textContent = "LIBRE · Experimento libre";
    }

    if (turnCounter) {
        turnCounter.textContent = `Turno ${currentScenario.turns.length} completado`;
    }

    if (currentModelName) {
        currentModelName.textContent = "💬 Conversación";
    }

    if (helperText) {
        helperText.textContent = canAdd
            ? "Todas las IA respondieron este turno. Puedes continuar la conversación o finalizarla para evaluar los resultados."
            : "Has llegado al máximo de 10 turnos. Puedes finalizar la conversación para evaluar los resultados.";
    }

    userMessage.innerHTML = `
        <div class="free-next-turn-choice">
            <p>Las respuestas de todas las IA para este turno ya fueron guardadas.</p>
            <div class="free-next-turn-actions">
                ${canAdd ? `
                    <button type="button" class="secondary" id="free-add-next-turn-btn">
                        + Escribir siguiente turno
                    </button>
                ` : ""}
                <button type="button" class="primary" id="free-finish-btn">
                    Finalizar conversación y evaluar
                </button>
            </div>
        </div>
    `;

    const addButton = getElement("free-add-next-turn-btn");
    if (addButton) {
        addButton.onclick = () => {
            currentModelIndex = 0;
            currentTurnIndex = currentScenario.turns.length;
            renderFreeTurnComposer();
        };
    }

    const finishButton = getElement("free-finish-btn");
    if (finishButton) {
        finishButton.onclick = async () => {
            finishButton.disabled = true;
            finishButton.textContent = "Preparando evaluación...";
            currentModelIndex = Math.max(selectedModels.length - 1, 0);
            currentTurnIndex = Math.max(currentScenario.turns.length - 1, 0);
            renderAllConversationsCompleted();
            await evaluateWholeExperiment();
        };
    }

    if (responseInput) {
        responseInput.value = "";
        responseInput.disabled = true;
        responseInput.placeholder = "Selecciona una acción para continuar.";
    }

    if (button) {
        button.disabled = true;
        button.textContent = "Turno completado";
        button.onclick = null;
    }

    setExperimentStatus("● Turno completado");
    updateModelSidebar();
}


function renderCurrentTurn() {
    const scenarioTitle = getElement("lab-scenario-title");
    const turnCounter = getElement("lab-turn-counter");
    const userMessage = getElement("lab-user-message");
    const currentModelName = getElement("current-model-name");
    const responseInput = getElement("manual-response-input");
    const helperText = getElement("lab-helper-text");
    const button = getElement("save-manual-response-btn");

    if (
        !currentScenario ||
        !scenarioTitle ||
        !turnCounter ||
        !userMessage ||
        !currentModelName
    ) {
        return;
    }

    const currentTurn =
        currentScenario.turns[currentTurnIndex];

    const modelName =
        selectedModels[currentModelIndex];

    const scenarioLabel =
        currentScenario.code ??
        currentScenario.scenario ??
        currentScenario.category ??
        "Escenario";

    scenarioTitle.textContent =
        `${scenarioLabel} · ${currentScenario.title ?? ""}`;

    turnCounter.textContent =
        `Turno ${localTurnNumber(currentTurn, currentTurnIndex)} de ${currentScenario.turns.length}`;

    userMessage.textContent =
        currentTurn.user ?? currentTurn.user_message ?? "";

    currentModelName.textContent =
        `🤖 ${modelName}`;

    if (helperText) {
        helperText.textContent =
            `Pega aquí la respuesta real de ${modelName}.`;
    }

    if (responseInput) {
        responseInput.disabled = false;
        responseInput.value = "";
        responseInput.placeholder =
            `Pega aquí la respuesta de ${modelName} para el turno ${localTurnNumber(currentTurn, currentTurnIndex)}...`;
        responseInput.focus();
    }

    if (button) {
        button.disabled = false;
        button.textContent =
            "Guardar respuesta y continuar";
        button.onclick = saveResponseAndContinue;
    }

    resultsReady = false;
    setExperimentStatus("● Ejecutándose");
    updateModelSidebar();
}


async function saveResponseAndContinue() {
    if (evaluationInProgress || resultsReady || savingResponse) {
        return;
    }

    const button = getElement("save-manual-response-btn");
    const responseInput = getElement("manual-response-input");

    if (
        !button ||
        !responseInput ||
        !currentExperiment ||
        !currentScenario
    ) {
        return;
    }

    const responseText = responseInput.value.trim();

    if (!responseText) {
        alert("Primero pega la respuesta de la IA.");
        responseInput.focus();
        return;
    }

    const currentTurn =
        currentScenario.turns[currentTurnIndex];

    const modelName =
        selectedModels[currentModelIndex];

    button.disabled = true;
    savingResponse = true;
    button.textContent = "Guardando respuesta...";

    try {
        const response = await fetch(
            "/api/responses/manual",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    experiment_id: currentExperiment.id,
                    model_name: modelName,
                    turn_number: localTurnNumber(currentTurn, currentTurnIndex),
                    response_text: responseText
                })
            }
        );

        if (!response.ok) {
            const detail = await safeReadError(response);
            throw new Error(
                detail || "El servidor no pudo guardar la respuesta."
            );
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (data.status !== "saved") {
            throw new Error(
                "La respuesta no pudo confirmarse como guardada."
            );
        }

        button.textContent = 'Respuesta guardada. Cargando siguiente turno...';
        window.dispatchEvent(new Event('evalia-response-saved'));
        const latest = await getExperimentResults();
        savedTurnsByModel = getSavedTurnsByModel(latest);
        if (!isFreeExperiment()) {
            const next = locateFirstPendingTurn(latest);
            if (!next.complete) {
                currentModelIndex = next.modelIndex;
                currentTurnIndex = next.turnIndex;
                renderCurrentTurn();
            } else {
                renderAllConversationsCompleted();
                // Wait for the explicit main-button click before preparing costs.
            }
        } else await advanceExperiment();

    } catch (error) {
        console.error(error);
        alert(`No se pudo guardar: ${error.message}`);

        button.disabled = false;
        button.textContent =
            "Guardar respuesta y continuar";
    } finally {
        savingResponse = false;
    }
}


async function advanceExperiment() {
    if (isFreeExperiment()) {
        const lastTurnIndex = currentScenario.turns.length - 1;
        const lastModelIndex = selectedModels.length - 1;

        if (currentModelIndex < lastModelIndex) {
            currentModelIndex += 1;
            renderCurrentTurn();
            return;
        }

        // En LIBRE no pasamos automáticamente al siguiente turno.
        // Primero dejamos que la persona escriba el siguiente mensaje
        // o decida finalizar la conversación.
        currentTurnIndex = lastTurnIndex;
        renderFreeNextTurnChoice();
        return;
    }

    const lastTurnIndex =
        currentScenario.turns.length - 1;

    const lastModelIndex =
        selectedModels.length - 1;

    // Aún faltan turnos del mismo modelo.
    if (currentTurnIndex < lastTurnIndex) {
        currentTurnIndex += 1;
        renderCurrentTurn();
        return;
    }

    // Terminó este modelo, pero quedan otros modelos seleccionados.
    if (currentModelIndex < lastModelIndex) {
        const completedModel =
            selectedModels[currentModelIndex];

        currentModelIndex += 1;
        currentTurnIndex = 0;

        alert(
            `${completedModel} completó sus ${currentScenario.turns.length} turnos. ` +
            `Ahora continúa ${selectedModels[currentModelIndex]}.`
        );

        renderCurrentTurn();
        return;
    }

    // Solo entra aquí cuando terminó el último turno del último modelo seleccionado.
    renderAllConversationsCompleted();
    // Capture completion never authorizes or prepares a paid evaluation.
}


function renderAllConversationsCompleted() {
    const scenarioTitle = getElement("lab-scenario-title");
    const turnCounter = getElement("lab-turn-counter");
    const currentModelName = getElement("current-model-name");
    const responseInput = getElement("manual-response-input");
    const helperText = getElement("lab-helper-text");
    const button = getElement("save-manual-response-btn");

    if (scenarioTitle && currentScenario) {
        const scenarioLabel =
            currentScenario.code ??
            currentScenario.scenario ??
            currentScenario.category ??
            "Escenario";

        scenarioTitle.textContent =
            `${scenarioLabel} · ${currentScenario.title ?? ""}`;
    }

    if (turnCounter) {
        turnCounter.textContent =
            "Conversaciones completadas";
    }

    if (currentModelName) {
        currentModelName.textContent =
            "✅ Todos los modelos seleccionados completaron sus turnos";
    }

    if (helperText) {
        helperText.textContent =
            "Todas las respuestas están guardadas. Evalúa todos los turnos y modelos con el botón inferior.";
    }

    if (responseInput) {
        responseInput.value = "";
        responseInput.disabled = true;
        responseInput.placeholder =
            "Todas las respuestas fueron guardadas.";
    }

    if (button) {
        button.disabled = false;
        button.textContent =
            "EVALUAR EXPERIMENTO COMPLETO";
        button.onclick = evaluateWholeExperiment;
    }

    markAllModelsAsCompleted();
    updateResponseProgress();
    setExperimentStatus("● Listo para evaluar");
}


async function evaluateWholeExperiment() {
    if (window.evaliaRealModeSelected?.()) {
        await window.evaluateRealSavedResponses();
        return;
    }
    if (evaluationInProgress || resultsReady) {
        return;
    }

    evaluationInProgress = true;

    const button = getElement("save-manual-response-btn");
    const helperText = getElement("lab-helper-text");

    try {
        setExperimentStatus("● Evaluando...");
        if (helperText) {
            helperText.textContent =
                "Ejecutando las reglas determinísticas de EvalIA...";
        }

        const before = await getExperimentResults();

        const pending = (before.results || [])
            .filter(item => !item.evaluated || item.review_required)
            .filter(item => selectedModels.includes(item.model.name))
            .sort((a, b) => {
                const modelA =
                    selectedModels.indexOf(a.model.name);
                const modelB =
                    selectedModels.indexOf(b.model.name);

                if (modelA !== modelB) {
                    return modelA - modelB;
                }

                return Number(a.turn_number) -
                    Number(b.turn_number);
            });

        let batchPendingCount = 0;
        let finishedCount = 0;

        if (pending.length > 0) {
            for (
                let index = 0;
                index < pending.length;
                index += 1
            ) {
                const item = pending[index];

                if (button) {
                    button.textContent =
                        `Evaluando ${index + 1} de ${pending.length} respuestas...`;
                }

                updateEvaluationProgress(
                    finishedCount,
                    pending.length
                );

                const evaluationResponse = await fetch(
                    `/api/responses/${item.response_id}/evaluate`,
                    {
                        method: "POST",
                        cache: "no-store"
                    }
                );

                if (!evaluationResponse.ok) {
                    const detail =
                        await safeReadError(evaluationResponse);

                    throw new Error(
                        detail ||
                        `No se pudo evaluar la respuesta ${item.response_id}.`
                    );
                }

                const evaluation =
                    await evaluationResponse.json();

                if (evaluationResponse.status === 202 &&
                    (evaluation.status === "batch_pending" ||
                     evaluation.detail?.status === "batch_pending")) {
                    batchPendingCount += 1;
                    continue;
                }

                if (evaluation.error) {
                    throw new Error(evaluation.error);
                }
                finishedCount += 1;
            }
        }

        if (batchPendingCount > 0) {
            updateEvaluationProgress(finishedCount, pending.length);
            setExperimentStatus("● Evaluación Batch pendiente");
            if (helperText) {
                helperText.textContent =
                    `${batchPendingCount} respuestas preparadas para Batch; aún no hay resultados finales. Comprueba de nuevo después de procesar e importar el lote.`;
            }
            if (button) {
                button.disabled = false;
                button.textContent = "Comprobar resultados Batch";
                button.onclick = evaluateWholeExperiment;
            }
            evaluationInProgress = false;
            return;
        }

        updateEvaluationProgress(
            pending.length,
            pending.length
        );

        await verifyFinalEvaluation();

    } catch (error) {
        console.error(error);

        setExperimentStatus("● Error de evaluación");

        if (helperText) {
            helperText.textContent =
                "Las respuestas están guardadas. Antes de reanudar, revisa el error y la autorización. Una transmisión incierta requiere revisar sus recibos y no se repite automáticamente.";
        }

        if (button) {
            button.disabled = false;
            button.textContent =
                "Reintentar evaluación";
            button.onclick = async () => {
                evaluationInProgress = false;
                await evaluateWholeExperiment();
            };
        }

        evaluationInProgress = false;

        alert(
            `Las respuestas están guardadas, pero ocurrió un error al evaluar: ${error.message}`
        );
    }
}


async function verifyFinalEvaluation() {
    const finalData = await getExperimentResults();
    const summary = finalData.summary || {};

    const pendingCount =
        Number(summary.responses_pending_evaluation || 0);


    const expectedResponses =
        selectedModels.length * currentScenario.turns.length;

    const evaluatedCount =
        Number(summary.responses_evaluated || 0);


    if (pendingCount !== 0) {
        throw new Error(
            `Quedaron ${pendingCount} respuestas pendientes de evaluación.`
        );
    }

    if (evaluatedCount < expectedResponses) {
        throw new Error(
            `Se esperaban ${expectedResponses} respuestas evaluadas y solo aparecen ${evaluatedCount}.`
        );
    }

    // Validated turn results are accessible without inventing or requiring
    // a new longitudinal evaluation. Existing longitudinal records survive.

    showResultsButton();
}


function showResultsButton(complete = true) {
    const button = getElement("save-manual-response-btn");
    const responseInput = getElement("manual-response-input");
    const currentModelName = getElement("current-model-name");
    const helperText = getElement("lab-helper-text");

    if (responseInput) {
        responseInput.disabled = true;
        responseInput.value = "";
        responseInput.placeholder =
            complete ? "Evaluación completada." : "Consulta de respuestas guardadas.";
    }

    if (currentModelName) {
        currentModelName.textContent =
            complete ? "✅ Evaluación completada" : "Consulta del experimento";
    }

    if (helperText) {
        helperText.textContent =
            complete ? "Todos los turnos ya fueron evaluados." : "Puedes consultar los resultados guardados; no se ejecutará una evaluación al abrir el caso.";
    }

    if (button) {
        button.disabled = false;
        button.textContent =
            "Ver resultados de la evaluación";
        button.onclick = () => {
            window.location.href =
                `/resultados?experiment_id=${currentExperiment.id}`;
        };
    }

    setExperimentStatus(complete ? "● Evaluado" : "● Consulta");
    if (complete) {
        markAllModelsAsCompleted();
        setProgressCompleted();
    }

    evaluationInProgress = false;
    resultsReady = true;
}


function updateModelSidebar() {
    const cards =
        document.querySelectorAll(".model-status");

    const currentModel =
        selectedModels[currentModelIndex];

    cards.forEach(card => {
        const modelName = card.dataset.model;
        const nameElement = card.querySelector("span");
        const statusElement = card.querySelector("small");

        if (!nameElement || !statusElement) {
            return;
        }

        card.classList.remove("active");

        const selectedIndex =
            selectedModels.indexOf(modelName);

        if (selectedIndex === -1) {
            nameElement.textContent =
                `⚪ ${modelName}`;
            statusElement.textContent =
                "No seleccionado";
            return;
        }

        const savedCount = (savedTurnsByModel.get(modelName) || new Set()).size;
        if (savedCount === currentScenario.turns.length && savedCount > 0) {
            nameElement.textContent =
                `✅ ${modelName}`;
            statusElement.textContent =
                "Completado";
            return;
        }

        if (modelName === currentModel) {
            card.classList.add("active");
            nameElement.textContent =
                `🟢 ${modelName}`;
            statusElement.textContent =
                `Turno ${currentTurnIndex + 1} de ${currentScenario.turns.length}`;
            return;
        }

        nameElement.textContent =
            `⚪ ${modelName}`;
        statusElement.textContent =
            "En espera";
    });

    updateResponseProgress();
}


function updateResponseProgress() {
    const progressFill =
        document.querySelector(".progress-bar div");

    const progressText =
        document.querySelector(".lab-summary p");

    if (!progressFill || !progressText) {
        return;
    }

    const totalSteps =
        selectedModels.length *
        currentScenario.turns.length;

    const completedSteps = selectedModels.reduce((total, model) => {
        const saved = savedTurnsByModel.get(model) || new Set();
        return total + currentScenario.turns.filter((turn, index) => saved.has(localTurnNumber(turn, index))).length;
    }, 0);

    const percentage =
        totalSteps > 0
            ? (completedSteps / totalSteps) * 100
            : 0;

    progressFill.style.width =
        `${percentage}%`;

    progressText.textContent =
        `${completedSteps} de ${totalSteps} respuestas guardadas`;
}


function updateEvaluationProgress(completed, total) {
    const progressFill =
        document.querySelector(".progress-bar div");

    const progressText =
        document.querySelector(".lab-summary p");

    if (progressFill) {
        const percentage =
            total > 0
                ? (completed / total) * 100
                : 100;

        progressFill.style.width =
            `${percentage}%`;
    }

    if (progressText) {
        progressText.textContent =
            total > 0
                ? `${completed} de ${total} respuestas evaluadas`
                : "Comprobando evaluación...";
    }
}


function setProgressCompleted() {
    const progressFill =
        document.querySelector(".progress-bar div");

    const progressText =
        document.querySelector(".lab-summary p");

    if (progressFill) {
        progressFill.style.width = "100%";
    }

    if (progressText) {
        const totalSteps =
            selectedModels.length *
            currentScenario.turns.length;

        progressText.textContent =
            `${totalSteps} de ${totalSteps} respuestas evaluadas`;
    }
}


function markAllModelsAsCompleted() {
    const cards =
        document.querySelectorAll(".model-status");

    cards.forEach(card => {
        const modelName = card.dataset.model;
        const nameElement = card.querySelector("span");
        const statusElement = card.querySelector("small");

        if (!nameElement || !statusElement) {
            return;
        }

        card.classList.remove("active");

        if (selectedModels.includes(modelName)) {
            nameElement.textContent =
                `✅ ${modelName}`;
            statusElement.textContent =
                "Completado";
        } else {
            nameElement.textContent =
                `⚪ ${modelName}`;
            statusElement.textContent =
                "No seleccionado";
        }
    });
}


document.addEventListener(
    "DOMContentLoaded",
    loadExperiment
);
