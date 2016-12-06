# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from google.appengine.api import urlfetch
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm, ScoreForms, CancelGameForm, GameForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
CANCEL_GAME_REQUEST = endpoints.ResourceContainer(
    CancelGameForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(
    user_name=messages.StringField(1),
    email=messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        url = 'http://www.setgetgo.com/randomword/get.php'
        try:
            result = urlfetch.fetch(url)
            if result.status_code == 200:
                target = result.content
                target_list = {}
                for i in target:
                    target_list[i] = False
                game = Game.new_game(user.key, request.attempts,
                                     target, target_list)
        except urlfetch.Error:
            logging.exception('Caught exception fetching url')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Hangman!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='game/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns games user is a part of"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        games = Game.query(Game.user == user.key).fetch()
        items = [game.to_form('string') for game in games]
        return GameForms(games=items)

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        found = False
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over or game.attempts_remaining == 0:
            return game.to_form('Game already over!')

        d = game.target_list
        for i in d:
            if request.guess == i:
                d[i] = True
                msg = 'Good guess!'
                found = True
        if all(d[x] is True for x in d):
            game.end_game(True)
            msg = 'You Win!'

        if not found:
            game.attempts_remaining -= 1
            msg = 'Sorry guess again'

        if game.attempts_remaining < 1:
            game.end_game(False)
            return game.to_form('Game over!')
        else:
            game.target_list = d
            game.put()
            return game.to_form(msg)

    @endpoints.method(request_message=CANCEL_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='POST')
    def cancel_game(self, request):
        """Cancels game, user loses by default"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if request.cancel:
                game.end_game(False)
                game.put()
                return game.to_form('Game was canceled.')
        return game.to_form('Game was not canceled.')

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(response_message=ScoreForms,
                      path='highscores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Returns scores in descending order"""
        return ScoreForms(
            items=[score.to_form() for score in Score.query().filter(
                Score.won == True).order(Score.guesses)])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='rank/{user_name}',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Returns ranking of a user"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        rank = 1
        query = Score.query().filter(Score.won == True).order(Score.guesses).fetch()
        for score in query:
            if user.key == score.user:
                msg = str(rank)
                return StringMessage(message=msg)
            else:
                rank += 1
        msg = 'User not ranked'
        return StringMessage(message=msg)


    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(
            message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over is False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                        for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([HangmanApi])
