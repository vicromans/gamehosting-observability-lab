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

function setupChatAutoRefresh() {
    const chat = document.getElementById("chat-container");

    if (!chat) {
        return;
    }

    const path = window.location.pathname;
    const messagesUrl = path.endsWith("/") ? path + "messages" : path + "/messages";

    async function refreshMessages() {
        try {
            const currentScrollBottom =
                chat.scrollHeight - chat.scrollTop - chat.clientHeight;
            const shouldStickToBottom = currentScrollBottom < 80;

            const response = await fetch(messagesUrl, {
                cache: "no-store"
            });

            if (!response.ok) {
                return;
            }

            const html = await response.text();

            if (!html) {
                return;
            }

            const normalizedContainer = document.createElement("div");
            normalizedContainer.innerHTML = html;
            const normalizedHtml = normalizedContainer.innerHTML;

            if (normalizedHtml === chat.innerHTML) {
                return;
            }

            const previousScrollHeight = chat.scrollHeight;
            const previousScrollTop = chat.scrollTop;

            chat.innerHTML = normalizedHtml;

            if (shouldStickToBottom) {
                scrollChatToBottom();
            } else {
                const addedHeight = chat.scrollHeight - previousScrollHeight;
                chat.scrollTop = previousScrollTop + addedHeight;
            }
        } catch (error) {
            console.log("Chat refresh error:", error);
        }
    }

    setInterval(refreshMessages, 2000);
}

window.addEventListener("load", function() {
    scrollChatToBottom();
    setupEnterToSend();
    setupTemplatePanel();
    setupChatAutoRefresh();
});
