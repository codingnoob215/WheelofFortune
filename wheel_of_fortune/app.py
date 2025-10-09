from flask import Flask, render_template, request, session, url_for, jsonify, redirect
import random

app = Flask(__name__) 

#Choose random puzzle when game starts 
@app.route('/board') 
def board(): 
  if 'puzzle' not in session: 
    session['puzzle'] = random.choice(PUZZLES)
    session['guessed'] = []

puzzle = session['puzzle']
guessed = session['guessed']

#Shows letters that have been guessed correctly and produces the current visible puzzle
revealed = ''.join([c if c = ' ' or c.upper() in guessed else '_' for c in puzzle])
return render_template('board.html', puzzle = revealed, guessed = guessed)
