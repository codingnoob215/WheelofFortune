from flask import Flask, render_template, request, session, url_for, jsonify, redirect
import random

app = Flask(__name__) 
app.secret_key = 'csc381fall'

@app.route('/')
def home(): 
  return redirect(url_for('board')

@app.route('/wheel')
def wheel(): 
  return render_template('wheel.html')

@app.route('/spin', methods=['POST']) 
def spin(): 
  wheel_values = [100,200,300, 400, 'BANKRUPT', 400,500, 'MISS A TURN', 600, 700, 800, 900, 1000]
  result = random.choice(wheel_values)
  session['last_spin'] = result
  return render_template('wheel.html', result=result)

@app.route('/spin_result')
def spin_result():
  value = request.args.get('value')
  session['last_spin'] = value
  if value and value isdigit(): 
    session['money'] += int(value)
elif value == 'BANKRUPT': 
  session['money'] = 0
# miss a turn skips
return ('', 204)

@app.route('/guess', methods=['POST'])
def guess(): 
  letter = request.form['letter'].upper()
  if letter and letter.isalpha(): 
    if letter not in session['guessed']:
     session['guessed'].append(letter)
      if letter in session['puzzle']:
      session['money'] += 500
  return redirect(url_for('board'))
  
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
  category, phrase = get_random_puzzle()
  session['puzzle'] = phrase.upper()
  session['category'] = category
  session['guessed'] = []
  session['round'] += 1
  return redirect(url_for('board'))

#Choose random puzzle when game starts 
@app.route('/board') 
def board(): 
  if 'puzzle' not in session: 
    category, phrase = get_random_puzzle()
    session['puzzle'] = phrase.upper()
    session['category'] = category
    session['guessed'] = []
    session['money'] = 0
    session[round] = 1
    session['player'] = "PLAYER 1"

puzzle = session['puzzle']
guessed = session['guessed']

#Shows letters that have been guessed correctly and produces the current visible puzzle
revealed = ''.join([c if c = ' ' or c.upper() in guessed else '_' for c in puzzle])
return render_template('board.html', category=session['category'],money=session['money'],round=session['round'],player=session['player'])

if __name__ = '__main__': 
app.run(debug=True)
