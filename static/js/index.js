const ws = new WebSocket("ws://localhost:8080/ws");
ws.onmessage = function (event) {
    console.log("MESSAGE: ", event);
};

function sendMessage(event) {
    const input = document.getElementById("messageText");
    ws.send(input.value)
    input.value = ''
    event.preventDefault()
}