"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask
from flask import render_template
from flask import request
import json
import logging
import urllib2
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.
wrong = 0
wordtoguess = ""
progress = ""
gameswon = 0
gameslost = 0
scoreDict = {}

@app.route('/')
def hello():
    """Returns the main hangman page."""
    return render_template('index.html')

@app.route('/new_game', methods = ['POST'])
def new_game():
        """this should generate a word"""
        global wordtoguess
        RequestURL = urllib2.Request('http://randomword.setgetgo.com/get.php')
        ReadURL = urllib2.urlopen(RequestURL)
        TheAnswer = (ReadURL.read()).upper()

        wordtoguess = TheAnswer

        global wrong
        wrong = 0

        word = {}
        word['word_length'] = len(wordtoguess)

        global progress
        progress = ""
        for i in range(0,len(wordtoguess)):
            progress += '_'

        return json.dumps(word)

@app.route('/check_letter', methods = ['POST'])
def check_letter():
    """Check whether the letter client guessed is valid"""
    global gameswon
    global gameslost
    global wrong
    global progress

    getJson = request.get_json(silent = True)
    guessed_letter = getJson['guess']
    logging.info(guessed_letter)

    progresslist = list(progress) #Seperate into array so can modify

    guessDict = {}
    if guessed_letter in wordtoguess:
        for i in range(0,len(wordtoguess)):
            if guessed_letter == wordtoguess[i]:
                progresslist[i] = guessed_letter
    else:
        wrong += 1

    progress = "".join(progresslist) #For joining back the list

    #Bool for win state
    win = True

    """If there is any _ in the word, win == False"""
    for i in range(0,len(progress)):
        if progress[i] == '_':
            win = False

    guessDict["word_state"] = progress
    guessDict["bad_guesses"] = wrong


    if win == True:
        #WIN THE GAME
        guessDict['game_state'] = "WIN"
        gameswon += 1
    else:
        if wrong >= 8:
            # LOSE THE GAME
            guessDict['game_state'] = "LOSE"
            guessDict['answer'] = wordtoguess
            gameslost += 1
        else:
            guessDict['game_state'] = "ONGOING"

    return json.dumps(guessDict)

@app.route('/score')
def score():
    global gameswon
    global gameslost
    global scoreDict
    #scoreDict = {}
    scoreDict['games_won'] = gameswon
    scoreDict['games_lost'] = gameslost

    return json.dumps(scoreDict)

@app.route('/score', methods = ['DELETE'])
def deleteScore():
    global gameswon
    global gameslost
    global scoreDict
    gameswon = 0
    gameslost = 0
    scoreDict['games_won'] = gameswon
    scoreDict['games_lost'] = gameslost

    return json.dumps(scoreDict)

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
