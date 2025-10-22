from flask import Flask, flash, render_template, request, session, url_for, jsonify, redirect
import random
from puzzles import PUZZLES

app = Flask(__name__) 
app.secret_key = 'csc381fall'

def get_new_puzzle():
    category = random.choice(list(PUZZLES.keys()))
    puzzle = random.choice(PUZZLES[category])
    return category, puzzle.upper()

@app.route('/')
def home(): 
  return redirect(url_for('board'))

@app.route('/wheel')
def wheel(): 
  return render_template('wheel.html')

@app.route('/buy_vowel', methods=['POST'])
def buy_vowel():
    vowel = request.form['vowel'].upper()
    if vowel not in "AEIOU":
        flash("That's not a vowel!",'error')
        return redirect(url_for('board'))

    if session.get('money', 0) < 250:
        flash("Not enough money to buy a vowel!",'error')
        return redirect(url_for('board'))

    if vowel not in session['guessed']:
        session['guessed'].append(vowel)
        session['money'] -= 250

    return redirect(url_for('board'))

@app.route('/spin', methods=['GET','POST']) 
def spin(): 
  wheel_values = [100, 200, 300, 400, 'BANKRUPT', 400, 500, 'MISS A TURN', 600, 700, 800, 900, 1000]
  result = random.choice(wheel_values)
  session['last_spin'] = result

    
  if isinstance(result, int):
        session['money'] = session.get('money', 0) + result
        flash(f"You spun ${result}!",'info')
  elif result == 'BANKRUPT':
        session['money'] = 0
        flash("BANKRUPT! You lost all your money!",'info')
  elif result == 'MISS A TURN':
        flash("You missed your turn!",'info')
  return render_template('wheel.html', result=result)

@app.route('/spin_result')
def spin_result():
  value = request.args.get('value')
  if not value:
     return jsonify({'error': 'No spin value recieved'}), 400
  
  session['last_spin'] = value
  money = session.get('money', 0)

  if value and value.isdigit(): 
    session['money'] = money + int(value)
    flash(f"You spun ${value}!",'info')
  elif value == 'BANKRUPT':
    session['money'] = 0
    flash("BANKRUPT! You lost all your money!",'info')
  elif value == 'LOSE A TURN':
    flash("You lost your turn!",'info')
    session['message'] = "BANKRUPT! You lost all of your money!"
  elif value in  ('LOSE A TURN', 'MISS A TURN'):
    session['message'] = 'You lost your turn.'
  else: 
    flash("Invalid spin result.",'info')

    return ('', 204)
    session['message'] = 'Invalid spin result.'

  session.modified = True

  return jsonify({'result' : value, 'money' : session['money']})

@app.route('/guess', methods=['POST'])
def guess(): 
  letter = request.form['letter'].upper()
  if letter and letter.isalpha():
    if letter in "AEIOU":
       flash("No vowels allowed", 'error')
       return redirect(url_for('board'))
    if letter in "AEIOU":
       flash("No vowels allowed", 'error')
       return redirect(url_for('board'))
    if letter not in session['guessed']:
        session['guessed'].append(letter)
        session.modified = True

        if letter in session['puzzle']:
            session['money'] += 500
    print("Guessed so far:", session['guessed'])  
    print("Puzzle:", session['puzzle'])
  return redirect(url_for('board'))
  
@app.route('/solve', methods=['POST']) 
def solve(): 
  guess = request.form.get('guess', '').upper()
  if guess == session.get('puzzle'): 
    session['bank'] = session.get('bank', 0) + 1000
    flash("Great job! You solved the puzzle!", 'success')
    return redirect(url_for('new puzzle'))
    session['message'] = "Great job! You solved the puzzle!"
    return redirect(url_for('new_puzzle'))
  else: 
    flash("Sorry, that is incorrect.", 'info')
    return redirect(url_for('board'))

@app.route('/new_puzzle')
def new_puzzle(): 
  category, phrase = get_new_puzzle()
  session['puzzle'] = phrase.upper()
  session['category'] = category
  session['guessed'] = []
  session['money'] = 0
  session['round'] = session.get('round', 0)+1
  return redirect(url_for('board'))

#Choose random puzzle when game starts 
@app.route('/board') 
def board(): 
  if 'puzzle' not in session: 
    category, phrase = get_new_puzzle()
    session['puzzle'] = phrase.upper()
    session['category'] = category
    session['guessed'] = []
    session['money'] = 0
    session['round'] = 1
    session['player'] = "PLAYER 1"

  if 'guessed' not in session:
      session['guessed'] = []
  puzzle = session['puzzle']
  guessed = session['guessed']
#Shows letters that have been guessed correctly and produces the current visible puzzle
  revealed = ''.join([c if c == ' ' or c.upper() in guessed else '_' for c in puzzle])
  return render_template('board.html', category=session['category'],money=session['money'],round=session['round'],player=session['player'], revealed=revealed)

if __name__ == '__main__': 
 app.run(debug=True)
