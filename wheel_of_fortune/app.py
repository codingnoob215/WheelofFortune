from flask import Flask, flash, render_template, request, session, url_for, jsonify, redirect
import random
import bonus_puzzles
from puzzles import PUZZLES
from bonus_puzzles import get_bonus_puzzle

app = Flask(__name__)
app.secret_key = 'csc381fall'

def get_new_puzzle():
    category = random.choice(list(PUZZLES.keys()))
    puzzle = random.choice(PUZZLES[category])
    return category, puzzle.upper()

@app.route('/')
def home():
    return redirect(url_for('start'))

@app.route('/start', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        session.clear()
        players = [
            request.form.get('player1', 'PLAYER 1').upper(),
            request.form.get('player2', 'PLAYER 2').upper(),
            request.form.get('player3', 'PLAYER 3').upper()
        ]
        session['players'] = players
        session['current_player'] = 0
        session['banks'] = {p: 0 for p in players}
        session['phase'] = 'tossup'
        session['tossup_stage'] = 'start'
        category, puzzle = get_new_puzzle()
        session['tossup_category'] = category
        session['tossup_puzzle'] = puzzle
        session['tossup_guessed'] = []
        session['awaiting_tossup_solve'] = False
        session['puzzle'] = None
        session['category'] = None
        session['guessed'] = []
        session['current_spin_value'] = None
        session['spin_rounds_completed'] = 0
        session['round'] = 0
        session.modified = True
        return redirect(url_for('board'))
    return render_template('start.html')

@app.before_request
def ensure_defaults():
    if 'players' not in session:
        session['players'] = ["PLAYER 1", "PLAYER 2", "PLAYER 3"]
    if 'banks' not in session:
        session['banks'] = {p: 0 for p in session['players']}
    if 'current_player' not in session:
        session['current_player'] = 0
    session.modified = False

@app.route('/board')
def board():
    if session.get('phase') == 'tossup' and 'tossup_puzzle' not in session:
        category, puzzle = get_new_puzzle()
        session['tossup_category'] = category
        session['tossup_puzzle'] = puzzle
        session['tossup_guessed'] = []
        session.modified = True
    if session.get('phase') == 'main' and not session.get('puzzle'):
        category, phrase = get_new_puzzle()
        session['puzzle'] = phrase.upper()
        session['category'] = category
        session['guessed'] = []
        session['current_spin_value'] = None
        session['round'] = session.get('round', 1)
        session.modified = True
    if session.get('phase') == 'tossup':
        puzzle = session.get('tossup_puzzle', '')
        guessed = session.get('tossup_guessed', [])
        category = session.get('tossup_category', '')
    else:
        puzzle = session.get('puzzle', '')
        guessed = session.get('guessed', [])
        category = session.get('category', '')
    revealed = ''.join([c if c == ' ' or c.upper() in guessed else '_' for c in puzzle])
    players = session.get('players', [])
    banks = session.get('banks', {p: 0 for p in players})
    player_money = [banks.get(p, 0) for p in players]
    return render_template('board.html',
                           category=category,
                           round=session.get('round', 1),
                           players=players,
                           current_player=session.get('current_player', 0),
                           player_money=player_money,
                           revealed=revealed,
                           phase=session.get('phase', 'tossup'),
                           tossup_stage=session.get('tossup_stage', None),
                           awaiting_tossup_solve=session.get('awaiting_tossup_solve', False))

@app.route('/wheel')
def wheel():
    return render_template('wheel.html')

@app.route('/spin')
def spin():
    values = [100, 200, 300, 400, 'BANKRUPT', 400, 500, 'MISS A TURN', 600, 700, 800, 900, 1000]
    result = random.choice(values)
    return redirect(url_for('spin_result', value=str(result)))

@app.route('/spin_result')
def spin_result():
    value = request.args.get('value')
    if value is None:
        return jsonify({'error': 'No spin value received'}), 400
    players = session.get('players', ["PLAYER 1", "PLAYER 2", "PLAYER 3"])
    player = players[session.get('current_player', 0)]
    if value.isdigit():
        val = int(value)
        session['current_spin_value'] = val
        session.modified = True
        return jsonify({'result': value, 'money': session.get('banks', {}).get(player, 0)})
    if value == 'BANKRUPT':
        session['banks'][player] = 0
        session['current_player'] = (session['current_player'] + 1) % len(players)
        session.modified = True
        return jsonify({'result': value, 'money': 0})
    if value in ('LOSE A TURN', 'MISS A TURN'):
        session['current_player'] = (session['current_player'] + 1) % len(players)
        session.modified = True
        return jsonify({'result': value, 'money': session.get('banks', {}).get(player, 0)})
    return jsonify({'error': 'Invalid spin result'}), 400

@app.route('/buy_vowel', methods=['POST'])
def buy_vowel():
    if session.get('phase') != 'main':
        flash("You can only buy vowels during the main round.", 'error')
        return redirect(url_for('board'))
    vowel = request.form.get('vowel', '').upper().strip()
    if not vowel or vowel not in "AEIOU":
        flash("That's not a vowel!", 'error')
        return redirect(url_for('board'))
    players = session['players']
    player = players[session.get('current_player', 0)]
    if session['banks'].get(player, 0) < 250:
        flash("Not enough money to buy a vowel!", 'error')
        session['current_player'] = (session['current_player'] + 1) % len(players)
        session.modified = True
        return redirect(url_for('board'))
    session.setdefault('guessed', [])
    if vowel in session.get('puzzle', '') and vowel not in session['guessed']:
        session['guessed'].append(vowel)
        session['banks'][player] -= 250
        flash(f"Vowel {vowel} revealed!", 'success')
    else:
        session['banks'][player] -= 250
        flash(f"Vowel {vowel} not in puzzle. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(players)
    session.modified = True
    return redirect(url_for('board'))

@app.route('/guess', methods=['POST'])
def guess():
    if session.get('phase') != 'main':
        flash("Consonant guessing is only allowed during the main round.", 'error')
        return redirect(url_for('board'))
    letter = request.form.get('letter', '').upper().strip()
    if not letter or len(letter) != 1 or not letter.isalpha():
        flash("Enter a single letter.", 'error')
        return redirect(url_for('board'))
    if letter in "AEIOU":
        flash("No vowels allowed here; use Buy Vowel.", 'error')
        return redirect(url_for('board'))
    players = session['players']
    player = players[session.get('current_player', 0)]
    if letter in session.get('guessed', []):
        flash("Letter already guessed.", 'info')
        return redirect(url_for('board'))
    session.setdefault('guessed', [])
    session['guessed'].append(letter)
    if letter in session.get('puzzle', ''):
        value = session.get('current_spin_value', 0)
        earned = value if isinstance(value, int) else 0
        session['banks'][player] = session['banks'].get(player, 0) + earned
        flash(f"Correct! {letter} is in the puzzle. {player} earns ${earned}.", 'success')
        session.pop('current_spin_value', None)
    else:
        flash(f"Sorry, {letter} is not in the puzzle. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(players)
    session.modified = True
    return redirect(url_for('board'))

@app.route('/solve', methods=['POST'])
def solve():
    guess_text = request.form.get('guess', '').upper().strip()
    if not guess_text:
        flash("Enter a solution.", 'error')
        return redirect(url_for('board'))
    if session.get('phase') == 'tossup':
        return redirect(url_for('tossup_solve'), code=307)
    puzzle = session.get('puzzle', '').upper()
    players = session['players']
    player = players[session.get('current_player', 0)]
    if guess_text == puzzle:
        flash(f"{player} solved the puzzle!", 'success')
        session['spin_rounds_completed'] = session.get('spin_rounds_completed', 0) + 1
        session['round'] = session.get('round', 0) + 1
        if session.get('spin_rounds_completed', 0) >= 2:
            session['phase'] = 'tossup'
            session['tossup_stage'] = 'end'
            category, puzzle = get_new_puzzle()
            session['tossup_category'] = category
            session['tossup_puzzle'] = puzzle
            session['tossup_guessed'] = []
            session['awaiting_tossup_solve'] = False
            session.modified = True
            return redirect(url_for('board'))
        else:
            category, phrase = get_new_puzzle()
            session['puzzle'] = phrase.upper()
            session['category'] = category
            session['guessed'] = []
            session['current_spin_value'] = None
            session.modified = True
            return redirect(url_for('board'))
    else:
        flash("Incorrect solution. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
        session.modified = True
        return redirect(url_for('board'))

@app.route('/tossup_guess', methods=['POST'])
def tossup_guess():
    if session.get('phase') != 'tossup':
        flash("Toss-up is not active.", 'error')
        return redirect(url_for('board'))
    letter = request.form.get('letter', '').upper().strip()
    if not letter or len(letter) != 1 or not letter.isalpha():
        flash("Enter one letter.", 'error')
        return redirect(url_for('board'))
    players = session['players']
    player = players[session.get('current_player', 0)]
    if letter in session.get('tossup_guessed', []):
        flash("Letter already guessed in toss-up.", 'info')
        return redirect(url_for('board'))
    session.setdefault('tossup_guessed', [])
    session['tossup_guessed'].append(letter)
    if letter in session.get('tossup_puzzle', ''):
        flash(f"{player} guessed {letter} and it's in the toss-up! You may attempt to solve now.", 'success')
        session['awaiting_tossup_solve'] = True
    else:
        flash(f"{letter} is not in the toss-up. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(players)
        session['awaiting_tossup_solve'] = False
    session.modified = True
    return redirect(url_for('board'))

@app.route('/tossup_solve', methods=['POST', 'GET'])
def tossup_solve():
    if session.get('phase') != 'tossup':
        flash("Toss-up is not active.", 'error')
        return redirect(url_for('board'))
    guess = request.form.get('guess', '').upper().strip() if request.method == 'POST' else ''
    if not guess:
        flash("Enter a solution to try to solve the toss-up.", 'info')
        return redirect(url_for('board'))
    players = session['players']
    player_idx = session.get('current_player', 0)
    player = players[player_idx]
    if guess == session.get('tossup_puzzle', '').upper():
        flash(f"{player} solved the toss-up!", 'success')
        session['tossup_solved_by'] = player
        session['banks'][player] = session['banks'].get(player, 0) + 1000
        if session.get('tossup_stage') == 'start':
            session['phase'] = 'main'
            session['tossup_stage'] = None
            category, phrase = get_new_puzzle()
            session['puzzle'] = phrase.upper()
            session['category'] = category
            session['guessed'] = []
            session['current_spin_value'] = None
            session['spin_rounds_completed'] = 0
            session['round'] = 1
            session['current_player'] = session['players'].index(player)
            session.modified = True
            return redirect(url_for('board'))
        else:
            session['phase'] = 'bonus'
            session['tossup_stage'] = None
            session['bonus_player'] = max(session['banks'].items(), key=lambda kv: kv[1])[0]
            flash(f"Final toss-up solved. {session['bonus_player']} goes to the bonus round!", 'info')
            session.modified = True
            return redirect(url_for('bonus_intro'))
    else:
        flash("Incorrect toss-up solve. Next player's chance.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
        session['awaiting_tossup_solve'] = False
        session.modified = True
        return redirect(url_for('board'))

@app.route('/end_tossup')
def end_tossup():
    if session.get('phase') != 'tossup':
        return redirect(url_for('board'))
    if not session.get('tossup_solved_by'):
        flash("Toss-up time over. No one solved it.", 'info')
    if session.get('tossup_stage') == 'start':
        session['phase'] = 'main'
        category, phrase = get_new_puzzle()
        session['puzzle'] = phrase.upper()
        session['category'] = category
        session['guessed'] = []
        session['current_spin_value'] = None
        session['round'] = 1
        session.modified = True
    elif session.get('tossup_stage') == 'end':
        session['phase'] = 'bonus'
        session['bonus_player'] = max(session['banks'].items(), key=lambda kv: kv[1])[0]
        session.modified = True
        return redirect(url_for('bonus_intro'))
    return redirect(url_for('board'))

@app.route('/new_puzzle')
def new_puzzle():
    category, phrase = get_new_puzzle()
    session['puzzle'] = phrase.upper()
    session['category'] = category
    session['guessed'] = []
    session['current_spin_value'] = None
    session['round'] = session.get('round', 0) + 1
    session.modified = True
    return redirect(url_for('board'))

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

@app.route('/bonus_intro')
def bonus_intro():
    if session.get('phase') != 'bonus':
        return redirect(url_for('board'))
    categories = ['PHRASES', 'PEOPLE', 'PLACES', 'THINGS']
    return render_template('bonus_intro.html', categories=categories, player=session.get('bonus_player'))

@app.route('/start_bonus', methods=['POST'])
def start_bonus():
    category = request.form.get('category', 'PHRASES')
    bonus_p = get_bonus_puzzle(category) if callable(get_bonus_puzzle) else ("BONUS", "EXAMPLE BONUS")
    if isinstance(bonus_p, tuple):
        bonus_cat = bonus_p[0]
        puzzle = bonus_p[1].upper()
    else:
        bonus_cat = category
        puzzle = str(bonus_p).upper()
    session['bonus_category'] = bonus_cat
    session['bonus_puzzle'] = puzzle
    session['bonus_revealed'] = ''.join(c if c == ' ' or c.upper() in "RSTLNE" else '_' for c in puzzle)
    session['bonus_guessed'] = []
    prizes = ["$5,000", "$10,000", "$25,000", "Luxury Car", "Vacation"]
    session['bonus_prize'] = random.choice(prizes)
    session.modified = True
    return redirect(url_for('bonus_board'))


@app.route('/reveal_bonus', methods=['POST'])
def reveal_bonus():
    consonants = request.form.get('consonants', '').upper().strip()
    vowel = request.form.get('vowel', '').upper().strip()
    puzzle = session.get('bonus_puzzle', '')
    if not puzzle:
        flash("No bonus puzzle in progress.", "error")
        return redirect(url_for('board'))
    picks = []
    for c in consonants:
        if c.isalpha():
            picks.append(c)
    if vowel and vowel.isalpha():
        picks.append(vowel)
    guessed = session.get('bonus_guessed', [])
    for p in picks:
        if p not in guessed:
            guessed.append(p)
    session['bonus_guessed'] = guessed
    revealed = ''.join([c if c == ' ' or c.upper() in guessed or c.upper() in "RSTLNE" else '_' for c in puzzle])
    session['bonus_revealed'] = revealed
    session.modified = True
    if '_' not in revealed:
      flash(f"You solved the bonus puzzle and won {session.get('bonus_prize')}!", "success")
    return redirect(url_for('start'))
    return render_template('bonus_board.html', category=session.get('bonus_category'), revealed=revealed, prize=session.get('bonus_prize'), player=session.get('bonus_player'))

@app.route('/bonus_guess', methods=['POST'])
def bonus_guess():
    letter = request.form.get('letter', '').upper().strip()

    if not letter or len(letter) != 1 or not letter.isalpha():
        flash("Please enter a valid letter before submitting.", "error")
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

    if '_' not in revealed:
        flash("You solved the bonus puzzle and won {session['bonus_prize']}!", "success")
        session.clear()  
        return redirect(url_for('board'))

    return redirect(url_for('bonus_board'))
    
@app.route('/bonus_board')
def bonus_board():
    if 'bonus_puzzle' not in session:
        flash("No bonus round in progress.", "error")
        return redirect(url_for('board'))
    return render_template('bonus_board.html', category=session.get('bonus_category'), revealed=session.get('bonus_revealed'), prize=session.get('bonus_prize'), player=session.get('bonus_player'))

if __name__ == '__main__':
    app.run(debug=True)
