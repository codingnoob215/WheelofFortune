from flask import Flask, render_template, request, session, url_for, jsonify, redirect
import random

app = Flask(__name__) 
app.secret_key = 'csc381fall'

@app.route('/')
def home(): 
  return redirect(url_for('wheel')

@app.route('/wheel')
def wheel(): 
  return render_template('wheel.html')

@app.route('/spin', methods=['POST']) 
def spin(): 
  wheel_values = [100,200,300, 400, 'BANKRUPT', 400,500, 'MISS A TURN', 600, 700, 800, 900, 1000]
  result = random.choice(wheel_values)
  session['last_spin'] = result
  return jsonify({'result': result}) 

@app.route('/guess', methods=['POST'])
def guess(): letter = request.json.get('letter', '').upper()
  if not letter or len(letter) != 1 or not letter.isalpha(): 
    return jsonify({'error': 'Invalid guess'})

guessed = session.get('guessed', []) 
if letter not in guessed: 
  guessed.append(letter) 
  session['guessed'] = guessed

puzzle = session['puzzle']
revealed = ''.join([c if c == " " or c.upper() in guessed else '_' for c in puzzle])
correct = letter in puzzle 
return jsonify({'correct': correct, 'revealed': revealed, 'guessed': guessed}) 

@app.route('/solve', methods=['POST']) 
def solve(): 
  guess = request.json.get('guess', '').upper()
  if guess == session.get('puzzle'): 
    session['bank'] = session.get('bank', 0) + 1000
    return jsonify({'correct':True, 'bank': session['bank']})
  else: 
    return jsonify({'correct':False})

@app.route('/new_puzzle')
def new_puzzle(): 
  session.pop('puzzle', None)
  session.pop('category', None)
  session.pop('guessed', None)
  return redirect(url_for('board'))

#Choose random puzzle when game starts 
@app.route('/board') 
def board(): 
  if 'puzzle' not in session: 
    chosen = random.choice(PUZZLES)
    session['puzzle'] = chosen['puzzle']
    session['category'] = chosen['category']
    session['guessed'] = []

puzzle = session['puzzle']
category = session['category']
guessed = session['guessed']

#Shows letters that have been guessed correctly and produces the current visible puzzle
revealed = ''.join([c if c = ' ' or c.upper() in guessed else '_' for c in puzzle])
return render_template('board.html', puzzle = revealed, guessed = guessed)

if __name__ = '__main__': 
app.run(debug=True)
