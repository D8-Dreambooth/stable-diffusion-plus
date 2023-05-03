// This sounds like a scary class, but it's just a simple class to track the history of a textfield.
// Use alt+up and alt+down to navigate through the history.

class HistoryTracker {
    constructor() {
        this.registeredElements = new Map();
    }

    registerHistory(textfield) {
        const id = textfield.id;

        if (!this.registeredElements.has(id)) {
            console.log("Registering textfield...", id);
            const history = this.loadHistory(id) || [];
            let index = history.length;

            textfield.addEventListener("keydown", (event) => {
                console.log("keydown", event.key, event.shiftKey);
                if (event.altKey && event.key === "ArrowUp") {
                    index = Math.max(0, index - 1);
                    textfield.value = history[index] || "";
                } else if (event.altKey && event.key === "ArrowDown") {
                    index = Math.min(history.length, index + 1);
                    textfield.value = history[index] || "";
                }
            });

            this.registeredElements.set(id, {textfield, history, index});
        }
    }

    storeHistory(textfield) {
        const id = textfield.id;
        const {history, index} = this.registeredElements.get(id);

        if (textfield.value !== history[history.length - 1]) {
            history.push(textfield.value);
            this.saveHistory(id, history);
            this.registeredElements.set(id, {textfield, history, index: history.length});
        }
    }

    loadHistory(id) {
        const historyString = getHistoryCookie(id);
        if (historyString) {
            return JSON.parse(historyString);
        }
        return null;
    }

    saveHistory(id, history) {
        setHistoryCookie(id, JSON.stringify(history));
    }
}

function getHistoryCookie(name) {
    const cookieName = encodeURIComponent(name) + "=";
    const cookieArray = document.cookie.split(";");

    for (let i = 0; i < cookieArray.length; i++) {
        let cookie = cookieArray[i];

        while (cookie.charAt(0) === " ") {
            cookie = cookie.substring(1);
        }

        if (cookie.indexOf(cookieName) === 0) {
            return decodeURIComponent(cookie.substring(cookieName.length, cookie.length));
        }
    }

    return null;
}

function setHistoryCookie(name, value) {
    const cookieValue = encodeURIComponent(value);
    const cookieName = encodeURIComponent(name);
  document.cookie = `${cookieName}=${cookieValue}; path=/`;
}
