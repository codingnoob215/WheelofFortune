from flask import Flask, flash, render_template, request, session, url_for, jsonify, redirect
import random
import bonus_puzzles
print("Loaded bonus_puzzles from:", bonus_puzzles.__file__)
from puzzles import PUZZLES
from bonus_puzzles import get_bonus_puzzle


app = Flask(__name__) 
app.secret_key = 'csc381fall'

def get_new_puzzle():
    category = random.choice(list(PUZZLES.keys()))
    puzzle = random.choice(PUZZLES[category])
    return category, puzzle.upper()

def next_player():
    """Advances the turn to the next player and resets round money."""
    player_count = len(session.get('players', []))
    if player_count > 0:
        session['current_player_index'] = (session.get('current_player_index', 0) + 1) % player_count
    session['money'] = 0 # Reset round money for the next player
    session.modified = True

@app.route('/')
def home(): 
  # This is now the main entry point, redirects to the home page
  return redirect(url_for('welcome'))

@app.route('/home')
def welcome():
    # Renders the new homepage
    return render_template('homepage.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    """Initializes the game with player names and the first puzzle."""
    session.clear() # Start a fresh game
    
    # Get player names from form
    player1 = request.form.get('player1', 'Player 1')
    player2 = request.form.get('player2', 'Player 2')
    player3 = request.form.get('player3', 'Player 3')
    
    # Store player data in session
    session['players'] = [
        {'name': player1, 'bank': 0},
        {'name': player2, 'bank': 0},
        {'name': player3, 'bank': 0}
    ]
    session['current_player_index'] = 0
    
    # Set up the first round
    session['round'] = 1
    session['money'] = 0 # Current round money
    session['guessed'] = []
    
    # Get the first puzzle
    category, phrase = get_new_puzzle()
    session['puzzle'] = phrase.upper()
    session['category'] = category

    session['initialized'] = True # Mark session as started
    session.modified = True
    
    return redirect(url_for('board'))


@app.route('/wheel')
def wheel(): 
  # Redirect to home if game hasn't started
  if 'players' not in session:
      return redirect(url_for('home'))
  return render_template('wheel.html')

@app.route('/buy_vowel', methods=['POST'])
def buy_vowel():
    # Redirect to home if game hasn't started
    if 'players' not in session:
        return redirect(url_for('home'))

    vowel = request.form['vowel'].upper()
    if vowel not in "AEIOU":
        flash("That's not a vowel!",'error')
        return redirect(url_for('board'))

    if session.get('money', 0) < 250:
        flash("Not enough money to buy a vowel!",'error')
        return redirect(url_for('board'))

    session['money'] -= 250
    if vowel not in session['guessed']:
        session['guessed'].append(vowel)
        session.modified = True

    # Buying a vowel always costs a turn, regardless of whether it's in the puzzle
    flash(f"You bought a '{vowel}'. Next player's turn.", 'info')
    next_player()
    return redirect(url_for('board'))

@app.route('/spin', methods=['GET','POST']) 
def spin(): 
  # This route appears to be unused by wheel.html, but we'll keep it safe
  if 'players' not in session:
      return redirect(url_for('home'))
  
  wheel_values = [100, 200, 300, 400, 'BANKRUPT', 400, 500, 'MISS A TURN', 600, 700, 800, 900, 1000]
  result = random.choice(wheel_values)
  session['last_spin'] = result

  if isinstance(result, int):
        session['money'] = session.get('money', 0) + result
        flash(f"You spun ${result}!",'info')
  elif result == 'BANKRUPT':
        session['money'] = 0
        flash("BANKRUPT! You lost all your money!",'info')
        next_player() # Bankrupt loses a turn
  elif result == 'MISS A TURN':
        flash("You missed your turn!",'info')
        next_player() # Miss a turn
  return render_template('wheel.html', result=result)

@app.route('/spin_result')
def spin_result():
  if 'players' not in session:
     return jsonify({'error': 'Game not started'}), 401

  value = request.args.get('value')
  if not value:
     return jsonify({'error': 'No spin value received'}), 400
  
  session['last_spin'] = value
  money = session.get('money', 0)
  player_index = session.get('current_player_index', 0)
  player_name = session['players'][player_index]['name']

  result_message = ""

  if value and value.isdigit(): 
    session['money'] = money + int(value)
    result_message = f"{player_name} spun ${value}!"
    flash(result_message,'info')
  elif value == 'BANKRUPT':
    session['money'] = 0
    result_message = f"{player_name} went BANKRUPT! Lost turn and round money."
    flash(result_message,'info')
    next_player()
  elif value in ('LOSE A TURN', 'MISS A TURN'):
    result_message = f"{player_name} spun LOSE A TURN."
    flash(result_message,'info')
    next_player()
  else: 
    result_message = "Invalid spin result."
    flash(result_message,'info')

  session.modified = True

  # Return the current player's round money
  return jsonify({'result' : value, 'money' : session.get('money', 0)})

@app.route('/guess', methods=['POST'])
def guess(): 
  if 'players' not in session:
        return redirect(url_for('home'))
        
  letter = request.form['letter'].upper()
  if not (letter and letter.isalpha() and len(letter) == 1):
      flash("Invalid guess. Please enter a single letter.", 'error')
      return redirect(url_for('board'))

  if letter in "AEIOU":
     flash("You must buy vowels! Guess a consonant.", 'error')
     return redirect(url_for('board'))
  
  if letter in session['guessed']:
      flash(f"'{letter}' has already been guessed!", 'info')
      next_player() # Guessing a used letter loses a turn
      return redirect(url_for('board'))

  session['guessed'].append(letter)
  session.modified = True
  
  spin_amount = session.get('last_spin', 0)
  # Ensure last_spin was a number
  try:
      spin_amount = int(spin_amount)
  except (ValueError, TypeError):
      spin_amount = 0 # Default to 0 if last spin wasn't a valid amount

  if letter in session['puzzle']:
      count = session['puzzle'].count(letter)
      session['money'] += (spin_amount * count)
      flash(f"Found {count} '{letter}'(s)!", 'success')
  else:
      flash(f"Sorry, no '{letter}'(s).", 'info')
      next_player() # Wrong guess loses a turn

  return redirect(url_for('board'))
  
@app.route('/solve', methods=['POST']) 
def solve(): 
  if 'players' not in session:
        return redirect(url_for('home'))

  guess = request.form.get('guess', '').upper().strip()
  puzzle = session.get('puzzle','').upper()
  player_index = session.get('current_player_index', 0)
  
  if guess == puzzle: 
    # Add current round money to the player's bank
    session['players'][player_index]['bank'] += session.get('money', 0)
    flash(f"Great job! You solved the puzzle! ${session.get('money', 0)} added to your bank.", 'success')
    
    session['bonus_eligible'] = True
    session['bonus_player'] = session['players'][player_index]['name']
    session.modified = True
    return redirect(url_for('bonus_intro'))
  else: 
    flash("Sorry, that is incorrect.", 'info')
    next_player() # Wrong solve loses a turn
    return redirect(url_for('board'))

@app.route('/bonus_intro')
def bonus_intro():
   if 'players' not in session:
        return redirect(url_for('home'))
   categories = ["Things", "Places", "People", "Events", "Phrases"]
   return render_template('bonus_intro.html', categories=categories)

@app.route('/start_bonus', methods=['POST'])
def start_bonus():
   if 'players' not in session:
        return redirect(url_for('home'))
   category = request.form['category']
   prizes = ["$5,000", "$10,000", "$25,000", "Luxury Car", "Vacation", "New House", "Dining Set", "Jetski"]
   prize = random.choice(prizes)
   bonus_category, puzzle = get_bonus_puzzle(category)
   revealed = ''.join(c if c.upper() in "RSTLNE" else '_' for c in puzzle.upper()) #same as in board
   
   session['bonus_puzzle'] = puzzle
   session['bonus_revealed'] = revealed
   session['bonus_prize'] = prize
   session['bonus_category'] = bonus_category
   session['bonus_guessed'] = [] # Initialize list for bonus guesses

   return render_template('bonus_board.html', category=bonus_category,revealed=revealed,prize=prize)

@app.route('/bonus_guess', methods=['POST'])
def bonus_guess():
    if 'players' not in session:
        return redirect(url_for('home'))

    letter = request.form.get('letter', '').upper().strip()

    if not letter or len(letter) != 1 or not letter.isalpha():
        flash("Please enter a valid single letter.", "error")
        return redirect(url_for('bonus_board'))

    guessed = session.get('bonus_guessed', [])
    if letter in guessed or letter in "RSTLNE":
        flash("You already used that letter!", "info")
        return redirect(url_for('bonus_board'))

    guessed.append(letter)
    session['bonus_guessed'] = guessed

    puzzle = session.get('bonus_puzzle', '')
    revealed = ''.join([
        c if c == ' ' or c.upper() in guessed or c.upper() in "RSTLNE" else '_'
        for c in puzzle
    ])
    session['bonus_revealed'] = revealed
    session.modified = True

    # Check if all letters guessed (e.g., 3 consonants, 1 vowel)
    # This logic is simplified: user can guess one by one.
    # A more complex logic would limit guesses.
    # For now, we just re-render.

    return redirect(url_for('bonus_board'))

@app.route('/bonus_solve', methods=['POST'])
def bonus_solve():
    guess = request.form.get('guess', '').upper().strip()
    puzzle = session.get('bonus_puzzle', '').upper()
    prize = session.get('bonus_prize', '')

    if not puzzle:
        flash("No bonus puzzle in progress.", "error")
        return redirect(url_for('board'))

    if guess == puzzle:
        flash(f"Congratulations! You solved the bonus puzzle and won {prize}!", "success")
        session.clear()
        return redirect(url_for('board'))
    else:
        flash("Sorry, that's not correct.", "info")
        return redirect(url_for('bonus_board'))
@app.route('/bonus_board')
def bonus_board():
    if 'bonus_puzzle' not in session:
        flash("No bonus round in progress.", "error")
        return redirect(url_for('board'))
    return render_template('bonus_board.html',
                           category=session['bonus_category'],
                           revealed=session['bonus_revealed'],
                           prize=session['bonus_prize'])


@app.route('/new_puzzle')
def new_puzzle(): 
  if 'players' not in session:
        return redirect(url_for('home'))

  category, phrase = get_new_puzzle()
  session['puzzle'] = phrase.upper()
  session['category'] = category
  session['guessed'] = []
  session['money'] = 0
  session['round'] = session.get('round', 0)+1
  
  # Advance to the next player for the start of the new round
  next_player() 
  
  return redirect(url_for('board'))

#clear cache on reset
@app.before_request
def clear_session_on_restart():
    # This logic is now handled by the /start_game route
    # We can keep it to clear session on server restart
    if not session.get('initialized'):
        session.clear()
        session['initialized'] = True


#Choose random puzzle when game starts 
@app.route('/board') 
def board(): 
  # Check if the game has been initialized
  if 'players' not in session or 'puzzle' not in session: 
    # If game not started, send to home page
    return redirect(url_for('home'))

  # Get current player info
  player_index = session.get('current_player_index', 0)
  current_player_name = session['players'][player_index]['name']
  
  # Get leaderboard data (all players and their banks)
  leaderboard = session.get('players', [])

  if 'guessed' not in session:
      session['guessed'] = []
      
  puzzle = session['puzzle']
  guessed = session['guessed']
  
  #Shows letters that have been guessed correctly and produces the current visible puzzle
  revealed = ''.join([c if c == ' ' or c.upper() in guessed else '_' for c in puzzle])
  
  return render_template('board.html', 
                         category=session['category'],
                         money=session.get('money', 0), # This is the current ROUND money
                         round=session['round'],
                         player=current_player_name, # This is the CURRENT player's name
                         revealed=revealed,
                         leaderboard=leaderboard) # This is the list of all players and banks

if __name__ == '__main__': 
 app.run(debug=True)