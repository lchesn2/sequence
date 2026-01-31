from flask import Flask, flash, session, render_template, redirect, url_for, request, jsonify
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
import datetime
import pytz
import pandas as pd
import secrets
import os
from threading import Lock
from werkzeug.security import generate_password_hash, check_password_hash

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

# User database (in production, use a proper database)
users = {
    'Larah': {'password': 'newton', 'role': 'admin'},
    'John': {'password': 'joh', 'role': 'admin'},
    'Adam': {'password': 'ada', 'role': 'admin'},
    'Behring': {'password': 'beh', 'role': 'admin'},
    'Daniel': {'password': 'dan', 'role': 'admin'},
    'Howard': {'password': 'how', 'role': 'admin'},
    'Jose': {'password': 'jos', 'role': 'user'},
    'Jaemo': {'password': 'jae', 'role': 'user'},
    'Kenji': {'password': 'ken', 'role': 'admin'},
    'Maya': {'password': 'may', 'role': 'admin'},
    'Nishant': {'password': 'nis', 'role': 'admin'},
    'Edward': {'password': 'edw', 'role': 'admin'},
    'Pratishta': {'password': 'pra', 'role': 'admin'},
    'Russell': {'password': 'rus', 'role': 'admin'},
    'Mel': {'password': 'mel', 'role': 'admin'},
    'Choi':{'password': 'cho', 'role':'admin'}
}

def ensure_csv_exists(filename, default_columns):
    """Ensure CSV file exists with proper headers"""
    if not os.path.exists(filename):
        pd.DataFrame(columns=default_columns).to_csv(filename, index=False)

def gen_team_df():
    """Generate team dataframe with error handling, filtered from 2025-06-25 onwards"""
    try:
        ensure_csv_exists('./dailyteams.csv', ['name', 'team', 'date'])
        team_df = pd.read_csv('./dailyteams.csv')
        team_df['date'] = pd.to_datetime(team_df['date'], errors='coerce')

        # Filter data from 2025-06-25 onwards
        cutoff_date = pd.to_datetime('2025-06-25')
        team_df = team_df[team_df['date'] >= cutoff_date]

        return team_df.sort_values(by=['team', 'name'], ascending=[True, True]).reset_index(drop=True)
    except Exception as e:
        print(f"Error loading team data: {e}")
        return pd.DataFrame(columns=['name', 'team', 'date'])

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

def daily_team_score():
    """Calculate daily team scores, filtered from 2025-06-25 onwards"""
    try:
        ensure_csv_exists('./games.csv', ['date', 'time', 'team', 'name', 'card', 'type'])
        game_df = pd.read_csv('./games.csv')
        game_df['date'] = pd.to_datetime(game_df['date'], errors='coerce')

        # Filter data from 2025-06-25 onwards
        cutoff_date = pd.to_datetime('2025-06-25')
        game_df = game_df[game_df['date'] >= cutoff_date]

        score_df = game_df.groupby(['date', 'team']).size().reset_index(name='Score')
        return score_df.sort_values(by=['date', 'Score'], ascending=[False, False]).reset_index(drop=True)
    except Exception as e:
        print(f"Error calculating team scores: {e}")
        return pd.DataFrame(columns=['date', 'team', 'Score'])

def gen_first_player(df):
    """Find the first player based on timestamp"""
    if df.empty:
        return "No player found"

    try:
        # Create a proper copy to avoid SettingWithCopyWarning
        df_copy = df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['date'])
        df_copy['time'] = pd.to_datetime(df_copy['time'], format='%H:%M:%S').dt.time
        df_copy['timestamp'] = df_copy.apply(lambda row: pd.Timestamp.combine(row['date'], row['time']), axis=1)
        df_copy = df_copy.sort_values(by='timestamp')

        if not df_copy.empty:
            return df_copy.iloc[0]['name']
        return "No player found"
    except Exception as e:
        print(f"Error finding first player: {e}")
        return "Error finding player"

# Initialize global dataframes
team_df = gen_team_df()
game_df = gen_all_game_df()
game_df2 = daily_team_score()

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
    global game_df, game_df2, team_df

    try:
        # Get current date in PST timezone
        pst = pytz.timezone('US/Pacific')
        today = pd.to_datetime(datetime.datetime.now(pst).date())

        # Filter today's teams
        team_df2 = team_df[team_df['date'].dt.date == today.date()]
        team_df2 = team_df2.sort_values(by=['name', 'date']).drop_duplicates(subset=['name'], keep='last')
        team_df2 = team_df2.sort_values(by=['team', 'name'], ascending=[True, True]).reset_index(drop=True)

        # Filter today's games
        todays_games = game_df[game_df['date'].dt.date == today.date()][['date', 'time', 'name', 'type']]
        team_count = team_df2['team'].nunique()

        # Convert time column
        if not todays_games.empty:
            todays_games['time'] = pd.to_datetime(todays_games['time'], format='%H:%M:%S').dt.time

        # Find next turn for Sequence games
        sequence_games = game_df[game_df['type'] == 'Sequence']######################################THIS IS STUCK PULLING HOWARD CONSISTENTLY
        next_turn = gen_first_player(sequence_games)

        # Prepare data for templates
        headings = todays_games.columns.tolist()
        data = todays_games.values.tolist()

        if current_user.role == 'admin':
            return render_template('admin.html',
                                 headings=headings,
                                 data=data,
                                 seq=todays_games,
                                 team=team_df2,
                                 nxtTurn=next_turn,
                                 name=current_user.username)
        elif current_user.role == 'user':
            return render_template('user.html',
                                 seq=todays_games[todays_games['type'] == 'Sequence'],
                                 team=team_df2,
                                 ass=todays_games[todays_games['type'] == 'Assist'],
                                 block=todays_games[todays_games['type'] == 'Block'],
                                 name=current_user.username)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        print(f"Dashboard error: {e}")

    return redirect(url_for('login'))

@app.route('/submit_form', methods=['POST'])
@login_required
def submit_form():
    global game_df, game_df2

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
            game_df2 = daily_team_score()

        flash('Game entry submitted successfully!', 'success')
    except Exception as e:
        flash(f'Error submitting form: {str(e)}', 'error')
        print(f"Submit form error: {e}")

    return redirect(url_for('dashboard'))

@app.route('/submit_form_team', methods=['POST'])
@login_required
def submit_form_team():
    global team_df

    try:
        team = request.form.get('team', '')
        date = request.form.get('datetime', '')

        # Validate input
        if not all([team, date]):
            flash('Team and date are required', 'error')# I DON'T THINK MY FLASH IS WORKING
            return redirect(url_for('dashboard'))

        new_row = {
            'name': current_user.username,
            'team': team,
            'date': date
        }

        with lock:
            team_df = pd.concat([team_df, pd.DataFrame([new_row])], ignore_index=True)
            team_df = team_df.sort_values(by=['name', 'date'])
            team_df.to_csv('./dailyteams.csv', index=False)

            # Refresh dataframe
            team_df = gen_team_df()

        flash('Team assignment updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating team: {str(e)}', 'error')
        print(f"Submit team error: {e}")

    return redirect(url_for('dashboard'))

@app.route('/halloffame')
@login_required
def halloffame():
    try:
        ensure_csv_exists('./games.csv', ['date', 'time', 'team', 'name', 'card', 'type'])
        df = pd.read_csv('./games.csv')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

        # Filter data from 2025-06-25 onwards
        cutoff_date = pd.to_datetime('2025-06-25')
        df = df[df['date'] >= cutoff_date]

        # Use only filtered data for hall of fame
        this_period = df[['date', 'time', 'name', 'type']]

        # Calculate statistics for each game type
        block_stats = this_period[this_period['type'] == 'Block'].groupby(['name']).size().reset_index(name='TotalFinishes')
        block_stats = block_stats.sort_values(by=['TotalFinishes'], ascending=[False]).reset_index(drop=True)

        assist_stats = this_period[this_period['type'] == 'Assist'].groupby(['name']).size().reset_index(name='TotalFinishes')
        assist_stats = assist_stats.sort_values(by=['TotalFinishes'], ascending=[False]).reset_index(drop=True)

        sequence_stats = this_period[this_period['type'] == 'Sequence'].groupby(['name']).size().reset_index(name='TotalFinishes')
        sequence_stats = sequence_stats.sort_values(by=['TotalFinishes'], ascending=[False]).reset_index(drop=True)

        return render_template('halloffame.html',
                             dataframe0block=block_stats,
                             dataframe1assist=assist_stats,
                             dataframe2seq=sequence_stats,
                             dataframe3=block_stats)
    except Exception as e:
        flash(f'Error loading hall of fame: {str(e)}', 'error')
        print(f"Hall of fame error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/send-data', methods=['POST'])
@login_required
def send_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        # Process data


        return jsonify({'success': True, 'message': 'Data processed successfully'})
    except Exception as e:
        print(f"Send data error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)