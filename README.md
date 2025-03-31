
<!-- ROADMAP -->
## Features / TODO

- [x] Multiplayer minesweeper game logic
	- [x] Core functionalities (flood cell opening, mines clicked counting etc.)
 	- [x] Turn changing
  	- [x] Winning logic
  	- [x] Bomb mechanic
- [ ] Lobby
	- [x] Lobby creation
	 	- [ ] Custom game rules
	- [x] Owner role - admins lobby (starts the game etc.)
	- [x] Players can rejoin started game 
		- [ ] Timer for players to rejoin
	- [x] Automatic removal of empty lobbies
	- [x] Chat and lobby messages (player left etc.)
	- [x] Ranked Game
		- [x] ELO calculation
- [x] Account functionality
	- [x] ELO assigned to account
	- [ ] Account frontend
- [x] Guest functionality (no registration)
- [x] Lobby list
	- [x] Display players inside lobby and their ELOs
	- [x] Join lobby

 Not an exhaustive list and more to come


### Installation
1. Clone the repo
   ```sh
   git clone https://github.com/remles1/multisweeper.git
   ```
2. cd
   ```sh
	cd multisweeper/
   ```
4. Make migrations
   ```sh
   python manage.py makemigrations
   ```
5. Migrate
   ```sh
	python manage.py migrate
   ```
6. Run dev server
   ```sh
	python manage.py runserver
   ```
Database is required.
Default credentials are inside manage.py file

<p align="right">(<a href="#readme-top">back to top</a>)</p>
