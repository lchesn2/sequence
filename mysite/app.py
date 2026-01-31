from flask import Flask, flash, render_template, redirect, url_for, request
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
import datetime
import pytz
import pandas as pd
import secrets
import os
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Global lock for thread safety
lock = Lock()

class User(UserMixin):
    def __init__(self, username, role):
        self.username = username
        self.role = role

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id, users[user_id]['role'])
    return None

users = {
    'Larah': {'password': 'newton', 'role': 'admin'},
    'John': {'password': 'joh', 'role': 'user'},
    'Adam': {'password': 'ada', 'role': 'user'},
    'Behring': {'password': 'beh', 'role': 'user'},
    'Daniel': {'password': 'dan', 'role': 'user'},
    'Howard': {'password': 'how', 'role': 'user'},
    'Jose': {'password': 'jos', 'role': 'user'},
    'Jaemo': {'password': 'jae', 'role': 'user'},
    'Kenji': {'password': 'ken', 'role': 'admin'},
    'Maya': {'password': 'may', 'role': 'admin'},
    'Nishant': {'password': 'nis', 'role': 'admin'},
    'Edward': {'password': 'edw', 'role': 'admin'},
    'Pratishta': {'password': 'pra', 'role': 'admin'},
    'Russell': {'password': 'rus', 'role': 'user'},
    'Mel': {'password': 'mel', 'role': 'user'},
    'Choi':{'password': 'cho', 'role':'admin'}
}

def ensure_csv_exists(filename, default_columns):
    """Ensure CSV file exists with proper headers"""
    if not os.path.exists(filename):
        pd.DataFrame(columns=default_columns).to_csv(filename, index=False)

def gen_all_game_df():
    """Generate games dataframe with error handling, filtered from 2025-06-25 onwards"""
    try:
        ensure_csv_exists('./games.csv', ['date', 'time', 'team', 'name', 'card', 'type'])
        game_df = pd.read_csv('./games.csv')
        game_df['date'] = pd.to_datetime(game_df['date'], errors='coerce')

        # Filter data from 2025-06-25 onwards
        cutoff_date = pd.to_datetime('2025-06-25')
        game_df = game_df[game_df['date'] >= cutoff_date]

        return game_df.sort_values(by=['type', 'date', 'time'], ascending=[True, False, True]).reset_index(drop=True)
    except Exception as e:
        print(f"Error loading game data: {e}")
        return pd.DataFrame(columns=['date', 'time', 'team', 'name', 'card', 'type'])

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

def load_games_df():
    """Load games CSV, parse dates, apply cutoff filter. Shared by all routes that read historical data."""
    ensure_csv_exists('./games.csv', ['date', 'time', 'team', 'name', 'card', 'type'])
    df = pd.read_csv('./games.csv')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    cutoff_date = pd.to_datetime('2025-06-25')
    return df[df['date'] >= cutoff_date]

def calculate_quarterly_stats(df, quarter='2025Q3'):
    """Calculate statistics for a specific quarter or all time"""
    if df.empty:
        return {
            'block': pd.DataFrame(columns=['name', 'TotalFinishes']),
            'assist': pd.DataFrame(columns=['name', 'TotalFinishes']),
            'sequence': pd.DataFrame(columns=['name', 'TotalFinishes'])
        }
    
    # Filter by quarter if not 'ALL'
    if quarter != 'ALL':
        start_date, end_date = get_quarter_date_range(quarter)
        if start_date and end_date:
            df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        else:
            df_filtered = df
    else:
        df_filtered = df
    
    # Calculate stats for each type
    stats = {}
    for game_type in ['Block', 'Assist', 'Sequence']:
        type_df = df_filtered[df_filtered['type'] == game_type]
        if not type_df.empty:
            type_stats = type_df.groupby(['name']).size().reset_index(name='TotalFinishes')
            type_stats = type_stats.sort_values(by=['TotalFinishes'], ascending=[False]).reset_index(drop=True)
            stats[game_type.lower()] = type_stats
        else:
            stats[game_type.lower()] = pd.DataFrame(columns=['name', 'TotalFinishes'])
    
    return stats

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
            user = User(username, users[username]['role'])
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    global game_df

    try:
        # Get current date in PST timezone
        pst = pytz.timezone('US/Pacific')
        today = pd.to_datetime(datetime.datetime.now(pst).date())

        # Filter today's games
        todays_games = game_df[game_df['date'].dt.date == today.date()][['date', 'name', 'type']]

        # Find the most recent player across all game types
        last_player = get_last_player(game_df)

        data = todays_games.values.tolist()

        if current_user.role == 'admin':
            return render_template('admin.html',
                                 data=data,
                                 nxtTurn=last_player,
                                 name=current_user.username)
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

        new_row = {
            'date': date,
            'time': time,
            'team': '',
            'name': name,
            'card': '',
            'type': game_type
        }

        with lock:
            game_df = pd.concat([game_df, pd.DataFrame([new_row])], ignore_index=True)
            game_df['date'] = pd.to_datetime(game_df['date'])
            game_df['date'] = game_df['date'].dt.date
            game_df.to_csv('games.csv', index=False)

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
        df = load_games_df()
        available_quarters = get_available_quarters(df)
        default_quarter = available_quarters[-1] if available_quarters else '2025Q3'
        selected_quarter = request.args.get('quarter', default_quarter)

        # Calculate stats for all available quarters plus 'ALL'
        quarters_data = {}
        for quarter in available_quarters + ['ALL']:
            quarters_data[quarter] = calculate_quarterly_stats(df, quarter)

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
                             days_remaining=days_remaining)
    except Exception as e:
        flash(f'Error loading hall of fame: {str(e)}', 'error')
        print(f"Hall of fame error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/hallofshame')
@login_required
def hallofshame():
    try:
        df = load_games_df()
        available_quarters = get_available_quarters(df)

        default_quarter = available_quarters[-1] if available_quarters else '2025Q3'
        selected_quarter = request.args.get('quarter', default_quarter)

        return render_template('hallofshame.html',
                             available_quarters=available_quarters,
                             selected_quarter=selected_quarter)
    except Exception as e:
        flash(f'Error loading hall of shame: {str(e)}', 'error')
        print(f"Hall of shame error: {e}")
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