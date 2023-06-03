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

            // Touch events for mobile users
            let touchStartX, touchStartTime, tapCount = 0;

            textfield.addEventListener("touchstart", (event) => {
                touchStartX = event.touches[0].clientX;
                touchStartTime = Date.now();
            });

            textfield.addEventListener("touchend", (event) => {
                const touchEndX = event.changedTouches[0].clientX;
                const touchEndTime = Date.now();
                const deltaPosition = touchEndX - touchStartX;
                const deltaTime = touchEndTime - touchStartTime;

                if (deltaTime < 200 && Math.abs(deltaPosition) < 50) {  // Thresholds for a tap
                    tapCount += 1;
                    setTimeout(() => {
                        tapCount = 0;
                    }, 400);  // Reset tapCount after 400ms
                    if (tapCount === 2) {
                        // Double-tap: Show hidden select menu
                        this.showHistorySelectMenu(textfield, history);
                    }
                } else if (deltaTime < 500 && Math.abs(deltaPosition) > 50) {  // Thresholds for a swipe
                    if (deltaPosition > 0) {
                        // Swipe left: next value
                        index = Math.min(history.length, index + 1);
                    } else {
                        // Swipe right: previous value
                        index = Math.max(0, index - 1);
                    }
                    textfield.value = history[index] || "";
                }
            });

            this.registeredElements.set(id, {textfield, history, index});
        }
    }

    storeHistory(textfield) {
        const id = `${this.username}-${textfield.id}`;
        const {history, index} = this.registeredElements.get(id);

        const valueIndex = history.indexOf(textfield.value);
        if (valueIndex !== -1) {
            // Remove the existing value from the history
            history.splice(valueIndex, 1);
        }

        history.push(textfield.value);
        this.saveHistory(id, history);
        this.registeredElements.set(id, {textfield, history, index: history.length});
    }

    showHistorySelectMenu(textfield, history) {
        // Implementation of the select menu depends on your actual DOM structure and CSS
        // Here is a simple example:
        let selectMenu = document.getElementById("hiddenSelectMenu");
        if (!selectMenu) {
            selectMenu = document.createElement("select");
            selectMenu.id = "hiddenSelectMenu";
            document.body.appendChild(selectMenu);
        }
        selectMenu.innerHTML = history.map(value => `<option>${value}</option>`).join("");
        selectMenu.style.display = "block";
        selectMenu.addEventListener("change", () => {
            textfield.value = selectMenu.value;
            selectMenu.style.display = "none";
        });
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
