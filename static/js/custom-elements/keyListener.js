class KeyListener {
    constructor() {
        this.listeners = {};
        this.handleKeyDown = this.handleKeyDown.bind(this);
        document.addEventListener("keydown", this.handleKeyDown);
    }

    handleKeyDown(event) {
        Object.keys(this.listeners).forEach((key) => {
            const [keyCommand, selector] = key.split("|");
            let modifier = null;
            let keyCheck = keyCommand;

            if (keyCommand.indexOf("+") > -1) {
                [modifier, keyCheck] = keyCommand.split("+");
            }

            const elements = document.querySelectorAll(selector);
            const isCorrectKey = event.key === keyCheck;
            const isCorrectModifier = modifier ? event[`${modifier}Key`] : true;
            const isElementWithinSelector = Array.from(elements).some(
                (element) => element.contains(event.target)
            );
            if (isCorrectKey && isCorrectModifier && isElementWithinSelector) {
                event.preventDefault();
                this.listeners[key].forEach((callback) => callback());
            }
        });
    }

    register(keyCommand, selector, callback) {
        const key = `${keyCommand}|${selector}`;
        if (!this.listeners[key]) {
            this.listeners[key] = [];
        }
        this.listeners[key].push(callback);
    }

    unregister(keyCommand, selector, callback) {
        const key = `${keyCommand}|${selector}`;
        if (callback) {
            const index = this.listeners[key].indexOf(callback);
            this.listeners[key].splice(index, 1);
        } else {
            delete this.listeners[key];
        }
    }
}
