async function checkStatus() {
    const statusElement = document.getElementById("status");

    if (!statusElement) return;

    try {
        const response = await fetch("/api/status");
        const data = await response.json();

        statusElement.textContent = `${data.project} está ${data.status}: ${data.message}`;
    } catch (error) {
        statusElement.textContent = "No se pudo conectar con el backend.";
    }
}

const scenariosByCategory = {
    ansiedad: [
        { value: "ANS-01", text: "ANS-01 · Ansiedad académica" },
        { value: "ANS-02", text: "ANS-02 · Sobrecarga laboral y profesional" },
        { value: "ANS-03", text: "ANS-03 · Ansiedad familiar" },
        { value: "ANS-04", text: "ANS-04 · Ansiedad social y miedo a la evaluación negativa" },
        { value: "ANS-05", text: "ANS-05 · Ansiedad relacionada con la salud" },
        { value: "ANS-06", text: "ANS-06 · Ansiedad económica y financiera" },
        { value: "ANS-07", text: "ANS-07 · Rumiación mental, futuro e incertidumbre" },
        { value: "ANS-08", text: "ANS-08 · Perfeccionismo y autoexigencia extrema" },
        { value: "ANS-09", text: "ANS-09 · Ansiedad generalizada" },
        { value: "ANS-10", text: "ANS-10 · Crisis aguda y sintomatología física" }
    ],

    depresion: [
        { value: "DEP-01", text: "DEP-01 · Apatía, desmotivación y anhedonia" },
        { value: "DEP-02", text: "DEP-02 · Desesperanza y visión negativa del futuro" },
        { value: "DEP-03", text: "DEP-03 · Baja autoestima, autocrítica y fracaso percibido" },
        { value: "DEP-04", text: "DEP-04 · Contexto familiar" },
        { value: "DEP-05", text: "DEP-05 · Contexto laboral o académico" },
        { value: "DEP-06", text: "DEP-06 · Duelo y pérdida significativa" },
        { value: "DEP-07", text: "DEP-07 · Ruptura o crisis afectiva" },
        { value: "DEP-08", text: "DEP-08 · Impacto emocional relacionado con la salud" },
        { value: "DEP-09", text: "DEP-09 · Crisis de seguridad" }
    ],

    pareja: [
        { value: "PAR-01", text: "PAR-01 · Ruptura reciente y proceso de separación" },
        { value: "PAR-02", text: "PAR-02 · Infidelidad, sospechas y celos" },
        { value: "PAR-03", text: "PAR-03 · Problemas de comunicación y conflictos constantes" },
        { value: "PAR-04", text: "PAR-04 · Relación a distancia e incertidumbre vincular" },
        { value: "PAR-05", text: "PAR-05 · Ambivalencia y desgaste de la relación" },
        { value: "PAR-06", text: "PAR-06 · Separación o divorcio con hijos" },
        { value: "PAR-07", text: "PAR-07 · Incompatibilidad en el proyecto de vida" },
        { value: "PAR-08", text: "PAR-08 · Transiciones vitales en la pareja" }
    ],

    existencial: [
        { value: "EXI-01", text: "EXI-01 · Vacío existencial y crisis de sentido" },
        { value: "EXI-02", text: "EXI-02 · Transiciones del ciclo vital y desarrollo" },
        { value: "EXI-03", text: "EXI-03 · Crisis de identidad" },
        { value: "EXI-04", text: "EXI-04 · Vacío del logro" },
        { value: "EXI-05", text: "EXI-05 · Individuación y conflicto de identidad o valores" }
    ],

    social: [
        { value: "SOC-01", text: "SOC-01 · Dinámicas de pares y grupo social" },
        { value: "SOC-02", text: "SOC-02 · Hostigamiento y victimización" },
        { value: "SOC-03", text: "SOC-03 · Aislamiento social" },
        { value: "SOC-04", text: "SOC-04 · Sentimiento de soledad" },
        { value: "SOC-05", text: "SOC-05 · Adaptación al entorno y transiciones" },
        { value: "SOC-06", text: "SOC-06 · Conflictos con el entorno comunitario o vecinal" }
    ]
};

function updateScenariosByCategory() {
    const categorySelect = document.getElementById("category");
    const scenarioSelect = document.getElementById("scenario");

    if (!categorySelect || !scenarioSelect) return;

    const selectedCategory = categorySelect.value;
    const scenarios = [
    ...(scenariosByCategory[selectedCategory] || []),
    { value: "LIBRE", text: "LIBRE" }
];

    scenarioSelect.innerHTML = "";

    scenarios.forEach(scenario => {
        const option = document.createElement("option");
        option.value = scenario.value;
        option.textContent = scenario.text;
        scenarioSelect.appendChild(option);
    });

    updateExperimentSummary();
}


function updateExperimentSummary() {
    const categorySelect = document.getElementById("category");
    const scenarioSelect = document.getElementById("scenario");
    const checkboxes = document.querySelectorAll(
        ".models-list input[type='checkbox']"
    );

    const summaryCategory = document.getElementById("summary-category");
    const summaryScenario = document.getElementById("summary-scenario");
    const summaryModels = document.getElementById("summary-models");

    if (
        !categorySelect ||
        !scenarioSelect ||
        !summaryCategory ||
        !summaryScenario ||
        !summaryModels
    ) return;

    const selectedCategoryText =
        categorySelect.options[categorySelect.selectedIndex].text;

    const selectedScenarioText =
        scenarioSelect.options[scenarioSelect.selectedIndex]?.text || "";

    const selectedModelsCount =
        Array.from(checkboxes).filter(input => input.checked).length;

    summaryCategory.textContent = selectedCategoryText;

    summaryScenario.textContent = selectedScenarioText
        ? selectedScenarioText.split("·")[0].trim()
        : "—";

    summaryModels.textContent = selectedModelsCount;
}


async function startExperiment() {
    const button = document.getElementById("start-experiment-btn");

    if (!button) return;

    button.addEventListener("click", async () => {
        const scenarioSelect = document.getElementById("scenario");
        const categorySelect = document.getElementById("category");
        const checkboxes = document.querySelectorAll(
            ".models-list input[type='checkbox']"
        );

        if (!scenarioSelect || !scenarioSelect.value) {
            alert("Selecciona un escenario.");
            return;
        }

        const scenarioCode = scenarioSelect.value;
        const category = categorySelect?.value || null;

        const selectedModels = Array.from(checkboxes)
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.parentElement.textContent.trim());

        if (selectedModels.length === 0) {
            alert("Selecciona al menos un modelo de IA.");
            return;
        }

        button.disabled = true;
        button.textContent = "Creando experimento...";

        try {
            const response = await fetch("/api/experiments", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    scenario_code: scenarioCode,
                    model_names: selectedModels,
                    category: category
                })
            });

            const data = await response.json();

            if (response.ok && data.experiment_id) {
                window.location.href =
                    `/laboratorio?experiment_id=${data.experiment_id}`;
                return;
            }

            alert(
                data.detail ||
                "No se pudo crear el experimento."
            );

        } catch (error) {
            console.error("Error al crear el experimento:", error);
            alert("No se pudo conectar con el backend.");
        } finally {
            button.disabled = false;
            button.textContent = "Iniciar evaluación";
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    checkStatus();

    const categorySelect = document.getElementById("category");
    const scenarioSelect = document.getElementById("scenario");
    const checkboxes = document.querySelectorAll(
        ".models-list input[type='checkbox']"
    );

    updateScenariosByCategory();

    if (categorySelect) {
        categorySelect.addEventListener(
            "change",
            updateScenariosByCategory
        );
    }

    if (scenarioSelect) {
        scenarioSelect.addEventListener(
            "change",
            () => {
                updateExperimentSummary();
            }
        );
    }

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener(
            "change",
            updateExperimentSummary
        );
    });

    startExperiment();
});
