 
        window.addEventListener("pageshow", function (event) {
            if (event.persisted) window.location.reload();
        });

        const roomId = sessionStorage.getItem("room_id");
        let username = 'Guest';
        const password = sessionStorage.getItem("password");
        document.getElementById("roomIdDisplay").textContent = roomId || "N/A";

        const urls = {
            currentUserUrl: "{% url 'current_user' %}"  // replace with actual endpoint
        };

        function getJWTToken() {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [key, value] = cookie.trim().split('=');
                if (key === 'jwt') {
                    return decodeURIComponent(value);
                }
            }
            return null;
        }

        async function checkAuthAndInit() {
            const token = getJWTToken();
            if (!token) {
                console.log("JWT not found in cookies.");
                window.location.href = "{% url 'account:login' %}";
                return;
            }

            try {
                const response = await fetch(urls.currentUserUrl, {
                    method: "GET",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    username = data.username;
                    initWebSocket();
                } else {
                    console.warn("Token invalid or expired");
                    window.location.href = "{% url 'account:login' %}";
                }
            } catch (error) {
                console.error("Auth check failed:", error);
                window.location.href = "{% url 'account:login' %}";
            }
        }

        checkAuthAndInit();

        function logout() {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [key] = cookie.trim().split('=');
                document.cookie = `${key}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;`;
            }
            location.reload();
        }

        function initWebSocket() {
            let isadminpage_updated = false;
            let selectedgamecard = null;
            let socket;
            const countdownElement = document.getElementById("countdown");

            function startCountdown(data) {
                const owner = sessionStorage.getItem("owner");
                let counter = 3;
                const countdownElement = document.getElementById("countdown");
                countdownElement.style.display = "block";
                countdownElement.textContent = counter;
                const gamePageURL = data.redirect_url;

                if (username === owner) {
                    countdownElement.textContent = "0";
                    window.location.href = "{% url 'waitforplayers' %}?gamePage=" + encodeURIComponent(gamePageURL);
                } else {
                    const interval = setInterval(() => {
                        counter--;
                        countdownElement.textContent = counter;
                        if (counter === 0) {
                            clearInterval(interval);
                            window.location.href = "{% url 'waitforplayers' %}?gamePage=" + encodeURIComponent(gamePageURL);
                        }
                    }, 1000);

                }
            }



            if (!roomId || !username || !password) {
                window.location.href = "{% url 'account:login' %}";
            } else {
                const protocol = window.location.protocol === "https:" ? "wss" : "ws";
                const token = getJWTToken();

                socket = new WebSocket(
                    `${protocol}://${window.location.host}/ws/wait/${roomId}/?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&token=${token}`
                );



                const ul = document.getElementById("playerList");

                const updatePlayerList = (players) => {
                    ul.innerHTML = "";
                    players.forEach(player => {
                        const li = document.createElement("li");
                        li.textContent = player;
                        ul.appendChild(li);
                    });
                };

                const gameListContainer = document.getElementById("gameListContainer");

                function updateGameList(games) {
                    gameListContainer.innerHTML = "";
                    const owner = sessionStorage.getItem("owner");

                    games.forEach(game => {
                        const card = document.createElement("div");
                        card.classList.add("game-card");
                        card.textContent = game;

                        if (username === owner) {
                            card.addEventListener("click", () => {
                                document.querySelectorAll(".game-card").forEach(c => c.classList.remove("selected"));
                                card.classList.add("selected");
                                selectedgamecard = game;

                                if (socket && socket.readyState === WebSocket.OPEN) {
                                    socket.send(JSON.stringify({
                                        type: "game_selected",
                                        room_id: roomId,
                                        username: username,
                                        selected_game: selectedgamecard
                                    }));
                                }
                            });
                        }

                        gameListContainer.appendChild(card);
                    });
                }

                socket.onmessage = function (event) {
                    const data = JSON.parse(event.data);

                    if (data.type === "players_update" && Array.isArray(data.players)) {
                        console.log("players_lst:", data.players);

                        updatePlayerList(data.players);

                        if (data.error) {
                            document.getElementById("error").innerText = data.error;
                        }
                        if (data.owner) {
                            sessionStorage.setItem('owner', data.owner);
                        }
                        if (data.selected_game) {
                            const selectedGame = data.selected_game;
                            const owner = sessionStorage.getItem("owner");

                            setTimeout(() => {
                                document.querySelectorAll(".game-card").forEach(c => {
                                    c.classList.toggle("selected", c.textContent.trim().toLowerCase() === selectedGame.toLowerCase());
                                    selectedgamecard = selectedGame;
                                });
                            }, 100); // delay in ms
                        }

                    }

                    if (data.error) {
                        document.getElementById("error").innerText = data.error;
                    }

                    if (data.owner) {
                        sessionStorage.setItem('owner', data.owner);
                        document.getElementById("startGameBtn").style.display =
                            username === data.owner ? "block" : "none";
                    }


                    if (data.type === "game_started") {
                        startCountdown(data);
                    }

                    if (data.gamelist) {
                        updateGameList(data.gamelist);
                        if (data.owner === username && !isadminpage_updated) {
                            isadminpage_updated = true;
                        }
                    }

                    if (data.selected_game) {
                        const selectedGame = data.selected_game;
                        const owner = sessionStorage.getItem("owner");

                        if (username !== owner) {
                            document.querySelectorAll(".game-card").forEach(c => {
                                c.classList.toggle("selected", c.textContent === selectedGame);
                            });
                        }
                    }
                };

                socket.onopen = () => console.log("WebSocket connected.");
                socket.onclose = (event) => {
                    console.warn("WebSocket closed:", event);
                    // Optional: handle reconnection logic here
                };

                document.getElementById("startGameBtn").addEventListener("click", () => {
                    if (selectedgamecard) {
                        socket.send(JSON.stringify({
                            type: "start_game",
                            room_id: roomId,
                            selected_game: selectedgamecard
                        }));
                    } else {
                        document.getElementById("error").innerText = "Please select a game to start.";
                    }
                });
            }
        }