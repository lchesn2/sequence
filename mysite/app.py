from flask import Flask, flash, render_template, redirect, url_for, request, session
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
import datetime
import pytz
import pandas as pd
import secrets
import os
from threading import Lock

GAMES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'games.csv')

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

CATEGORY_CONFIG = {
    'Fame': {
        'Sequence':     {'display': 'Finish',        'description': 'Completing a sequence'},
        'Block':        {'display': 'Block',         'description': "Stopping an opponent's sequence"},
        'Assist':       {'display': 'Assist',        'description': "Setting up a teammate's finish"},
    },
    'Shame': {
        'Misfire':        {'display': 'Misfire',       'description': 'A bad chip toss that disturbs the board (scattered chips, bumped pieces, knocked-off spots)'},
        'Tunnel Vision':  {'display': 'Tunnel Vision', 'description': 'Only seeing one path: removing/playing for a single option when a better play (e.g. blocking two threats) was available but unseen'},
    },
    'Flame': {
        'Bullseye':     {'display': 'Bullseye',     'description': 'A perfect chip toss, landed clean and dead center'},
        '20-20 Vision': {'display': '20-20 Vision', 'description': 'Playing the path that turned out to matter (e.g. choosing to remove for the assist over blocking, and it pays off when a teammate had the exact finishing card)'},
    },
}
TYPE_TO_CATEGORY = {t: cat for cat, types in CATEGORY_CONFIG.items() for t in types}

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Global lock for thread safety
lock = Lock()

class User(UserMixin):
    def __init__(self, username, role, offices):
        self.username = username
        self.role = role
        self.offices = offices  # list; active office stored in session

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id, users[user_id]['role'], users[user_id]['offices'])
    return None

users = {
    # ADP office
    'Jaemo':     {'password': 'jae', 'role': 'user',  'offices': ['ADP']},
    'John':      {'password': 'joh', 'role': 'user',  'offices': ['ADP']},
    'Adam':      {'password': 'ada', 'role': 'user',  'offices': ['ADP']},
    'Behring':   {'password': 'beh', 'role': 'user',  'offices': ['ADP']},
    'Daniel':    {'password': 'dan', 'role': 'user',  'offices': ['ADP']},
    'Howard':    {'password': 'how', 'role': 'user',  'offices': ['ADP']},
    'Jose':      {'password': 'jos', 'role': 'user',  'offices': ['ADP']},
    'Russell':   {'password': 'rus', 'role': 'user',  'offices': ['ADP']},
    'Mel':       {'password': 'mel', 'role': 'user',  'offices': ['ADP']},
    'Kenji':     {'password': 'ken', 'role': 'admin', 'offices': ['ADP']},
    'Maya':      {'password': 'may', 'role': 'admin', 'offices': ['ADP']},
    'Nishant':   {'password': 'nis', 'role': 'admin', 'offices': ['ADP']},
    'Edward':    {'password': 'edw', 'role': 'admin', 'offices': ['ADP']},
    'Pratishta': {'password': 'pra', 'role': 'admin', 'offices': ['ADP']},
    'Choi':      {'password': 'cho', 'role': 'admin', 'offices': ['ADP']},
    # Irwin office
    'Kevin':  {'password': 'kev',    'role': 'admin', 'offices': ['Irwin']},
    'Jazz':   {'password': 'jaz',    'role': 'admin', 'offices': ['Irwin']},
    'Isaac':  {'password': 'isa',    'role': 'admin', 'offices': ['Irwin']},
    'Mitch':  {'password': 'mit',    'role': 'user',  'offices': ['Irwin']},
    'Mike':   {'password': 'mik',    'role': 'user',  'offices': ['Irwin']},
    'Jason':  {'password': 'jas',    'role': 'user',  'offices': ['Irwin']},
    'Sherry': {'password': 'she',    'role': 'user',  'offices': ['Irwin']},
    'Landon': {'password': 'lan',    'role': 'user',  'offices': ['Irwin']},
    'Ryan':   {'password': 'rya',    'role': 'user',  'offices': ['Irwin']},
    'Brent':  {'password': 'bre',    'role': 'user',  'offices': ['Irwin']},
    # Multi-office
    'Larah':  {'password': 'newton', 'role': 'admin', 'offices': ['ADP', 'Irwin']},
}

OFFICE_PLAYERS = {
    'ADP':   ['Adam', 'Behring', 'Choi', 'Daniel', 'Edward', 'Howard',
              'John', 'Jose', 'Kenji', 'Maya', 'Mel', 'Nishant', 'Pratishta', 'Russell'],
    'Irwin': ['Brent', 'Isaac', 'Jason', 'Jazz', 'Kevin', 'Landon',
              'Larah', 'Mike', 'Mitch', 'Ryan', 'Sherry'],
}

def ensure_csv_exists(filename, default_columns):
    if not os.path.exists(filename):
        pd.DataFrame(columns=default_columns).to_csv(filename, index=False)

def _backfill_office(df):
    if 'office' not in df.columns:
        df['office'] = 'ADP'
    else:
        df['office'] = df['office'].where(df['office'].notna() & (df['office'] != ''), 'ADP')
    return df

def _backfill_category(df):
    """Backfill missing category values using TYPE_TO_CATEGORY; defaults to Fame."""
    if 'category' not in df.columns:
        df['category'] = df['type'].map(TYPE_TO_CATEGORY).fillna('Fame')
    else:
        df['category'] = df['category'].where(df['category'].notna() & (df['category'] != ''),
                                               df['type'].map(TYPE_TO_CATEGORY).fillna('Fame'))
    return df

def gen_all_game_df():
    try:
        ensure_csv_exists(GAMES_CSV, ['date', 'time', 'team', 'name', 'card', 'type', 'category', 'office'])
        game_df = pd.read_csv(GAMES_CSV)
        game_df = _backfill_category(game_df)
        game_df = _backfill_office(game_df)
        game_df['date'] = pd.to_datetime(game_df['date'], errors='coerce')

        return game_df.sort_values(by=['type', 'date', 'time'], ascending=[True, False, True]).reset_index(drop=True)
    except Exception as e:
        print(f"Error loading game data: {e}")
        return pd.DataFrame(columns=['date', 'time', 'team', 'name', 'card', 'type', 'category', 'office'])

def get_last_player(df):
    """Get the most recent player by date + time descending"""
    if df.empty:
        return "No entries yet"

    try:
        df_copy = df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['date'])
        df_copy['time'] = pd.to_datetime(df_copy['time'], format='%H:%M:%S').dt.time
        df_copy['timestamp'] = df_copy.apply(lambda row: pd.Timestamp.combine(row['date'], row['time']), axis=1)
        df_copy = df_copy.sort_values(by='timestamp', ascending=False)

        return df_copy.iloc[0]['name']
    except Exception as e:
        print(f"Error finding last player: {e}")
        return "Error"

def get_quarter_date_range(quarter_str):
    """Get the start and end dates for a given quarter string like '2025Q3'"""
    if quarter_str == 'ALL':
        return None, None
    
    try:
        year = int(quarter_str[:4])
        quarter_num = int(quarter_str[5])
        
        quarter_ranges = {
            1: (f'{year}-01-01', f'{year}-03-31'),
            2: (f'{year}-04-01', f'{year}-06-30'),
            3: (f'{year}-07-01', f'{year}-09-30'),
            4: (f'{year}-10-01', f'{year}-12-31'),
        }
        
        if quarter_num in quarter_ranges:
            return pd.to_datetime(quarter_ranges[quarter_num][0]), pd.to_datetime(quarter_ranges[quarter_num][1])
    except (ValueError, IndexError):
        pass
    
    return None, None

def get_available_quarters(df):
    """Get list of all quarters present in the data"""
    if df.empty:
        return []
    
    # Add year-quarter column
    df_copy = df.copy()
    df_copy['year_quarter'] = df_copy['date'].dt.to_period('Q').astype(str)
    
    # Get unique quarters and sort them
    quarters = sorted(df_copy['year_quarter'].unique())
    
    return quarters

def load_games_df(office=None):
    ensure_csv_exists(GAMES_CSV, ['date', 'time', 'team', 'name', 'card', 'type', 'category', 'office'])
    df = pd.read_csv(GAMES_CSV)
    df = _backfill_category(df)
    df = _backfill_office(df)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    if office:
        df = df[df['office'] == office]
    return df

def calculate_category_stats(df, category, quarter='2025Q3'):
    """Calculate per-type counts for a given category and quarter (or ALL)."""
    type_keys = list(CATEGORY_CONFIG[category].keys())
    empty = {t.lower().replace(' ', '_'): pd.DataFrame(columns=['name', 'TotalFinishes']) for t in type_keys}

    if df.empty:
        return empty

    if quarter != 'ALL':
        start_date, end_date = get_quarter_date_range(quarter)
        if start_date and end_date:
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

    stats = {}
    for game_type in type_keys:
        key = game_type.lower().replace(' ', '_')
        type_df = df[df['type'] == game_type]
        if not type_df.empty:
            type_stats = type_df.groupby('name').size().reset_index(name='TotalFinishes')
            stats[key] = type_stats.sort_values('TotalFinishes', ascending=False).reset_index(drop=True)
        else:
            stats[key] = pd.DataFrame(columns=['name', 'TotalFinishes'])
    return stats

def get_active_office():
    """Return the office currently selected in session, defaulting to the user's first office."""
    return session.get('office', current_user.offices[0])

# Initialize global dataframe
game_df = gen_all_game_df()

@app.route('/')
def start():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if username in users and password == users[username]['password']:
            user = User(username, users[username]['role'], users[username]['offices'])
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            if len(user.offices) > 1:
                return redirect(url_for('select_office'))
            session['office'] = user.offices[0]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/select-office', methods=['GET', 'POST'])
@login_required
def select_office():
    if request.method == 'POST':
        office = request.form.get('office')
        if office in current_user.offices:
            session['office'] = office
            return redirect(url_for('dashboard'))
    return render_template('select_office.html',
                           offices=current_user.offices,
                           name=current_user.username)

@app.route('/dashboard')
@login_required
def dashboard():
    global game_df

    try:
        # Get current date in PST timezone
        pst = pytz.timezone('US/Pacific')
        today = pd.to_datetime(datetime.datetime.now(pst).date())

        # Filter today's games to this user's office
        office_df = game_df[game_df['office'] == get_active_office()]
        todays_games = office_df[office_df['date'].dt.date == today.date()][['date', 'time', 'name', 'type']].copy()

        # Find the most recent player in this office
        last_player = get_last_player(office_df)

        todays_games['timestamp'] = todays_games['date'].dt.strftime('%Y-%m-%d') + ' ' + todays_games['time'].astype(str)
        todays_games = todays_games.sort_values('timestamp', ascending=False)
        data = todays_games[['timestamp', 'name', 'type']].values.tolist()
        office_players = OFFICE_PLAYERS.get(get_active_office(), [])

        if current_user.role == 'admin':
            return render_template('admin.html',
                                 data=data,
                                 nxtTurn=last_player,
                                 name=current_user.username,
                                 office_players=office_players)
        elif current_user.role == 'user':
            return render_template('user.html',
                                 data=data,
                                 nxtTurn=last_player,
                                 name=current_user.username)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        print(f"Dashboard error: {e}")

    return redirect(url_for('login'))

@app.route('/submit_form', methods=['POST'])
@login_required
def submit_form():
    global game_df

    try:
        date = request.form.get('date', '')
        time = request.form.get('time', '')
        name = request.form.get('name', '')
        game_type = request.form.get('type', '')

        # Validate
        if not all([date, time, name, game_type]):
            flash('All fields are required', 'error')
            return redirect(url_for('dashboard'))

        category = TYPE_TO_CATEGORY.get(game_type, 'Fame')
        new_row = {
            'date': date,
            'time': time,
            'team': '',
            'name': name,
            'card': '',
            'type': game_type,
            'category': category,
            'office': get_active_office(),
        }

        with lock:
            game_df = pd.concat([game_df, pd.DataFrame([new_row])], ignore_index=True)
            game_df['date'] = pd.to_datetime(game_df['date'])
            game_df['date'] = game_df['date'].dt.date
            game_df.to_csv(GAMES_CSV, index=False)

            # Refresh dataframes
            game_df = gen_all_game_df()

        flash('Game entry submitted successfully!', 'success')
    except Exception as e:
        flash(f'Error submitting form: {str(e)}', 'error')
        print(f"Submit form error: {e}")

    return redirect(url_for('dashboard'))

@app.route('/halloffame')
@login_required
def halloffame():
    try:
        df = load_games_df(office=get_active_office())
        available_quarters = get_available_quarters(df)
        default_quarter = available_quarters[-1] if available_quarters else 'ALL'
        selected_quarter = request.args.get('quarter', default_quarter)
        if selected_quarter not in list(available_quarters) + ['ALL']:
            selected_quarter = default_quarter

        fame_df = df[df['category'] == 'Fame']
        quarters_data = {}
        for quarter in available_quarters + ['ALL']:
            quarters_data[quarter] = calculate_category_stats(fame_df, 'Fame', quarter)

        # Current quarter info (PST)
        pst = pytz.timezone('US/Pacific')
        now_pst = datetime.datetime.now(pst)
        current_month = now_pst.month
        current_year = now_pst.year

        if current_month <= 3:
            current_q_num = 1
            quarter_end = datetime.datetime(current_year, 3, 31, 23, 59, 59, tzinfo=pst)
        elif current_month <= 6:
            current_q_num = 2
            quarter_end = datetime.datetime(current_year, 6, 30, 23, 59, 59, tzinfo=pst)
        elif current_month <= 9:
            current_q_num = 3
            quarter_end = datetime.datetime(current_year, 9, 30, 23, 59, 59, tzinfo=pst)
        else:
            current_q_num = 4
            quarter_end = datetime.datetime(current_year, 12, 31, 23, 59, 59, tzinfo=pst)

        current_quarter_label = f"{current_year} Q{current_q_num}"
        days_remaining = (quarter_end.date() - now_pst.date()).days

        return render_template('halloffame.html',
                             quarters_data=quarters_data,
                             available_quarters=available_quarters,
                             selected_quarter=selected_quarter,
                             current_quarter_label=current_quarter_label,
                             days_remaining=days_remaining,
                             fame_config=CATEGORY_CONFIG['Fame'])
    except Exception as e:
        flash(f'Error loading hall of fame: {str(e)}', 'error')
        print(f"Hall of fame error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/hallofshame')
@login_required
def hallofshame():
    try:
        df = load_games_df(office=get_active_office())
        available_quarters = get_available_quarters(df)
        default_quarter = available_quarters[-1] if available_quarters else 'ALL'
        selected_quarter = request.args.get('quarter', default_quarter)
        if selected_quarter not in list(available_quarters) + ['ALL']:
            selected_quarter = default_quarter

        shame_df = df[df['category'] == 'Shame']
        quarters_data = {}
        for quarter in available_quarters + ['ALL']:
            quarters_data[quarter] = calculate_category_stats(shame_df, 'Shame', quarter)

        return render_template('hallofshame.html',
                             quarters_data=quarters_data,
                             available_quarters=available_quarters,
                             selected_quarter=selected_quarter,
                             shame_config=CATEGORY_CONFIG['Shame'])
    except Exception as e:
        flash(f'Error loading hall of shame: {str(e)}', 'error')
        print(f"Hall of shame error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/hallofflame')
@login_required
def hallofflame():
    try:
        df = load_games_df(office=get_active_office())
        available_quarters = get_available_quarters(df)
        default_quarter = available_quarters[-1] if available_quarters else 'ALL'
        selected_quarter = request.args.get('quarter', default_quarter)
        if selected_quarter not in list(available_quarters) + ['ALL']:
            selected_quarter = default_quarter

        flame_df = df[df['category'] == 'Flame']
        quarters_data = {}
        for quarter in available_quarters + ['ALL']:
            quarters_data[quarter] = calculate_category_stats(flame_df, 'Flame', quarter)

        return render_template('hallofflame.html',
                             quarters_data=quarters_data,
                             available_quarters=available_quarters,
                             selected_quarter=selected_quarter,
                             flame_config=CATEGORY_CONFIG['Flame'])
    except Exception as e:
        flash(f'Error loading hall of flame: {str(e)}', 'error')
        print(f"Hall of flame error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(error):
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    return "Internal server error", 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)