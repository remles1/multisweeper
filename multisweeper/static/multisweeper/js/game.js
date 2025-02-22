const socket = new WebSocket(`ws://localhost:8000/ws/lobby/${lobby_id}`);
let firstClick = true;
let startTime = null;
let timerRunning = false;
let timerInterval = null;
let minesLeft = mine_count;
mines_left_update_counter(minesLeft);
update_seconds_counter(0)



document.querySelector('#new-game-button').addEventListener('click', () => {
    restart_game();
    const stats_div = document.getElementById("stats");
    stats_div.style.display = "none";

});

function restart_game(){
    const message = JSON.stringify({
        type: "new_game",
        message: ""
    })
    socket.send(message)
    firstClick = true;
    startTime = null;
    timerRunning = false;
    minesLeft = mine_count;
    mines_left_update_counter(minesLeft);

    if (timerInterval) {
        clearInterval(timerInterval);
    }
    timerInterval = null;
    update_seconds_counter(0);
    document.querySelector('#new-game-button').classList.value = 'face-button face-neutral';
}




let user_board_dict = {
    "c": "cell-closed",
    "0": "cell-0",
    "f_1": "cell-flagged-1",
    "f_2": "cell-flagged-2",
    "fw": "cell-flagged-wrong",
    "m": "cell-mine",
    "me": "cell-mine-exploded",
    "1": "cell-1",
    "2": "cell-2",
    "3": "cell-3",
    "4": "cell-4",
    "5": "cell-5",
    "6": "cell-6",
    "7": "cell-7",
    "8": "cell-8",
    "pressed": "cell-pressed"
}

socket.onopen = function (e) {
    console.log("WebSocket Connected!");

};

socket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    if(data["type"] === "user_board"){
        let user_board = JSON.parse(data["message"])
        user_board = user_board.map(row =>
            row.map(cell => user_board_dict[cell])
        )
        //console.log(user_board)
        render_user_board(user_board)
        let gameOver = data["over"];
        if (gameOver) {
            timerRunning = false;
            const div = document.querySelector('#board');
            Array.from(div.children).forEach(child => {
                const clonedChild = child.cloneNode(true);
                div.replaceChild(clonedChild, child);
            });

            if(data["won"]){
                mines_left_update_counter(0);
                update_seconds_counter(Math.floor(data["time"]/1000))
                document.querySelector('#new-game-button').classList.value = 'face-button face-happy';
            }
            else {
                document.querySelector('#new-game-button').classList.value = 'face-button face-sad';
            }
            let timeSpent = data["time"] / 1000;
            console.log(timeSpent);
        }
    }
};

socket.onclose = function (e) {
    console.log("WebSocket Disconnected!");
};

function render_user_board(user_board) {
    const board = document.getElementById("board");
    board.innerHTML = '';
    for (let i = 0; i < user_board.length; i++) {
        for (let j = 0; j < user_board[0].length; j++) {
            let cell = document.createElement("div");
            cell.id = "id" + i + "-" + j;
            cell.className = "cell " + user_board[i][j];

            cell.addEventListener("mousedown", cellMouseDown);
            cell.addEventListener("mouseup", cellMouseUp);
            cell.addEventListener("mouseover", cellMouseOver);
            cell.addEventListener("mouseleave", cellMouseLeave);

            board.appendChild(cell)
        }
    }
}

let leftPressed = false;

function cellMouseDown(event) {
    if (event.button !== 0) {
        return;
    }
    leftPressed = true;
    if (event.button === 0 && !this.classList.contains(user_board_dict["f"]) && !this.classList.contains(user_board_dict["0"])) {
        this.classList.add(user_board_dict["pressed"]);
    }

}

function cellMouseOver(event) {
    event.preventDefault();
    if (leftPressed) {
        this.classList.add(user_board_dict["pressed"]);
    }
}

function cellMouseLeave(event) {
    event.preventDefault();
    if (this.classList.contains(user_board_dict["pressed"])) {
        this.classList.remove(user_board_dict["pressed"]);
    }
}

function cellMouseUp(event) {
    if (event.button !== 0) {
        return;
    }
    leftPressed = false;

    if (this.classList.contains(user_board_dict["0"])) {
        return;
    }


    else {
        const message = JSON.stringify({
            type: "l_click",
            message: this.id.replace(/^id/, "")
        })
        socket.send(message)
    }


    if (firstClick) {
        startTime = performance.now()
        timerRunning = true;
        timer();
        firstClick = false;
    }
}


function timer() {
    let seconds = 0;
    timerInterval=setInterval(()=>{
        if (!timerRunning) {
            return;
        }
        seconds += 1;
        update_seconds_counter(seconds)
    },1000);
}

function update_seconds_counter(seconds){
    let seconds_as_digits = convertNumberTo3Digits(seconds);
        for(let i = 0; i < 3; i++){
            let digit_div = document.getElementById(`sc_d${i}`)
            digit_div.classList.value = `digit digit-${seconds_as_digits[i]}`;
        }
}

function mines_left_update_counter(mine_count){
    let mines_left_as_digits = convertNumberTo3Digits(mine_count);
    for(let i = 0; i < 3; i++){
            let digit_div = document.getElementById(`mlc_d${i}`)
            digit_div.classList.value = `digit digit-${mines_left_as_digits[i]}`;
    }
}

function convertNumberTo3Digits(number){
    if (number > 999){
        return ['9','9','9'];
    }
    let formatted = number.toString().padStart(3,'0');
    return formatted.split('');
}