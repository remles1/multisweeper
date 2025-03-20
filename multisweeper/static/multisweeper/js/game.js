// TODO make timer turn based, current logic is a remnant of singleplayer minesweeper

const socket = new WebSocket(`ws://localhost:8000/ws/lobby/${lobby_id}`);
let firstClick = true;
let startTime = null;
let timerRunning = false;
let timerInterval = null;
let minesLeft = mine_count;
mines_left_update_counter(minesLeft);
update_seconds_counter(0)
let username = null;
let state = ""



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
    "f_0": "cell-flagged-0",
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
    if(data["type"] === "seats"){
        render_seats_and_controls(data);
    }
    else if(data["type"] === "game_over"){
        if (data["draw"]){
            alert('draw');
        }
        else{
            let winner_username = data["winner_username"]
            alert(`${winner_username} is the winner! Congratulations!`);
        }

    }
    else if(data["type"] === "state"){
        state = data["message"];
    }
    else if(data["type"] === "username"){
        username = data["message"];
    }
    else if(data["type"] === "game_in_progress_redirect"){
        location.replace("/game-in-progress/");
    }
    else if(data["type"] === "user_board"){
        let user_board = JSON.parse(data["message"])
        let user_board_mapped = user_board.map(row =>
            row.map(cell => user_board_dict[cell])
        )
        //console.log(user_board)
        render_user_board(user_board, user_board_mapped)
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

function render_user_board(user_board, user_board_mapped) {
    const board = document.getElementById("board");
    board.innerHTML = '';

    minesLeft = mine_count;
    for (let i = 0; i < user_board.length; i++) {
        for (let j = 0; j < user_board[0].length; j++) {
            let cell = document.createElement("div");
            cell.id = "id" + i + "-" + j;
            cell.className = "cell " + user_board_mapped[i][j];
            if(user_board[i][j].includes("f")){
                minesLeft--;
            }
            cell.addEventListener("mousedown", cellMouseDown);
            cell.addEventListener("mouseup", cellMouseUp);
            cell.addEventListener("mouseover", cellMouseOver);
            cell.addEventListener("mouseleave", cellMouseLeave);

            board.appendChild(cell)
        }
    }
    mines_left_update_counter(minesLeft)
}

function render_seats_and_controls(data){
    const seats = data["seats"];
    const scores = data["scores"];
    const elo_ratings = data["elo_ratings"];
    console.log(elo_ratings);
    const active_seat = `${data["active_seat"]}`;
    const owner = `${data["owner"]}`;
    const start_game_button = document.getElementById("start-game-button");
    if(username === owner && state !== 'LobbyGameInProgressState'){
        start_game_button.style.display = 'inline';
    }
    else {
        start_game_button.style.display = 'none';
    }

    for(let key in seats){
        const score_div = document.getElementById(`score-${key}`);
        const player_color_icon = document.getElementById(`player-color-icon-${key}`);
        const player_seat_span = document.getElementById(`player-seat-${key}`);
        const owner_player_controls = document.getElementById(`owner-player-controls-${key}`);
        const username_in_this_seat = `${seats[key]}`;
        const elo_div = document.getElementById(`elo-${key}`)

        // player colors and turn indicator
        if(active_seat === key){
            player_color_icon.className = `triangle triangle-${key}`;
        }
        else {
            player_color_icon.className = `circle circle-${key}`;
        }


        // if the username is the owner (username is a global variable assigned to the file),
        // show owner controls along every seat
        if(username === owner && state !== 'LobbyGameInProgressState'){
            owner_player_controls.style.display = 'inline';
        }
        else {
            owner_player_controls.style.display = 'none';
        }


        if(username_in_this_seat === 'null'){
            player_seat_span.innerHTML = `Empty seat #${parseInt(key)+1}`;

            // if the seat is empty, hide the owner controls
            owner_player_controls.style.display = 'none';
        }
        else{
            player_seat_span.innerHTML = `${username_in_this_seat}`;
        }
        if(username_in_this_seat === owner){


            player_seat_span.innerHTML = `${username_in_this_seat} OWNER`;

            //dont display owner controls for owners' seat
            owner_player_controls.style.display = 'none';
        }

        if (scores[key] === undefined) {
            score_div.innerHTML = "SCORE: 0"; // or any default value
        } else {
            score_div.innerHTML = `SCORE: ${scores[key]}`;
        }

        if (elo_ratings[key] === null){
            elo_div.innerHTML = '-';
        }
        else {
            if (elo_ratings[key] === '--GUEST--'){
                elo_div.innerHTML = `${elo_ratings[key]}`
            }
            else {
                elo_div.innerHTML = `${elo_ratings[key]} ELO`;
            }

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

function chooseSeat(seat){
    const message = JSON.stringify({
        type: "choose_seat",
        message: seat,
    })
    socket.send(message)
}

function promoteToOwner(seat){
    const message = JSON.stringify({
        type: "promote_to_owner",
        message: seat,
    })
    socket.send(message)
}

function startGame(){
    const message = JSON.stringify({
        type: "start_game",
    })
    socket.send(message)
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

