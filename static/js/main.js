/**
 * AthletIQ – client-side helpers
 *   • Delete confirmation dialog
 *   • Auto-dismiss flash messages
 *   • Simple form validation feedback
 */

/* ── Delete confirmation ── */
function confirmDelete(name) {
    return confirm(`Are you sure you want to delete athlete "${name}"?\n\nThis will also remove all associated training sessions, workout sets, recovery logs, and biometric entries.`);
}

function confirmDeleteExercise(name) {
    return confirm(`Are you sure you want to delete exercise "${name}"?\n\nThis will also remove all workout sets associated with this exercise.`);
}

function confirmDeleteSet(setId, athleteName) {
    return confirm(`Are you sure you want to delete workout set #${setId} for ${athleteName}?`);
}

/* ── Auto-dismiss flash messages after 6 seconds ── */
document.addEventListener("DOMContentLoaded", () => {
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach((flash) => {
        setTimeout(() => {
            flash.style.transition = "opacity .4s ease, transform .4s ease";
            flash.style.opacity = "0";
            flash.style.transform = "translateY(-8px)";
            setTimeout(() => flash.remove(), 400);
        }, 6000);
    });

    /* ── Form validation visual feedback ── */
    const form = document.getElementById("athlete-form");
    if (form) {
        form.addEventListener("submit", (e) => {
            const inputs = form.querySelectorAll(".form-input[required]");
            let valid = true;
            inputs.forEach((input) => {
                if (!input.value.trim()) {
                    input.style.borderColor = "var(--accent-coral)";
                    input.style.boxShadow = "0 0 0 3px rgba(244,63,94,.15)";
                    valid = false;
                } else {
                    input.style.borderColor = "";
                    input.style.boxShadow = "";
                }
            });
            if (!valid) {
                e.preventDefault();
            }
        });
    }
});
