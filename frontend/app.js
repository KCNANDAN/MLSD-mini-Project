
const API_BASE_URL = "http://127.0.0.1:8002/api/v1";

const petitionForm = document.getElementById("petition-form");
const submitButton = document.getElementById("submit-button");
const formMessage = document.getElementById("form-message");

const resultSection = document.getElementById("result-section");
const runStatus = document.getElementById("run-status");
const runIdElement = document.getElementById("run-id");
const resultContent = document.getElementById("result-content");

let pollingTimer = null;

const POLLING_INTERVAL_MS = 2500;
const MAX_POLLING_ATTEMPTS = 120;


// --------------------------------------------------
// Utility functions
// --------------------------------------------------

function showMessage(message, isError = false) {
    formMessage.textContent = message;
    formMessage.style.color = isError ? "#c0392b" : "#718096";
}


function setSubmitting(isSubmitting) {
    submitButton.disabled = isSubmitting;

    submitButton.innerHTML = isSubmitting
        ? "Submitting petition..."
        : 'Submit petition <span aria-hidden="true">→</span>';
}


function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined && text !== null) {
        element.textContent = String(text);
    }

    return element;
}


function clearPolling() {
    if (pollingTimer !== null) {
        clearTimeout(pollingTimer);
        pollingTimer = null;
    }
}


function showResultSection(runId, status) {
    resultSection.classList.remove("hidden");

    runIdElement.textContent = runId;

    updateRunStatus(status);

    resultContent.replaceChildren(
        createElement(
            "p",
            "",
            "Your petition has been submitted and is awaiting processing."
        )
    );

    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
}


function updateRunStatus(status) {
    runStatus.textContent = String(status).toUpperCase();

    runStatus.className = "status-badge";

    if (status === "completed") {
        runStatus.style.background = "#e8f7ef";
        runStatus.style.color = "#16865b";
    } else if (status === "failed") {
        runStatus.style.background = "#fff0f0";
        runStatus.style.color = "#c0392b";
    } else {
        runStatus.style.background = "#edf1ff";
        runStatus.style.color = "#3157d5";
    }
}


// --------------------------------------------------
// API request handling
// --------------------------------------------------

async function submitPetition(payload) {
    const response = await fetch(
        `${API_BASE_URL}/petitions`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail || "Unable to submit your petition."
        );
    }

    return data;
}


async function fetchRunStatus(runId) {
    const response = await fetch(
        `${API_BASE_URL}/runs/${encodeURIComponent(runId)}`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail || "Unable to retrieve petition status."
        );
    }

    return data;
}


// --------------------------------------------------
// Result rendering
// --------------------------------------------------

function renderCitations(citations) {
    const section = createElement("div");

    section.appendChild(
        createElement("h4", "", "Regulatory citations")
    );

    if (!citations || citations.length === 0) {
        section.appendChild(
            createElement(
                "p",
                "",
                "No verified regulatory citations are available."
            )
        );

        return section;
    }

    citations.forEach((citation) => {
        const card = createElement("div", "citation-card");

        card.appendChild(
            createElement(
                "h4",
                "",
                `${citation.document_name} — ${citation.chapter}, ${citation.clause}`
            )
        );

        if (citation.page !== null && citation.page !== undefined) {
            card.appendChild(
                createElement(
                    "p",
                    "",
                    `Page: ${citation.page}`
                )
            );
        }

        card.appendChild(
            createElement(
                "p",
                "",
                citation.excerpt
            )
        );

        section.appendChild(card);
    });

    return section;
}


function renderEligibilityResult(result) {
    resultContent.replaceChildren();

    if (!result) {
        resultContent.appendChild(
            createElement(
                "p",
                "",
                "No eligibility result is available."
            )
        );

        return;
    }

    const recommendation = createElement(
        "div",
        "recommendation-card"
    );

    recommendation.appendChild(
        createElement(
            "span",
            "result-label",
            "RECOMMENDATION"
        )
    );

    recommendation.appendChild(
        createElement(
            "h3",
            "",
            result.recommendation.replaceAll("-", " ").toUpperCase()
        )
    );

    recommendation.appendChild(
        createElement(
            "p",
            "",
            result.basis
        )
    );

    resultContent.appendChild(recommendation);

    resultContent.appendChild(
        createElement(
            "h4",
            "",
            "Eligibility position"
        )
    );

    resultContent.appendChild(
        createElement(
            "p",
            "",
            result.eligibility_position
        )
    );

    resultContent.appendChild(
        renderCitations(result.citations)
    );

    if (result.escalation_path) {
        resultContent.appendChild(
            createElement(
                "h4",
                "",
                "Escalation path"
            )
        );

        resultContent.appendChild(
            createElement(
                "p",
                "",
                result.escalation_path
            )
        );
    }

    if (result.human_decision_required) {
        const notice = createElement(
            "div",
            "notice",
            "Human review required. This recommendation is not a final academic decision."
        );

        resultContent.appendChild(notice);
    }
}


function renderFailedRun(error) {
    resultContent.replaceChildren(
        createElement(
            "p",
            "",
            `Processing failed: ${error || "An unexpected error occurred."}`
        )
    );
}


// --------------------------------------------------
// Asynchronous status polling
// --------------------------------------------------

async function pollRunStatus(runId, attempt = 0) {
    if (attempt >= MAX_POLLING_ATTEMPTS) {
        showMessage(
            "Status polling limit reached. You can still track this petition using its run ID.",
            true
        );

        return;
    }

    try {
        const run = await fetchRunStatus(runId);

        updateRunStatus(run.status);

        if (run.status === "completed") {
            clearPolling();

            renderEligibilityResult(run.result);

            showMessage(
                "Petition processing completed successfully."
            );

            return;
        }

        if (run.status === "failed") {
            clearPolling();

            renderFailedRun(run.error);

            showMessage(
                "Petition processing failed.",
                true
            );

            return;
        }

        resultContent.replaceChildren(
            createElement(
                "p",
                "",
                run.status === "running"
                    ? "Your petition is currently being processed by the agent workflow."
                    : "Your petition is waiting in the processing queue."
            )
        );

        pollingTimer = setTimeout(
            () => pollRunStatus(runId, attempt + 1),
            POLLING_INTERVAL_MS
        );

    } catch (error) {
        clearPolling();

        showMessage(
            `Unable to track petition: ${error.message}`,
            true
        );
    }
}


// --------------------------------------------------
// Petition form submission
// --------------------------------------------------

petitionForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    clearPolling();

    setSubmitting(true);

    showMessage("Submitting your petition...");

    const formData = new FormData(petitionForm);

    const payload = {
        student_reference: formData.get("student_reference").trim(),

        petition_type: formData.get("petition_type"),

        admission_batch: formData.get("admission_batch").trim(),

        semester: Number(formData.get("semester")),

        description: formData.get("description").trim(),

        additional_details: {},
    };

    const additionalDetails = formData
        .get("additional_details")
        .trim();

    if (additionalDetails) {
        payload.additional_details = {
            notes: additionalDetails,
        };
    }

    try {
        const accepted = await submitPetition(payload);

        showResultSection(
            accepted.run_id,
            accepted.status
        );

        showMessage(
            "Petition accepted. Tracking processing status..."
        );

        pollRunStatus(accepted.run_id);

    } catch (error) {
        showMessage(
            error.message,
            true
        );

    } finally {
        setSubmitting(false);
    }
});


// --------------------------------------------------
// Initial state
// --------------------------------------------------

console.info(
    "Academic Petition Triage frontend initialized."
);
