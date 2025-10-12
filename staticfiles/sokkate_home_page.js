   document.getElementById("exit-button").addEventListener("click", () => {
        const elem = document.documentElement; // full page
        if (!document.fullscreenElement) {
            elem.requestFullscreen(); // Enter fullscreen
            document.getElementById("exit-button").innerText="Exit"
        } else {
            document.exitFullscreen(); // Exit fullscreen
            document.getElementById("exit-button").innerText="Full Screen"
        }
        });

        let lastCards = [];
        let lastBorderColor = "gray";
        let currentSuitFilter = "ALL";
        let currentTurnPlayer = null;
        let username = 'Guest';
        const roomId = sessionStorage.getItem("room_id");
        const password = sessionStorage.getItem("password");
        let socket;

        let shuffleAnimation_flag=true

        function enableTouchDrag(cardElement) {
            let startX, startY, originalX, originalY;
            let dragging = false;

            cardElement.addEventListener("touchstart", function (e) {
                const touch = e.touches[0];
                startX = touch.clientX;
                startY = touch.clientY;

                const rect = cardElement.getBoundingClientRect();
                originalX = rect.left;
                originalY = rect.top;

                cardElement.style.position = 'absolute';
                cardElement.style.zIndex = '1000';
                dragging = true;
            });

            cardElement.addEventListener("touchmove", function (e) {
                if (!dragging) return;
                e.preventDefault();
                const touch = e.touches[0];
                const deltaX = touch.clientX - startX;
                const deltaY = touch.clientY - startY;

                cardElement.style.left = `${originalX + deltaX}px`;
                cardElement.style.top = `${originalY + deltaY}px`;
            });

            cardElement.addEventListener("touchend", function (e) {
                dragging = false;
                const table = document.getElementById('table');
                const rect = table.getBoundingClientRect();
                const touch = e.changedTouches[0];

                if (
                    touch.clientX > rect.left &&
                    touch.clientX < rect.right &&
                    touch.clientY > rect.top &&
                    touch.clientY < rect.bottom
                ) {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: 'playing_card', card: cardElement.getAttribute('data-card') }));
                    }
                }

                cardElement.style.position = '';
                cardElement.style.left = '';
                cardElement.style.top = '';
                cardElement.style.zIndex = '';
            });
        }

        function renderCards(cards, borderColor, suitFilter, isMyTurn) {
            const cardlistDiv = document.querySelector('.cardlist');
            cardlistDiv.innerHTML = '';

            let filteredCards = suitFilter !== "ALL"
                ? cards.filter(card => card.startsWith(suitFilter))
                : cards;

            filteredCards.forEach((card, idx) => {
                const cardDiv = document.createElement('div');
                cardDiv.classList.add('card');
                cardDiv.setAttribute('data-card', card);
                cardDiv.style.border = `3px solid ${borderColor}`;
                cardDiv.style.marginLeft = idx === 0 ? '0' : '-32px';
                cardDiv.draggable = isMyTurn;
                if (!isMyTurn) cardDiv.classList.add('drag-disabled');

                let symbol = "";
                if (card.startsWith("D")) symbol = "♦️";
                else if (card.startsWith("F")) symbol = "♣️";
                else if (card.startsWith("S")) symbol = "♠️";
                else if (card.startsWith("H")) symbol = "♥️";

                const cardValue = card.substring(1);

                const suitSpan = document.createElement('span');
                suitSpan.textContent = symbol;
                suitSpan.style.fontSize = '2rem';
                suitSpan.style.position = 'absolute';
                suitSpan.style.top = '50%';
                suitSpan.style.left = '50%';
                suitSpan.style.transform = 'translate(-50%, -50%)';

                const valueSpan = document.createElement('span');
                valueSpan.textContent = cardValue;
                valueSpan.style.fontSize = '2rem';
                valueSpan.style.position = 'absolute';
                valueSpan.style.top = '8px';
                valueSpan.style.left = '12px';

                cardDiv.appendChild(suitSpan);
                cardDiv.appendChild(valueSpan);

                if (isMyTurn) {
                    // Mouse drag events
                    cardDiv.addEventListener('dragstart', e => {
                        e.dataTransfer.setData('text/plain', card);
                        e.target.style.opacity = '0.5';
                    });
                    cardDiv.addEventListener('dragend', e => {
                        e.target.style.opacity = '1';
                    });

                    // Touch drag events
                    enableTouchDrag(cardDiv);
                }

                cardlistDiv.appendChild(cardDiv);
            });
        }

        function drawTable(players) {
            const table = document.getElementById("table");
            const centerX = table.clientWidth / 2;
            const centerY = table.clientHeight / 2;
            const personSize = 30;
            const radius = table.clientWidth / 2 + (personSize / 2);
            // Remove bubbles for players not in the new list
            const currentUsernames = players.map(p => p.username);
            table.querySelectorAll('.person').forEach(div => {
                const uname = div.getAttribute('data-username');
                if (!currentUsernames.includes(uname)) {
                    div.remove();
                }
            });

            // Keep track of existing player divs
            const existingDivs = {};
            table.querySelectorAll('.person').forEach(div => {
                const uname = div.getAttribute('data-username');
                existingDivs[uname] = div;
            });

            // Create new divs if they don't exist
            players.forEach(player => {
                if (!existingDivs[player.username]) {
                    const div = document.createElement('div');
                    div.className = 'person';
                    div.style.backgroundColor = "white";
                    div.style.borderColor = player.color || "gray";
                    div.innerText = player.username[0].toUpperCase();
                    div.setAttribute('data-username', player.username);
                    table.appendChild(div);
                    existingDivs[player.username] = div;
                }
                sessionStorage.setItem(`player_color_${player.username}`, player.color || "gray");
            });

            // Recalculate positions for all player divs
            const total = players.length;
            players.forEach((player, i) => {
                const angle = (2 * Math.PI * i) / total;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                const div = existingDivs[player.username];

                // Smooth movement using CSS transition
                div.style.transition = 'left 0.5s, top 0.5s';
                div.style.left = `${x - personSize / 2}px`;
                div.style.top = `${y - personSize / 2}px`;
                div.style.borderColor = player.color || "gray";
            });
        }



        const tableDiv = document.getElementById('table');
        tableDiv.addEventListener('dragover', e => e.preventDefault());
        tableDiv.addEventListener('drop', e => {
            e.preventDefault();
            const card = e.dataTransfer.getData('text/plain');
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'playing_card', card: card }));
            }
        });

        function updateTurnUI(currentPlayer) {
            const turnIndicator = document.getElementById('turn-indicator');
            document.querySelectorAll('.person.highlight').forEach(el => el.classList.remove('highlight'));

            if (currentPlayer === username) {
                turnIndicator.textContent = "🎯 Your turn!";
                document.querySelector('.cardlist').classList.add('rotating-border');
            } else {
                turnIndicator.textContent = `🕒 ${currentPlayer}'s turn...`;
                document.querySelector('.cardlist').classList.remove('rotating-border');
            }

            const playerElement = document.querySelector(`.person[data-username="${currentPlayer}"]`);
            if (playerElement) playerElement.classList.add("highlight");

            renderCards(lastCards, lastBorderColor, currentSuitFilter, currentPlayer === username);
            // 🔹 Enable/disable deck pile
            updateDeckPileState(currentPlayer);
        }

        function getJWTToken() {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [key, value] = cookie.trim().split('=');
                if (key === 'jwt') return decodeURIComponent(value);
            }
            return null;
        }

        async function checkAuthAndInit() {
            const token = getJWTToken();
            if (!token) return window.location.href = "{% url 'account:login' %}";

            try {
                const response = await fetch("{% url 'current_user' %}", {
                    method: "GET",
                    headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }
                });
                if (response.ok) {
                    const data = await response.json();
                    username = data.username;
                    initWebSocket();
                } else {
                    window.location.href = "{% url 'account:login' %}";
                }
            } catch (err) {
                window.location.href = "{% url 'account:login' %}";
            }
        }

        // card distribution logic start 
        let dealingInterval;
        let animationRunning = false;
        let pendingCardsData = null;

        function startDealingAnimation(players) {
            stopDealingAnimation();
            animationRunning = true;
            pendingCardsData = null;

            const table = document.getElementById("table");
            const deckPile = document.getElementById("deck-pile");
            const deckRect = deckPile.getBoundingClientRect();
            const tableRect = table.getBoundingClientRect();
            const centerX = deckRect.left - tableRect.left + deckRect.width / 2;
            const centerY = deckRect.top - tableRect.top + deckRect.height / 2;

            const total = players.length;
            let idx = 0;

            dealingInterval = setInterval(() => {
                const playerEl = players[idx];
                const playerRect = playerEl.getBoundingClientRect();

                const targetX = playerRect.left - tableRect.left + playerRect.width / 2;
                const targetY = playerRect.top - tableRect.top + playerRect.height / 2;

                const card = document.createElement("div");
                card.classList.add("dealing-card");
                const cardWidth = 40;
                const cardHeight = 60;

                card.style.left = (centerX - cardWidth / 2) + "px";
                card.style.top = (centerY - cardHeight / 2) + "px";
                card.style.setProperty("--target-transform",
                    `translate(${targetX - centerX}px, ${targetY - centerY}px)`
                );

                table.appendChild(card);
                setTimeout(() => card.remove(), 700);

                idx = (idx + 1) % total;
            }, 200);

            setTimeout(() => {
                stopDealingAnimation();
                if (pendingCardsData) {
                    showCards(pendingCardsData);
                    pendingCardsData = null;
                }
            }, 3000);
        }


        function stopDealingAnimation() {
            if (dealingInterval) clearInterval(dealingInterval);
            dealingInterval = null;
            document.querySelectorAll(".dealing-card").forEach(c => c.remove());
            animationRunning = false;
        }
        function showCards(data) {
            lastCards = data.player_cards;
            lastBorderColor = sessionStorage.getItem(`player_color_${username}`) || "gray";

            renderCards(lastCards, lastBorderColor, currentSuitFilter, currentTurnPlayer === username);
            
            socket.send(JSON.stringify({ type: "get_starting_player" }));

            // Wait for next tick so players divs exist
            setTimeout(() => {
                const players = Array.from(document.querySelectorAll(".person"));
                const remaining = 52 - (players.length ? data.player_cards.length * players.length : 0);
                createDeckPile(remaining);
            }, 50); // 50ms delay ensures DOM updated
        }
        // card distribution logic end


        // card deck drop animation start
        function createDeckPile(remainingCards = 52) {
            const deckPile = document.getElementById('deck-pile');
            deckPile.innerHTML = '';

            const maxVisible = 3;
            const visibleCount = Math.min(remainingCards, maxVisible);

            for (let i = 0; i < visibleCount; i++) {
                const cardDiv = document.createElement('div');
                cardDiv.classList.add('deck-card');
                cardDiv.style.left = '0px';
                cardDiv.style.top = `${-i * 2}px`; // small offset for stacked effect
                cardDiv.style.zIndex = i;
                cardDiv.style.transform = `rotate(${(Math.random() - 0.5) * 3}deg)`;
                cardDiv.style.width = '40px';
                cardDiv.style.height = '60px';
                deckPile.appendChild(cardDiv);
            }

            // card count
            const countSpan = document.createElement('span');
            countSpan.textContent = remainingCards;
            countSpan.style.color = 'black';            // color as string
            countSpan.style.position = 'absolute';      // full word
            countSpan.style.top = '50%';
            countSpan.style.left = '50%';
            countSpan.style.transform = 'translate(-50%, -50%)';
            countSpan.style.fontWeight = 'bold';
            countSpan.style.fontSize = '1.2rem';
            countSpan.style.textShadow = '0 0 3px white'; // optional for visibility
            countSpan.style.zIndex = 1000;
            deckPile.appendChild(countSpan);

        }

        // card deck drop animation end 

        // clear round animation start
        function animateRoundWinner(winnerPlayer, winnerCard, player_color_dict) {
            if (!winnerCard) return; // safety check

            const playedCardsDiv = document.getElementById('played-cards');
            const tableRect = playedCardsDiv.getBoundingClientRect();

            // vanish previous cards
            playedCardsDiv.querySelectorAll('.card').forEach(card => {
                card.style.transition = 'transform 0.4s ease, opacity 0.4s ease';
                card.style.transform = 'scale(0)';
                card.style.opacity = '0';
            });

            setTimeout(() => {
                playedCardsDiv.innerHTML = "";

                // create winner card
                const cardDiv = document.createElement('div');
                cardDiv.classList.add('card');
                cardDiv.style.width = '80px';
                cardDiv.style.height = '110px';
                cardDiv.style.border = `3px solid ${player_color_dict[winnerPlayer] || 'gold'}`;
                cardDiv.style.borderRadius = '10px';
                cardDiv.style.position = 'absolute';
                cardDiv.style.top = '50%';
                cardDiv.style.left = '50%';
                cardDiv.style.transform = 'translate(-50%, -50%) scale(0)';
                cardDiv.style.background = '#fff';
                cardDiv.style.display = 'flex';
                cardDiv.style.flexDirection = 'column';
                cardDiv.style.justifyContent = 'center';
                cardDiv.style.alignItems = 'center';
                cardDiv.style.fontWeight = 'bold';
                cardDiv.style.fontSize = '1rem';
                cardDiv.style.zIndex = 1000;
                cardDiv.style.transition = 'all 0.6s ease';

                // symbol & value
                let symbolMap = { D: "♦️", F: "♣️", S: "♠️", H: "♥️" };
                const symbol = symbolMap[winnerCard[0]] || "";
                const valueSpan = document.createElement('span');
                valueSpan.textContent = winnerCard.substring(1);
                valueSpan.style.fontSize = '1.2rem';
                const symbolSpan = document.createElement('span');
                symbolSpan.textContent = symbol;
                symbolSpan.style.fontSize = '2rem';
                cardDiv.appendChild(symbolSpan);
                cardDiv.appendChild(valueSpan);
                playedCardsDiv.appendChild(cardDiv);

                // scale up slightly in center
                requestAnimationFrame(() => {
                    cardDiv.style.transform = 'translate(-50%, -50%) scale(1)';
                    cardDiv.style.boxShadow = '0 0 20px gold, 0 0 30px rgba(255,215,0,0.5)';
                });

                // move to winner's avatar smoothly after 0.8s
                setTimeout(() => {
                    const winnerEl = document.querySelector(`.person[data-username="${winnerPlayer}"]`);
                    if (!winnerEl) return;

                    const winnerRect = winnerEl.getBoundingClientRect();
                    const parentRect = playedCardsDiv.getBoundingClientRect();
                    const targetX = winnerRect.left - parentRect.left + winnerRect.width / 2 - 40; // half card width
                    const targetY = winnerRect.top - parentRect.top + winnerRect.height / 2 - 55; // half card height

                    cardDiv.style.left = `${targetX}px`;
                    cardDiv.style.top = `${targetY}px`;
                    cardDiv.style.transform = 'scale(0.6)';
                    cardDiv.style.boxShadow = '0 0 10px gold, 0 0 20px rgba(255,215,0,0.3)';
                }, 800);

                // cleanup
                setTimeout(() => {
                    cardDiv.remove();
                    currentTurnPlayer = winnerPlayer;
                    updateTurnUI(winnerPlayer);
                }, 1800);
            }, 400);
        }
        // clear round animation end

        // clear updateDeckPileState
        function updateDeckPileState(currentPlayer) {
            const deckPile = document.getElementById('deck-pile');
            if (currentPlayer === username) {
                deckPile.style.cursor = 'pointer';
                deckPile.style.opacity = '1';
                deckPile.onclick = () => {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: 'get_extra_card_from_deck' }));
                    }
                };
                // for android
                deckPile.touchstart = () => {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: 'get_extra_card_from_deck' }));
                    }
                };

            } else {
                deckPile.style.cursor = 'not-allowed';
                deckPile.style.opacity = '0.5';
                deckPile.onclick = null; // disable click
            }
        }

        // newly drawn card animation start
        function animateDrawnCard(card) {
            const deckPile = document.getElementById('deck-pile');
            const cardDiv = document.createElement('div');
            cardDiv.classList.add('dealing-card');
            cardDiv.style.left = '0px';
            cardDiv.style.top = '0px';
            cardDiv.style.setProperty('--target-transform', `translate(0px, -10px) scale(1)`);
            deckPile.appendChild(cardDiv);

            setTimeout(() => cardDiv.remove(), 600);
        }
        // newly drawn card animation end


        // red day animation start
        function triggerRedDay(winnerUsername, tableCards, cardGiven, smasher) {
            if (!winnerUsername) return;

            const winnerEl = document.querySelector(`.person[data-username="${winnerUsername}"]`);
            const playedCardsDiv = document.getElementById("played-cards");

            // Highlight winner with pulse + shake table
            if (winnerEl) {
                winnerEl.classList.add("highlight");
                const table = document.getElementById("table");
                table.classList.add("shake-table");
                setTimeout(() => {
                    winnerEl.classList.remove("highlight");
                    table.classList.remove("shake-table");
                }, 2000);
            }

            // Floating "Red Day" text
            const text = document.createElement("div");
            text.classList.add("red-day-text");
            text.textContent = `Red Day! ${winnerUsername} has been SMASHED by ${smasher}! 🔥`;
            document.body.appendChild(text);
            setTimeout(() => text.remove(), 4000);

            // Step 1: Smash animation for card_given
            const smashCard = document.createElement("div");
            smashCard.classList.add("card", "smash-card");
            smashCard.textContent = cardGiven;
            playedCardsDiv.appendChild(smashCard);

            smashCard.style.transform = "scale(3) rotate(25deg)";
            smashCard.style.opacity = "0.9";
            setTimeout(() => {
                smashCard.style.transform = "scale(1) rotate(0)";
                smashCard.style.opacity = "1";
            }, 300);

            // Step 2: Other table cards sucked into the smash card
            setTimeout(() => {
                const allCards = Array.from(playedCardsDiv.querySelectorAll(".card"));
                allCards.forEach((c, idx) => {
                    if (c !== smashCard) {
                        c.style.transition = "all 0.7s ease-in";
                        c.style.transform = "translate(0,0) scale(0.2)";
                        c.style.opacity = "0";
                        setTimeout(() => c.remove(), 800);
                    }
                });
            }, 700);

            // Step 3: Smash card flies to winner
            setTimeout(() => {
                const winnerRect = winnerEl.getBoundingClientRect();
                const parentRect = playedCardsDiv.getBoundingClientRect();

                const targetX = winnerRect.left - parentRect.left + winnerRect.width / 2 - 40;
                const targetY = winnerRect.top - parentRect.top + winnerRect.height / 2 - 55;

                smashCard.style.transition = "all 1s ease-in-out";
                smashCard.style.left = `${targetX}px`;
                smashCard.style.top = `${targetY}px`;
                smashCard.style.transform = "scale(0.6)";
                smashCard.style.opacity = "0.8";

                setTimeout(() => smashCard.remove(), 1000);
            }, 1500);
        }


        // red day animation end


        // gamecompletedplayer feature start
        function handleCompletedGame(data, players_completed_now) {
            const completedPlayers = data.players_completed;
            const winner = players_completed_now.find(player => player === username);
            if (winner) {
                const rank = completedPlayers.indexOf(winner) + 1;
                // 🎉 Show winner popup
                showWinnerPopup(winner, rank);
            }

            // 🂡 If YOU are the winner → hide your cardlist
            if (winner === username) {
                hidePlayerCardlist();
            }

        }

        function showWinnerPopup(winner, rank) {
            const winDiv = document.createElement("div");
            winDiv.textContent = `${winner} finished 🎉 Rank #${rank}`;
            Object.assign(winDiv.style, {
                position: "fixed",
                top: "20%",
                left: "50%",
                transform: "translateX(-50%)",
                padding: "15px 25px",
                background: "gold",
                border: "3px solid black",
                fontWeight: "bold",
                fontSize: "1.3rem",
                borderRadius: "10px",
                zIndex: "2000"
            });
            document.body.appendChild(winDiv);
            setTimeout(() => winDiv.remove(), 3000);
        }

        function hidePlayerCardlist() {
            const cardlistDiv = document.querySelector(".cardlist");
            if (cardlistDiv) {
                cardlistDiv.innerHTML = "";
                cardlistDiv.style.display = "none";
            }
          
        }

        // function removePlayerBubble(username) {
        //     const personDiv = document.querySelector(`.person[data-username="${username}"]`);
        //     if (personDiv) {
        //         personDiv.classList.add("fade-out");
        //         setTimeout(() => personDiv.remove(), 500); // wait for animation
        //     }
        // }

       function updateCompletedPlayers(completedPlayers) {
            let completedDiv = document.getElementById("completed-players");
            if (!completedDiv) {
                completedDiv = document.createElement("div");
                completedDiv.id = "completed-players";
                Object.assign(completedDiv.style, {
                    marginTop: "10px",
                    padding: "10px",
                    border: "2px solid black",
                    background: "#f8f8f8"
                });
                // Insert at top of body
                document.body.insertBefore(completedDiv, document.body.firstChild);
            }

            completedDiv.innerHTML = "<h3>🏆 Completed Players: " + completedPlayers.length + "</h3>";
            completedPlayers.forEach((p, idx) => {
                const span = document.createElement("div");
                span.textContent = `#${idx + 1} ${p}`;
                span.style.fontWeight = p === username ? "bold" : "normal";
                completedDiv.appendChild(span);
            });
        }


        // popup for card_problem start
       

        function showCardProblemPopup(cardsByPlayer) {
            const modal = document.getElementById("cardProblemModal");
            const cardsContainer = document.getElementById("cardsContainer");
            const otherPlayerCardsDiv = document.getElementById("otherPlayerCards");
            const continueBtn = document.getElementById("continueBtn");
            const seeCardsBtn = document.getElementById("seeCardsBtn");
            const messagePara = document.getElementById("cardProblemMessage");

            // Reset
            cardsContainer.innerHTML = "";
            otherPlayerCardsDiv.style.display = "none";
            continueBtn.disabled = true;
            continueBtn.textContent = "Continue";
            continueBtn.style.background = "#9ca3af"; // gray
            // make the button non clickable
            continueBtn.style.cursor = "not-allowed";
            seeCardsBtn.textContent = "See Opponent Cards";
            seeCardsBtn.disabled = false;

            messagePara.textContent = "Card problem detected! Click below to reveal opponent cards.";

            // Heading
            const heading = document.createElement("h4");
            heading.textContent = "Opponent Cards:";
            heading.style.marginBottom = "12px";
            cardsContainer.appendChild(heading);

            // Loop opponents
            Object.keys(cardsByPlayer).forEach(player => {
                if (player === username) return; // skip self

                const playerDiv = document.createElement("div");
                playerDiv.style.marginBottom = "16px";

                const header = document.createElement("b");
                header.textContent = player;
                playerDiv.appendChild(header);

                const cardRow = document.createElement("div");
                cardRow.style.display = "flex";
                cardRow.style.flexDirection = "row";
                cardRow.style.marginTop = "6px";

                const cards = Array.isArray(cardsByPlayer[player]) ? cardsByPlayer[player] : [];

                cards.forEach((card, idx) => {
                    const cardDiv = document.createElement("div");
                    cardDiv.classList.add("card");
                    cardDiv.style.border = "2px solid red";
                    cardDiv.style.marginLeft = idx === 0 ? "0" : "-28px";

                    let symbol = "";
                    if (card.startsWith("D")) symbol = "♦️";
                    else if (card.startsWith("F")) symbol = "♣️";
                    else if (card.startsWith("S")) symbol = "♠️";
                    else if (card.startsWith("H")) symbol = "♥️";

                    const cardValue = card.substring(1);

                    const suitSpan = document.createElement("span");
                    suitSpan.textContent = symbol;
                    suitSpan.style.fontSize = "2rem";
                    suitSpan.style.display = "block";
                    suitSpan.style.textAlign = "center";

                    const valueSpan = document.createElement("span");
                    valueSpan.textContent = cardValue;
                    valueSpan.style.fontSize = "1.2rem";
                    valueSpan.style.display = "block";
                    valueSpan.style.textAlign = "center";

                    cardDiv.appendChild(suitSpan);
                    cardDiv.appendChild(valueSpan);

                    cardRow.appendChild(cardDiv);
                });

                playerDiv.appendChild(cardRow);
                cardsContainer.appendChild(playerDiv);
            });

            // Show modal
            modal.style.display = "flex";

            // Toggle see/hide cards
            seeCardsBtn.onclick = () => {
                const isHidden = otherPlayerCardsDiv.style.display === "none";
                if (isHidden) {
                    otherPlayerCardsDiv.style.display = "block";
                    seeCardsBtn.textContent = "Hide Opponent Cards";
                    continueBtn.disabled = false;
                    // seeCardsBtn.disabled = true; // disable after seeing
                    // notify server
                    // change the button to normal color green
                    continueBtn.style.background = "#4caf50"; // green
                     // make the button clickable
                    continueBtn.style.cursor = "pointer";
                    socket.send(JSON.stringify({ type: "saw_the_card" }));
                }
                else{
                    otherPlayerCardsDiv.style.display = "none";
                    continueBtn.disabled = true;
                    continueBtn.style.background = "#9ca3af"; // gray
                    // make the button non clickable
                    continueBtn.style.cursor = "not-allowed";

                }
            };

            // Continue button
            continueBtn.onclick = () => {
                modal.style.display = "none";
            };
        }

        //popup for card_problem end


      function shuffleAnimation(start = true) {
        const cardsStage = document.getElementById('cards-stage');

        if (start && shuffleAnimation_flag) {
            console.log("stat value", start, "in start",'shuffleAnimation_flag',shuffleAnimation_flag);

            // Show stage
            cardsStage.style.display = 'block';

            // // Start animation for all cards
            // const cards = document.querySelectorAll('#cards-stage .cardanimation');
            // cards.forEach(card => {
            // card.style.animation = `cardFlow var(--cycle) cubic-bezier(.2,.9,.2,1) infinite`;
            // card.style.opacity = 1;
            // });

            shuffleAnimation_flag = false;
        } else {
            console.log("stat value", start, "in !start",'shuffleAnimation_flag',shuffleAnimation_flag);

            const cards = document.querySelectorAll('#cards-stage .cardanimation');
            // cards.forEach(card => {
            //     card.style.animation = ''; // Stop animation
            //     card.style.opacity = 0;    // Hide them
            // });

            // Hide and clean up
            cardsStage.style.display = 'none';
        }
        }

        // Optional: stop animation when page reloads
        // window.addEventListener('beforeunload', () => {
        // shuffleAnimation(false);
        // });


        // card shuffle animation end


        function card_played_table_update(data){
            const player_color_dict = data.player_color_dict || {};
            const playedCardsDiv = document.getElementById('played-cards');
            playedCardsDiv.innerHTML = '';

            const current_round = data.current_round;

            current_round.played_cards.forEach(entry => {
                const playerName = Object.keys(entry)[0];
                const card = entry[playerName];

                const cardDiv = document.createElement('div');
                cardDiv.classList.add('card');
                cardDiv.style.border = `3px solid ${player_color_dict[playerName] || 'gray'}`;
                cardDiv.style.width = '80px';
                cardDiv.style.height = '120px';
                cardDiv.style.marginLeft = playedCardsDiv.children.length === 0 ? '0' : '-32px';
                cardDiv.style.position = 'relative';
                cardDiv.style.background = '#fff';
                cardDiv.style.borderRadius = '12px';
                cardDiv.style.display = 'inline-flex';
                cardDiv.style.flexDirection = 'column';
                cardDiv.style.justifyContent = 'center';
                cardDiv.style.alignItems = 'center';
                cardDiv.style.fontWeight = 'bold';
                cardDiv.style.fontSize = '1rem';
                cardDiv.style.zIndex = 100;

                let symbol = "";
                if (card.startsWith("D")) symbol = "♦️";
                else if (card.startsWith("F")) symbol = "♣️";
                else if (card.startsWith("S")) symbol = "♠️";
                else if (card.startsWith("H")) symbol = "♥️";

                const valueSpan = document.createElement('span');
                valueSpan.textContent = card.substring(1);
                valueSpan.style.fontSize = '1.2rem';
                valueSpan.style.marginBottom = '5px';

                const symbolSpan = document.createElement('span');
                symbolSpan.textContent = symbol;
                symbolSpan.style.fontSize = '2rem';

                cardDiv.appendChild(symbolSpan);
                cardDiv.appendChild(valueSpan);

                playedCardsDiv.appendChild(cardDiv);

                if (playerName === username) {
                    lastCards = lastCards.filter(c => c !== card);
                }
            });

            currentTurnPlayer = data.next_player;
            console.log("next player", data.next_player);
            updateTurnUI(data.next_player);
        }        



        // error message start
        function showMessage(message, type = "error", duration = 2500) {
            const bar = document.getElementById("error-message-bar");
            bar.textContent = message;

            // Reset classes
            bar.className = "message-bar " + type;

            // Show animation
            requestAnimationFrame(() => {
                bar.classList.add("show");
            });

            // Auto hide
            setTimeout(() => {
                bar.classList.remove("show");
            }, duration);
        }

        // error message end

        // gamecompletedplayer feature end
        function initWebSocket() {
            if (!roomId || !username || !password) window.location.href = "{% url 'account:login' %}";
            const protocol = window.location.protocol === "https:" ? "wss" : "ws";
            const token = getJWTToken();
            socket = new WebSocket(`${protocol}://${window.location.host}/ws/Sokkatte/${roomId}/?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&token=${token}`);

            socket.onmessage = event => {
                const data = JSON.parse(event.data);
                if (data.type === "players_update" && data.connected_dict) {
                    console.log('Player update received by the client');

                    const players = Object.entries(data.connected_dict).map(([username, color]) => ({ username, color }));
                    drawTable(players);
                    
                    shuffleAnimation(true); // start shuffling animation
                }
                if (data.type === "start_card_distribution") {
                    // start animation
                    const players = document.querySelectorAll(".person");
                    if (players.length > 0) {
                        shuffleAnimation(false); // start shuffling animation

                        startDealingAnimation(players);
                    }
                    socket.send(JSON.stringify({ type: "get_my_cards_req" }));
                }
                if (data.type === "cards_distributed") {
                    // stop animation
                    if (animationRunning) {
                        // store until animation finishes
                        pendingCardsData = data;
                    } else {
                        // no animation running, show immediately
                        showCards(data);

                        // 🃏 create deck pile after distribution
                        const players = Array.from(document.querySelectorAll(".person"));
                        const remaining = 52 - data.player_cards.length * players.length;
                        createDeckPile(remaining);
                    }

                }

                if (data.type === "starting_player") {
                    currentTurnPlayer = data.starting_player;
                    updateTurnUI(data.starting_player);
                    shuffleAnimation(false)
                }
                if (data.type === "card_played") {
                    card_played_table_update(data)
                }
                if (data.type == "clear_round") {
                    console.log("winner", data.next_player);
                    updateTurnUI(data.next_player);
                    document.getElementById('played-cards').innerHTML = "";
                    animateRoundWinner(data.next_player, data.card, data.player_color_dict || {});


                }
                if (data.type === "extra_card") {
                    const newlyDrawnCards = data.new_cards; // cards just drawn
                    lastCards = data.full_cards; // full hand
                    lastBorderColor = sessionStorage.getItem(`player_color_${username}`) || "gray";

                    renderCards(lastCards, lastBorderColor, currentSuitFilter, currentTurnPlayer === username, newlyDrawnCards);
                }

                if (data.type === "red_day_triggered") {
                    const winner = data.to_winner;
                    const smasher = data.from_player
                    const tableCards = data.current_round_card_list || [];
                    const cardGiven = data.card_given;   // the arrogance smash card

                    triggerRedDay(winner, tableCards, cardGiven, smasher);
                    console.log('winner', winner);
                    console.log('username', username);
                    console.log("next player", data.next_player);
                    

                    if (username === winner) {
                        // Add both tableCards + cardGiven to my hand
                        console.log('tableCards', tableCards, 'cardGiven', cardGiven, 'winner', winner);

                        lastCards = [...lastCards, ...tableCards, cardGiven];
                        renderCards(lastCards, lastBorderColor, currentSuitFilter, currentTurnPlayer === username);
                    }
                    else if (username === smasher) {
                        // Remove cardGiven by my hand
                        lastCards = lastCards.filter(card => card !== cardGiven);
                        renderCards(lastCards, lastBorderColor, currentSuitFilter, currentTurnPlayer === username);
                    }
                    
                    updateTurnUI(data.next_player);

                }
               if (data.type == "completed_game") {
                    console.log("game completed data", data);
                    if (data.connected_dict && data.players_still_in) {
                        // Build a new dict with only active players and their colors
                        const new_connected_dict = {};
                        data.players_still_in.forEach(username => {
                            new_connected_dict[username] = data.connected_dict[username] || "gray";
                        });

                        // Create array of { username, color } objects for drawTable
                        const players = data.players_still_in.map(username => ({
                            username,
                            color: new_connected_dict[username]
                        }));

                        drawTable(players);
                    }
                    handleCompletedGame(data, data.players_completed_now);
                    // 🏆 Update completed players list on top
                    updateCompletedPlayers(data.players_completed_now);
                }

                if (data.type === "game_over") {
                    const looser = data.looser;
                    console.log("came to the game_over message");
                    
                    const completedList = encodeURIComponent(JSON.stringify(data.game_completed_player_list));
                    // Redirect with query params
                    console.log("Game over. Redirecting to winner page...",data.looser, data.game_completed_player_list);
                    window.location.href = `{% url 'winner_page' %}?looser=${encodeURIComponent(looser)}&completed=${completedList}`;                
                }

                if (data.type === "card_problem") {
                    console.log("Card problem:", data.other_player_card_list,data.players);
                    console.log("username",username)
                    // Build object only for opponents
                    const cardsByPlayer = {};
                    data.players.forEach(player => {
                        if (player !== username) {
                                cardsByPlayer[player] = data.other_player_card_list[player];
                            }
                    });

                    showCardProblemPopup(cardsByPlayer, data.message);
                    

                }
                
                if (data.type==="watching_card_again"){
                    console.log("Server message:", data.message);
                }

                if (data.type==="saw_card_ack"){
                    console.log("Saw card ack received");
                    // update the cardlist of the user
                    const userCardList = data.extra_cards;
                    updated_player_cards = data.updated_player_cards || [];
                    lastCards = updated_player_cards;
                    connected_dict = data.connected_dict || {};
                    lastBorderColor = sessionStorage.getItem(`player_color_${username}`) || "gray";
                    console.log("Your updated card list:", userCardList);
                    renderCards(lastCards, lastBorderColor, currentSuitFilter, currentTurnPlayer === username);
                    console.log("Your updated card list after acknowledging:", userCardList);
                }

                if (data.type=="current_round_table_update"){
                    console.log("current_round_table_update recieved by client");
                    shuffleAnimation(false); // start shuffling animation
                    card_played_table_update(data)
                    console.log("current_round_table_update recieved by client completed");
                    


                }

                if (data.type === "error") {    
                    showMessage(data.message, "error");
               
    
                }
            };

            // for retry logic
            socket.onopen = () => {
                console.log("WebSocket connected!");
                retries = 0; // reset retries on success
            };
            socket.onerror = err => {
                console.error("WebSocket error:", err);
                socket.close(); // triggers retry
            };

            socket.onclose = () => {
                if (retries > 0) {
                    console.warn(`WebSocket closed. Retrying in ${delay / 1000}s... (${retries} left)`);
                    setTimeout(() => initWebSocket(retries - 1, delay), delay);
                } else {
                    console.error("Max retries reached. Could not connect WebSocket.");
                }
            };
        }

        document.addEventListener('DOMContentLoaded', () => {
            if (document.cookie.includes("jwt")) checkAuthAndInit();
            document.querySelectorAll('.suit-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    currentSuitFilter = btn.getAttribute('data-suit');
                    renderCards(lastCards, lastBorderColor, currentSuitFilter, currentTurnPlayer === username);
                });
            });
        });