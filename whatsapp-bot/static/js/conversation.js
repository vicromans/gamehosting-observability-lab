function scrollChatToBottom() {
    const chat = document.getElementById("chat-container");

    if (chat) {
        chat.scrollTop = chat.scrollHeight;
    }
}

function setupEnterToSend() {
    const textarea = document.getElementById("reply-textarea");
    const form = document.getElementById("reply-form");

    if (!textarea || !form) {
        return;
    }

    textarea.addEventListener("keydown", function(event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();

            if (textarea.value.trim().length > 0) {
                form.submit();
            }
        }
    });
}

window.addEventListener("load", function() {
    scrollChatToBottom();
    setupEnterToSend();
});
function setupTemplatePanel() {
    const openButton = document.getElementById("open-template-panel");
    const closeButton = document.getElementById("close-template-panel");
    const panel = document.getElementById("template-panel");

    if (!openButton || !closeButton || !panel) {
        return;
    }

    openButton.addEventListener("click", function() {
        panel.classList.add("visible");
    });

    closeButton.addEventListener("click", function() {
        panel.classList.remove("visible");
    });
}

window.addEventListener("load", function() {
    setupTemplatePanel();
});
