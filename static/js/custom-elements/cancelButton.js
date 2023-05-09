class cancelButton {
    constructor(element) {
        this.element = element;
        this.onClick = this.onClick.bind(this);
        this.element.addEventListener('click', this.onClick);
    }

    async onClick() {
        const result = await sendMessage("cancel", {}, true);
    }

    static init() {
        const $buttons = $('.cancelButton');
        if ($buttons.length) {
            return $buttons.get().map(button => new cancelButton(button));
        } else {
            const button = document.createElement('button');
            button.className = 'cancelButton';
            return [new cancelButton(button)];
        }
    }
}

$.fn.cancelButton = function () {
    const buttons = cancelButton.init();
    return buttons.length === 1 ? $(buttons[0].element) : $(buttons.map(button => button.element));
};
