class HistoryTracker {
    constructor() {
        this.registeredElements = new Map();
        this.storage = window.localStorage || window.sessionStorage;
        this.username = this.getUsernameFromCookie();
    }

    getUsernameFromCookie() {
        const cookieValue = this.getCookieValue("user");
        if (cookieValue) {
            return cookieValue;
        }
        return null;
    }

    getCookieValue(name) {
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

    registerHistory(textfield) {
        const id = `${this.username}-${textfield.id}`;

        if (!this.registeredElements.has(id)) {
            const history = this.loadHistory(id) || [];
            let index = history.length;

            textfield.addEventListener("keydown", (event) => {
                if (event.altKey && event.key === "ArrowUp") {
                    index = Math.max(0, index - 1);
                    textfield.value = history[index] || "";
                } else if (event.altKey && event.key === "ArrowDown") {
                    index = Math.min(history.length, index + 1);
                    textfield.value = history[index] || "";
                }
            });

            this.registeredElements.set(id, { textfield, history, index });
        }
    }

    storeHistory(textfield) {
        const id = `${this.username}-${textfield.id}`;
        const { history, index } = this.registeredElements.get(id);

        if (textfield.value !== history[history.length - 1]) {
            history.push(textfield.value);
            this.saveHistory(id, history);
            this.registeredElements.set(id, { textfield, history, index: history.length });
        }
    }

    loadHistory(id) {
        const historyString = this.storage.getItem(id);
        if (historyString) {
            return JSON.parse(historyString);
        }
        return null;
    }

    saveHistory(id, history) {
        this.storage.setItem(id, JSON.stringify(history));
    }
}
