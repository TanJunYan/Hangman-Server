"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask
from flask import render_template
from flask import request
from flask import session
from google.appengine.ext import ndb
import json
import logging
import urllib2
import base64
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.
wrong = 0
wordtoguess = ""
progress = ""
gameswon = 0
gameslost = 0
scoreDict = {}
signed_in = False
sign_in_name = ""

app.secret_key = "Touch My Bodeh"
#Create Entity
class Player(ndb.Model):
    Name            = ndb.StringProperty()
    PassWord        = ndb.StringProperty()
    Admin           = ndb.BooleanProperty()
    Games_Created   = ndb.IntegerProperty()
    Games_Played    = ndb.IntegerProperty()
    Games_Won       = ndb.IntegerProperty()
    Games_Lost      = ndb.IntegerProperty()
    Join_ID         = ndb.IntegerProperty()
    Wrong_Guesses   = ndb.IntegerProperty()
    Word_State      = ndb.StringProperty()

class GAMES(ndb.Model):
    GAMEID      = ndb.IntegerProperty()
    THE_WORD    = ndb.StringProperty()
    WordLength  = ndb.IntegerProperty()
    HINT        = ndb.StringProperty()
    Won         = ndb.IntegerProperty()
    Lost        = ndb.IntegerProperty()

@app.route('/')
def main():
    #Returns the main hangman page.
    games = GAMES.query()
    game_list = []

    if games.count():                           #IF there are games in the database
        game_list = games.fetch(games.count())  #game_list = to the total games available

    gameStuff = []
    for i in game_list:
        gamePlay = {}
        gamePlay['hint'] = i.HINT
        gamePlay['word_length'] = i.WordLength
        gamePlay['game_id'] = i.GAMEID
        gameStuff.append(gamePlay)

    signed_in = False
    sign_in_name = "GuestThatBrokeIn"
    wow = Player.query()
    #app.logger.info(wow.fetch())
    if 'token' in session:
        logging.debug('signed in')
        signed_in = True
        sign_in_name = session['token']

    return render_template('main.html', signed_in = signed_in, sign_in_name = sign_in_name, game_list = gameStuff)

@app.route('/token', methods = ['GET', 'POST'])
def token():
    #global token
    name     = request.authorization.username #Get the name input
    password = request.authorization.password #Get the password input

    #If they enter Nothing
    if name == '' or password == '':
        app.logger.error('Username and Password does not take in blank spaces')
        return json.dumps({'error' : 'Bad request, malformed data'}), 400

    #Once sometime is typed into the username and password
    #Get - Sign in  ;  POST - Sign Up  ;  else - entered with another method somehow
    if request.method == 'GET':
        username = Player.query(Player.Name == name)

        if username.count() == 0:
            app.logger.error("You Don't Exist in our Database")
            return json.dumps({'error' : 'User not found'}), 404
        if username.get().PassWord != password:
            app.logger.error("YOU LIAR")
            return json.dumps({'error' : 'Wrong Password'}), 403

        session['token'] = name
        if username.get().Admin: # Check for admin priviledges and stores in session for future uses
            session['admin'] = True
        else:
            session['admin'] = False
        return json.dumps({'token' : name})

    elif request.method == 'POST':
        username = Player.query(Player.Name == name)
        if username.count() > 0:
            app.logger.error("Name already Taken")
            return json.dumps({'error' : 'Conflicting user id'}), 409
        if username.count() == 0:
            create = Player(
                        Name            = name,
                        PassWord        = password,
                        Admin           = False,
                        Games_Created   = 0,
                        Games_Played    = 0,
                        Games_Won       = 0,
                        Games_Lost      = 0,
                        Join_ID         = 0,
                        Wrong_Guesses   = 0,
                        Word_State      = ''
                            )
            create.put()
            session['token'] = name
            return json.dumps({'token' : name})
    else:
        app.logger.error('You shall not pass!')
        return json.dumps({'error' : 'Method not allowed'}), 405



@app.route('/games', methods = ['GET', 'POST', 'DELETE'])
def Games():
    if request.method == 'GET':
        app.logger.error('GET!')
        return json.dumps({'error' : 'Method not allowed'}), 405
    elif request.method == 'POST':
        JsonInput = request.data #Get the JSON for the word and hint data from the input
        JsonData = json.loads(JsonInput)
        #Store Game stuff into a temporary variable

        tempWord = JsonData["word"]
        tempWord = tempWord.upper()
        tempLength = len(tempWord)
        tempHint = JsonData["hint"]
        tempID = 1 #Default the game id to 1
        while True:
            IDquery = GAMES.query(GAMES.GAMEID == tempID)
            if IDquery.count() == 0: # If there is no other game ID occupying, break out of while loop
                break
            else:
                tempID += 1 #If there is other games with the same ID +1 to tempID and rerun the loop
        #Saves the game stuff into database
        Create = GAMES(GAMEID = tempID, THE_WORD = tempWord, WordLength = tempLength, HINT = tempHint, Won = 0, Lost = 0)
        Create.put()

        query = Player.query(Player.Name == session['token'])
        query.get().Games_Created += 1
        query.get().put()

        games = GAMES.query()
        game_list = []

        if games.count():                           #IF there are games in the database
            game_list = games.fetch(games.count())  #game_list = to the total games available

        gameStuff = []
        for i in game_list:
            gamePlay = {}
            gamePlay['hint'] = i.HINT
            gamePlay['word_length'] = i.WordLength
            gamePlay['game_id'] = i.GAMEID
            gameStuff.append(gamePlay)

        return json.dumps(gameStuff)
    elif request.method == 'DELETE':
        if session['admin']:
            getgame = GAMES.query()
            getgamelist = getgame.fetch(getgame.count())
            for i in getgamelist:
                i.key.delete()
        else:
            app.logger.error('You cannot delete this')
            return json.dumps({'error' : 'You do not have permission to perform this operation'}), 403
    else:
        app.logger.error('You shall not pass!')
        return json.dumps({'error' : 'Method not allowed'}), 405


@app.route('/games/<game_id>', methods = ['GET', 'DELETE'])
def GameWord(game_id):
    gamequery = GAMES.query(GAMES.GAMEID == int(game_id))

    if gamequery.count() == 0: # Check if game exists in the database
        app.logger.error('Game not found/is deleted')
        return json.dumps({'error' : 'Game not found'}), 404

    if request.method == 'GET':
        player = Player.query(Player.Name == session['token']) #Get stuff from the database regarding the current user token
        if player.get().Join_ID != int(game_id):       #If the game id the user possess does not have the same game id as the game he is joinging
            player.get().Join_ID = int(game_id)        #Set the current id to the room id so it won't pass in here
            player.get().Games_Played += 1
            app.logger.info(player.get().Games_Played)
            player.get().Wrong_Guesses = 0                     #To reset current wrong guesses from 2nd game onwards
            player.get().Word_State = ''                        #To reset current word state from 2nd game onwards
            for i in gamequery.get().THE_WORD:                  #Replace the words with blank spaces
                player.get().Word_State += '_'
                app.logger.info(player.get().Word_State)
            player.get().put()

        GameWord = {}
        GameWord["hint"] = gamequery.get().HINT
        GameWord["word_length"] = gamequery.get().WordLength
        GameWord["game_id"] = gamequery.get().GAMEID
        return render_template('game.html', game_property = GameWord)
    elif request.method == 'DELETE':
        if session['admin']:
            gamequery.get().key.delete()
            return json.dumps({"message", "Game was deleted"})
        else:
            return json.dumps({'error' : 'You do not have permission to perform this operation'}), 403
    else:
        app.logger.error('Method not allowed')
        return json.dumps({'error' : 'Method not allowed'}), 405


@app.route('/games/<game_id>/check_letter', methods = ['POST'])
def check_letter(game_id):
    """Check whether the letter client guessed is valid"""
    if not ('token' in session):
        app.logger.error("You shouldn't be here")
        return json.dumps({'error' : 'You do not have permission to perform this operation'}), 403

    ongoingquery = GAMES.query(GAMES.GAMEID == int(game_id))

    getJson = request.data
    Jsondata = json.loads(getJson)
    #Jsondata = request.get_json(silent = True)
    guessed_letter = Jsondata['guess']

    player = Player.query(Player.Name == session['token'])
    progress = player.get().Word_State
    wordtoguess = ongoingquery.get().THE_WORD
    wrong = player.get().Wrong_Guesses
    app.logger.error(player.get().Word_State)

    progresslist = list(progress) #Seperate into array so can modify

    app.logger.info("wordtoguess")
    if guessed_letter in wordtoguess:
        app.logger.info("wordtoguess")
        for i in range(0,len(wordtoguess)):
            if guessed_letter == wordtoguess[i]:
                progresslist[i] = guessed_letter
    else:
        wrong += 1

    progress = "".join(progresslist) #For joining back the list

    #Update database
    player.get().Word_State = progress
    player.get().Wrong_Guesses = wrong
    player.get().put()

    #status = Player.query(Player.Games_Won)
    #Bool for win state
    win = True

    guessDict = {}
    """If there is any _ in the word, win == False"""
    for i in range(0,len(progress)):
        if progress[i] == '_':
            win = False

    guessDict["word_state"] = progress
    guessDict["bad_guesses"] = wrong


    if win == True:
        #WIN THE GAME
        guessDict['game_state'] = "WIN"
        player.get().Games_Won += 1
        player.get().put()
        ongoingquery.get().Won += 1
        ongoingquery.get().put()
    else:
        if wrong >= 8:
            # LOSE THE GAME
            guessDict['game_state'] = "LOSE"
            guessDict['answer'] = wordtoguess
            player.get().Games_Lost += 1
            player.get().put()
            ongoingquery.get().Lost += 1
            ongoingquery.get().put()

        else:
            guessDict['game_state'] = "ONGOING"

    return json.dumps(guessDict)

@app.route('/admin', methods = ['GET'])
def admin():
    if not session['admin']:
        return json.dumps({'error' : 'You do not have permission to perform this operation'}), 403
    if request.method != 'GET':
        return json.dumps({'error' : 'Method not allowed'}), 405
    return render_template('admin.html')

@app.route('/admin/players', methods = ['GET'])
def CheckPlayers():
    if not session['admin']:
        return json.dumps({'error' : 'You do not have permission to perform this operation'}), 403
    if request.method != 'GET':
        return json.dumps({'error' : 'Method not allowed'}), 405


    PlayerSortby = request.args.get('sortby')
    PlayerOrder = request.args.get('order')
    Query = Player.query()
    if PlayerSortby == 'wins':
        Query = Query.order(Player.Games_Won)
    elif PlayerSortby == 'losses':
        Query = Query.order(Player.Games_Lost)
    elif PlayerSortby == 'alphabetical':
        Query = Query.order(Player.Name)
    else:
        app.logger.error('Bad request, malformed data')
        return json.dumps({'error' : 'Bad request, malformed data'}), 400

    player_list = []

    if Query.count():                           #IF there are games in the database
        player_list = Query.fetch(Query.count())  #game_list = to the total games available

    sortedStuff = []
    for i in player_list:
        playerdetails = {}
        playerdetails['name'] = i.Name
        playerdetails['games_created'] = i.Games_Created
        playerdetails['games_played'] = i.Games_Played
        playerdetails['games_won'] = i.Games_Won
        playerdetails['games_lost'] = i.Games_Lost
        sortedStuff.append(playerdetails)

    if PlayerOrder == 'asc':
        pass
    elif PlayerOrder == 'desc':
        sortedStuff.reverse()
    else:
        app.logger.error('Bad request, malformed data')
        return json.dumps({'error' : 'Bad request, malformed data'}), 400

    return json.dumps(sortedStuff)

@app.route('/admin/words', methods = ['GET'])
def CheckGames():
    if not session['admin']:
        return json.dumps({'error' : 'You do not have permission to perform this operation'}), 403
    if request.method != 'GET':
        return json.dumps({'error' : 'Method not allowed'}), 405

    WordSortby = request.args.get('sortby')
    WordOrder = request.args.get('order')
    Query = GAMES.query()
    if WordSortby == 'solved':
        Query = Query.order(GAMES.Won)
    elif WordSortby == 'length':
        Query = Query.order(GAMES.WordLength)
    elif WordSortby == 'alphabetical':
        Query = Query.order(GAMES.THE_WORD)
    else:
        app.logger.error('Bad request, malformed data')
        return json.dumps({'error' : 'Bad request, malformed data'}), 400

    game_list = []

    if Query.count():                           #IF there are games in the database
        game_list = Query.fetch(Query.count())  #game_list = to the total games available

    sortedStuff = []
    for i in game_list:
        gamedetails = {}
        gamedetails['word'] = i.THE_WORD
        gamedetails['wins'] = i.Won
        gamedetails['losses'] = i.Lost
        sortedStuff.append(gamedetails)

    if WordOrder == 'asc':
        pass
    elif WordOrder == 'desc':
        sortedStuff.reverse()
    else:
        app.logger.error('Bad request, malformed data')
        return json.dumps({'error' : 'Bad request, malformed data'}), 400

    return json.dumps(sortedStuff)

@app.route('/addadmin', methods = ['GET'])
def addadmin():
    create = Player(
                    Name = 'Pandoge',
                    PassWord = 'admin',
                    Admin           = True,
                    Games_Created   = 0,
                    Games_Played    = 0,
                    Games_Won       = 0,
                    Games_Lost      = 0,
                    Join_ID         = 0,
                    Wrong_Guesses   = 0,
                    Word_State      = ''
                    )
    create.put()
    return "Admin Created"

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
