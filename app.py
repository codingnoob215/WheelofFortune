from flask import Flask, flash, render_template, request, session, url_for, jsonify, redirect
import random
import time
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


@app.route('/')
def home():
    return redirect(url_for('start'))


@app.route('/start', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        # Reset session/game state
        session.clear()
        players = [
            request.form['player1'].upper(),
            request.form['player2'].upper(),
            request.form['player3'].upper()
        ]
        session['players'] = players
        session['current_player'] = 0
        session['banks'] = {p: 0 for p in players}  # cumulative money per player
        # Setup game flow counters
        session['phase'] = 'tossup'  # 'tossup' or 'main' or 'bonus'
        session['tossup_stage'] = 'start'  # 'start' or 'end' (end is final tossup to decide bonus)
        session['spin_rounds_completed'] = 0  # count of full main puzzles solved
        session['round'] = 0
        # choose toss-up puzzle
        category, puzzle = get_new_puzzle()
        session['tossup_category'] = category
        session['tossup_puzzle'] = puzzle
        session['tossup_guessed'] = []     # letters guessed during tossup
        session['tossup_solved_by'] = None
        session['awaiting_tossup_solve'] = False
        # main puzzle fields will be initialized when tossup is solved or when tossup ends
        session.modified = True
        return redirect(url_for('board'))
    return render_template('start.html')


# Wheel page (keeps single page)
@app.route('/wheel')
def wheel():
    # render wheel; actual spinning result endpoint is /spin_result
    # Disable spinning client-side if tossup active (board will show instructions).
    return render_template('wheel.html')


@app.route('/spin_result')
def spin_result():
    # Kept for wheel.html ajax compatibility (GET expected)
    value = request.args.get('value')
    if value is None:
        return jsonify({'error': 'No spin value received'}), 400

    # ensure current player present
    players = session.get('players', ["PLAYER 1", "PLAYER 2", "PLAYER 3"])
    player = players[session.get('current_player', 0)]
    # Handle numeric or special
    if value.isdigit():
        val = int(value)
        # store spin value for next /guess action so server knows how much to award
        session['current_spin_value'] = val
        session.modified = True
        # return current banks for UI to show
        return jsonify({'result': value, 'banks': session.get('banks', {})})
    elif value == 'BANKRUPT':
        session['banks'][player] = 0
        # bankrupt -> next player's turn
        session['current_player'] = (session['current_player'] + 1) % len(players)
        session.modified = True
        return jsonify({'result': value, 'banks': session.get('banks', {})})
    elif value in ('LOSE A TURN', 'MISS A TURN'):
        session['current_player'] = (session['current_player'] + 1) % len(players)
        session.modified = True
        return jsonify({'result': value, 'banks': session.get('banks', {})})
    else:
        return jsonify({'error': 'Invalid spin result'}), 400


@app.route('/buy_vowel', methods=['POST'])
def buy_vowel():
    # Only allowed during main phase
    if session.get('phase') != 'main':
        flash("You can only buy vowels during the main spins.", 'error')
        return redirect(url_for('board'))

    vowel = request.form['vowel'].upper()
    if vowel not in "AEIOU":
        flash("That's not a vowel!", 'error')
        return redirect(url_for('board'))

    player = session['players'][session.get('current_player', 0)]
    if session['banks'].get(player, 0) < 250:
        flash("Not enough money to buy a vowel!", 'error')
        # advance turn
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
        return redirect(url_for('board'))

    # process vowel
    if vowel in session.get('puzzle', '') and vowel not in session.get('guessed', []):
        session['guessed'].append(vowel)
        session['banks'][player] = session['banks'].get(player, 0) - 250
        flash(f"Vowel {vowel} revealed!", 'success')
        # player keeps turn (they can keep buying/spinning)
    else:
        # incorrect vowel: charge and advance
        session['banks'][player] = session['banks'].get(player, 0) - 250
        flash(f"Vowel {vowel} not in puzzle. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
    session.modified = True
    return redirect(url_for('board'))


@app.route('/guess', methods=['POST'])
def guess():
    # Guess a consonant during the main spin round
    if session.get('phase') != 'main':
        flash("Consonant guessing is only allowed during the main round.", 'error')
        return redirect(url_for('board'))

    letter = request.form['letter'].upper().strip()
    if not letter or not letter.isalpha() or len(letter) != 1:
        flash("Enter a single letter.", 'error')
        return redirect(url_for('board'))

    if letter in "AEIOU":
        flash("No vowels allowed here; use Buy Vowel.", 'error')
        return redirect(url_for('board'))

    player = session['players'][session.get('current_player', 0)]
    if letter in session.get('guessed', []):
        flash("Letter already guessed.", 'info')
        return redirect(url_for('board'))

    session.setdefault('guessed', [])
    session['guessed'].append(letter)
    if letter in session.get('puzzle', ''):
        # Award money based on current spin value
        value = session.get('current_spin_value', 0)
        earned = value if isinstance(value, int) else 0
        session['banks'][player] = session['banks'].get(player, 0) + earned
        flash(f"Correct! {letter} is in the puzzle. {player} earns ${earned}.", 'success')
        # Player keeps turn (they can spin again)
        session.pop('current_spin_value', None)
    else:
        flash(f"Sorry, {letter} is not in the puzzle. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
    session.modified = True
    return redirect(url_for('board'))


@app.route('/solve', methods=['POST'])
def solve():
    guess = request.form.get('guess', '').upper().strip()
    if not guess:
        flash("Enter a solution.", 'error')
        return redirect(url_for('board'))

    # If in tossup, route to tossup solve behavior
    if session.get('phase') == 'tossup':
        # Let tossup_solve handle validation/turns
        return redirect(url_for('tossup_solve'), code=307)

    # main game solve
    puzzle = session.get('puzzle', '').upper()
    player = session['players'][session.get('current_player', 0)]
    if guess == puzzle:
        # award player's bank (no extra immediate bonus except cumulative)
        flash(f"{player} solved the puzzle!", 'success')
        # increment completed main spin puzzle count
        session['spin_rounds_completed'] = session.get('spin_rounds_completed', 0) + 1
        session['round'] = session.get('round', 0) + 1

        # After solving, check if we've finished the configured two spin rounds
        if session['spin_rounds_completed'] >= 2:
            # move to final tossup to decide bonus
            session['phase'] = 'tossup'
            session['tossup_stage'] = 'end'
            category, puzzle = get_new_puzzle()
            session['tossup_category'] = category
            session['tossup_puzzle'] = puzzle
            session['tossup_guessed'] = []
            session['awaiting_tossup_solve'] = False
            flash("Two spin rounds completed. Final toss-up starting to decide the bonus round!", 'info')
            session.modified = True
            return redirect(url_for('board'))
        else:
            # start next main puzzle
            category, phrase = get_new_puzzle()
            session['puzzle'] = phrase.upper()
            session['category'] = category
            session['guessed'] = []
            session['money'] = 0
            session.modified = True
            return redirect(url_for('board'))
    else:
        flash("Incorrect solution. Next player's turn.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
        session.modified = True
        return redirect(url_for('board'))


# TOSS-UP handling endpoints (use board view)
@app.route('/tossup_guess', methods=['POST'])
def tossup_guess():
    # A player guesses a single letter during tossup
    if session.get('phase') != 'tossup':
        flash("Toss-up is not active.", 'error')
        return redirect(url_for('board'))

    letter = request.form.get('letter', '').upper().strip()
    if not letter or len(letter) != 1 or not letter.isalpha():
        flash("Enter one letter.", 'error')
        return redirect(url_for('board'))

    player = session['players'][session.get('current_player', 0)]

    if letter in session.get('tossup_guessed', []):
        flash("Letter already guessed in toss-up.", 'info')
        return redirect(url_for('board'))

    session.setdefault('tossup_guessed', [])
    session['tossup_guessed'].append(letter)
    if letter in session.get('tossup_puzzle', ''):
        flash(f"{player} guessed {letter} and it's in the toss-up! You may attempt to solve now.", 'success')
        session['awaiting_tossup_solve'] = True
        # keep current player so they can press Solve
    else:
        flash(f"{letter} is not in the toss-up. Next player's turn.", 'info')
        # move to next player
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
        session['awaiting_tossup_solve'] = False

    session.modified = True
    return redirect(url_for('board'))


@app.route('/tossup_solve', methods=['POST', 'GET'])
def tossup_solve():
    if session.get('phase') != 'tossup':
        flash("Toss-up is not active.", 'error')
        return redirect(url_for('board'))

    # solve can be called via POST (form) or GET redirect
    guess = request.form.get('guess', '').upper().strip() if request.method == 'POST' else ''
    player_idx = session.get('current_player', 0)
    player = session['players'][player_idx]

    # if no guess provided just redirect to board
    if not guess:
        flash("Enter a solution to try to solve the toss-up.", 'info')
        return redirect(url_for('board'))

    if guess == session.get('tossup_puzzle', '').upper():
        flash(f"{player} solved the toss-up!", 'success')
        session['tossup_solved_by'] = player
        # reward for tossup
        session['banks'][player] = session['banks'].get(player, 0) + 1000
        # If this was the starting tossup (start stage), move to main play
        if session.get('tossup_stage') == 'start':
            session['phase'] = 'main'
            session['tossup_stage'] = None
            # initialize first main puzzle
            category, phrase = get_new_puzzle()
            session['puzzle'] = phrase.upper()
            session['category'] = category
            session['guessed'] = []
            session['money'] = 0
            session['spin_rounds_completed'] = 0
            session['round'] = 1
            # tossup winner spins first
            session['current_player'] = session['players'].index(player)
            session.modified = True
            return redirect(url_for('board'))
        else:
            # final tossup (end stage) -> decide bonus player
            session['phase'] = 'bonus'
            session['tossup_stage'] = None
            session['bonus_player'] = max(session['banks'].items(), key=lambda kv: kv[1])[0]
            flash(f"Final toss-up solved. {session['bonus_player']} goes to the bonus round!", 'info')
            # redirect to bonus setup page
            session.modified = True
            return redirect(url_for('bonus'))
    else:
        flash("Incorrect toss-up solve. Next player's chance.", 'info')
        session['current_player'] = (session['current_player'] + 1) % len(session['players'])
        session['awaiting_tossup_solve'] = False
        session.modified = True
        return redirect(url_for('board'))


@app.route('/end_tossup')
def end_tossup():
    # Called if a tossup timer runs out — treat as move-on to next phase
    if session.get('phase') != 'tossup':
        return redirect(url_for('board'))

    if not session.get('tossup_solved_by'):
        flash("Toss-up time over. No one solved it.", 'info')

    if session.get('tossup_stage') == 'start':
        # start main anyway, choose current player as starter if none solved
        session['phase'] = 'main'
        category, phrase = get_new_puzzle()
        session['puzzle'] = phrase.upper()
        session['category'] = category
        session['guessed'] = []
        session['money'] = 0
        session['round'] = 1
        session.modified = True
    elif session.get('tossup_stage') == 'end':
        # move to bonus (determine highest bank)
        session['phase'] = 'bonus'
        session['bonus_player'] = max(session['banks'].items(), key=lambda kv: kv[1])[0]
        session.modified = True
        return redirect(url_for('bonus'))

    return redirect(url_for('board'))


@app.route('/new_puzzle')
def new_puzzle():
    # start a new main puzzle (used after a solve when still in main rounds)
    category, phrase = get_new_puzzle()
    session['puzzle'] = phrase.upper()
    session['category'] = category
    session['guessed'] = []
    session['money'] = 0
    session['round'] = session.get('round', 0) + 1
    session.modified = True
    return redirect(url_for('board'))


@app.route('/bonus', methods=['GET'])
def bonus():
    # Show who is in bonus and category selection
    if session.get('phase') != 'bonus':
        return redirect(url_for('board'))
    # let's provide some categories for bonus selection
    categories = ['PHRASES', 'PEOPLE', 'PLACES', 'THINGS']
    return render_template('bonus.html', categories=categories, player=session.get('bonus_player'))


@app.route('/start_bonus', methods=['POST'])
def start_bonus():
    # Accept chosen category and present bonus puzzle
    category = request.form.get('category')
    # generate a special bonus puzzle (reuse get_bonus_puzzle if available)
    bonus_p = get_bonus_puzzle(category) if callable(get_bonus_puzzle) else ("BONUS", "EXAMPLE BONUS")
    session['bonus_category'] = category
    session['bonus_puzzle'] = bonus_p[1].upper() if isinstance(bonus_p, tuple) else str(bonus_p).upper()
    # Render a simple bonus screen
    return render_template('bonus_play.html', player=session.get('bonus_player'), category=category, puzzle=session['bonus_puzzle'])


@app.before_request
def ensure_defaults():
    # Ensure there are defaults to avoid KeyErrors when hitting /board
    if 'players' not in session:
        session['players'] = ["PLAYER 1", "PLAYER 2", "PLAYER 3"]
    if 'banks' not in session:
        session['banks'] = {p: 0 for p in session['players']}
    session.modified = False


@app.route('/board', methods=['GET', 'POST'])
def board():
    # Board uses the current session to render the page.
    # If no puzzle set (first landing), initialize an initial tossup started from /start flow
    if 'tossup_puzzle' not in session and session.get('phase') == 'tossup':
        category, puzzle = get_new_puzzle()
        session['tossup_category'] = category
        session['tossup_puzzle'] = puzzle
        session['tossup_guessed'] = []
        session.modified = True

    # If main-phase puzzle not initialized, ensure fields exist
    if session.get('phase') == 'main' and 'puzzle' not in session:
        category, phrase = get_new_puzzle()
        session['puzzle'] = phrase.upper()
        session['category'] = category
        session['guessed'] = []
        session['money'] = 0
        session['round'] = session.get('round', 1)
        session.modified = True

    # Prepare revealed string for whichever puzzle is active
    if session.get('phase') == 'tossup':
        puzzle = session.get('tossup_puzzle', '')
        guessed = session.get('tossup_guessed', [])
    else:
        puzzle = session.get('puzzle', '')
        guessed = session.get('guessed', [])

    revealed = ''.join([c if c == ' ' or c.upper() in guessed else '_' for c in puzzle])

    # Build player money list in order of players for template
    players = session.get('players', ["PLAYER 1", "PLAYER 2", "PLAYER 3"])
    banks = session.get('banks', {p: 0 for p in players})
    player_money = [banks.get(p, 0) for p in players]

    return render_template(
        'board.html',
        category=(session.get('tossup_category') if session.get('phase') == 'tossup' else session.get('category')),
        round=session.get('round', 1),
        players=players,
        current_player=session.get('current_player', 0),
        player_money=player_money,
        revealed=revealed,
        phase=session.get('phase', 'main'),
        tossup_stage=session.get('tossup_stage', None),
        awaiting_tossup_solve=session.get('awaiting_tossup_solve', False)
    )


if __name__ == '__main__':
    app.run(debug=True)
