#Hangman API


##Game Description:
Hangman is a simple game where you guess a word a letter at a time. With each
incorrect guess a part of a stick figure body is drawn. The parts are the head,
torso, left arm, right arm, left leg, and right leg giving the user 5 incorrect
guesses until the game is over.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, min, max, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Min must be less than
    max. Also adds a task to a task queue to update the average moves remaining
    for active games.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **get_user_games**
     - Path: 'game/user/{user_name}'
     - Method: GET
     - Parameters: user_name
     - Returns: GameForms with a user's games
     - Description: Returns all of the games a user currently is playing

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.

 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: POST
    - Parameters: cancel Boolean
    - Returns: Gameform of canceled game
    - Description: Accepts a boolean to cancel a game a user is currently playing. The game will be scored as a loss.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).

 - **get_high_scores**
    - Path: 'highscores'
    - Method: GET
    - Parameters: None
    - Returns: List of ordered scores
    - Description: Returns a list of users with their highest score in descending order.

 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms.
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get_user_rankings**
    - Path: 'rank/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: Rank of user
    - Description: If user is ranked will return their rank as a number(string), if not will return 'User not ranked'

 - **get_average_attempts**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.

 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.

##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **NewGameForm**
    - Used to create a new game (user_name, min, max, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **CancelGameForm**
    - Used to cancel game.
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).
 - **StringMessage**
    - General purpose String container.
 - **GameForms**
    - Multiple GameForm container.
 - **ScoreForms**
    - Multiple ScoreForm container.