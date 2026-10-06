(function () {
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const clearBtn = document.getElementById("clearBtn");
  const chatLog = document.getElementById("chatLog");

  const INITIAL_BOT_MESSAGE = "Hello! I'm SupportBot. How can I help you today?";
  let waiting = false;

  function createMessage(text, sender) {
    const wrapper = document.createElement("div");
    wrapper.className = "message " + sender + "-message";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;

    wrapper.appendChild(bubble);
    chatLog.appendChild(wrapper);
    chatLog.scrollTop = chatLog.scrollHeight;
    return wrapper;
  }

  function createTypingIndicator() {
    const wrapper = document.createElement("div");
    wrapper.className = "message bot-message";
    wrapper.id = "typingIndicator";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble typing-bubble";
    bubble.setAttribute("aria-label", "SupportBot is typing");
    bubble.innerHTML = "<span></span><span></span><span></span>";

    wrapper.appendChild(bubble);
    chatLog.appendChild(wrapper);
    chatLog.scrollTop = chatLog.scrollHeight;
    return wrapper;
  }

  function removeTypingIndicator() {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) {
      indicator.remove();
    }
  }

  function setWaiting(isWaiting) {
    waiting = isWaiting;
    sendBtn.disabled = isWaiting;
    messageInput.disabled = isWaiting;
  }

  async function sendMessage(message) {
    setWaiting(true);
    createMessage(message, "user");
    createTypingIndicator();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message }),
      });

      let data = {};
      try {
        data = await response.json();
      } catch (parseError) {
        data = {};
      }

      removeTypingIndicator();

      if (!response.ok) {
        createMessage(
          data.error || "Sorry, something went wrong. Please try again.",
          "bot"
        );
        return;
      }

      createMessage(data.reply || "Sorry, I could not generate a response.", "bot");
    } catch (networkError) {
      removeTypingIndicator();
      createMessage(
        "Sorry, I could not reach the support service. Please check your connection and try again.",
        "bot"
      );
    } finally {
      setWaiting(false);
      messageInput.focus();
    }
  }

  chatForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (waiting) {
      return;
    }

    const message = messageInput.value.trim();
    if (!message) {
      return;
    }

    messageInput.value = "";
    sendMessage(message);
  });

  clearBtn.addEventListener("click", async function () {
    if (waiting) {
      return;
    }

    try {
      await fetch("/api/clear", { method: "POST" });
    } catch (networkError) {
      chatLog.innerHTML = "";
      createMessage(INITIAL_BOT_MESSAGE, "bot");
      return;
    }

    chatLog.innerHTML = "";
    createMessage(INITIAL_BOT_MESSAGE, "bot");
    messageInput.value = "";
    messageInput.focus();
  });

  messageInput.focus();
})();
