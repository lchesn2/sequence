from flask import Flask, flash,session,render_template, redirect, url_for, request, jsonify,flash
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask_bcrypt import Bcrypt
import datetime
import time
import pandas as pd
from flask_login import UserMixin
import secrets
from datetime import datetime
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

bcrypt = Bcrypt(app)

class User(UserMixin):
    def __init__(self, username,role):
        self.username = username
        self.role = users[username]['role']

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id,users[user_id]['role'])
    return None

@app.route('/')
def start():
    return render_template('login.html')

users = {
    'Larah': {'password': 'newton', 'role': 'admin'},
    'Andy': {'password': 'and', 'role': 'user'},
    'Behring':{'password':'beh','role':'admin'},
    'Daniel':{'password':'dan','role':'user'},
    'Howard':{'password':'how','role':'user'},
    'Jose':{'password':'jos','role':'user'},
    'Jaemo':{'password':'jae','role':'user'},
    'Kenji':{'password':'ken','role':'admin'},
    'Maya':{'password':'may','role':'admin'},
    'Nishant':{'password':'nis','role':'admin'},
    'Paul':{'password':'pau','role':'user'},
    'Poonam':{'password':'poo','role':'admin'},
    'Russell':{'password':'rus','role':'user'}

}

def gen_team_df():
    team_df=pd.read_csv('./dailyteams.csv')
    today=pd.to_datetime(datetime.now().date())
    team_df['date'] = pd.to_datetime(team_df['date'], errors='coerce') #, format='mixed'
    return team_df.sort_values(by=['team','name'],ascending=[True,True]).reset_index(drop=True)

def gen_all_game_df():
    game_df=pd.read_csv('./games.csv').sort_values(by=['type','date','time'],ascending=[True,False,True]).reset_index(drop=True)
    game_df['date']=pd.to_datetime(game_df['date'], errors='coerce')
    return game_df

def daily_team_score():
    game_df2=pd.read_csv('./games.csv')
    # admin needs to set some parameter
    game_df2['date']=pd.to_datetime(game_df2['date'], errors='coerce')
    game_df2=game_df2.groupby(['date','team']).size().reset_index(name='Score').sort_values(by=['date','Score'],ascending=[False,False]).reset_index(drop=True)

    return game_df2


def gen_first_player(df):
    df['date'] = pd.to_datetime(df['date'])

    # Ensure 'timecolumn' is in datetime format (only time part)
    df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.time

    # Combine date and time into a single datetime column for sorting
    df['timest'] = df.apply(lambda row: pd.Timestamp.combine(row['date'], row['time']), axis=1)

    # Sort the DataFrame by the combined datetime column
    df = df.sort_values(by='timest')

    # Select the row with the maximum datetime
    max_datetime_row = df.loc[df['timest'].idxmax()]
    df.drop('timest',axis=1)
    return max_datetime_row['name']

#df = pd.read_csv('./games.csv')
team_df=gen_team_df()
game_df=gen_all_game_df()
game_df2= daily_team_score()

lock=Lock()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and password==users[username]['password']:
            user = User(username,users[username]['role'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html')
    return render_template('login.html')


def cond_divide(value,team_c):

    return value//2 if team_c%2==0 else value//1

@app.route('/dashboard')
@login_required
def dashboard():
    global game_df,game_df2,team_df
    today=pd.to_datetime(datetime.now().date())
    # Today Your Teams Are (df0)
    # filter by date, drop duplicates if multiple entries in one day since sort by date only latest is kept- this is for instances if player needs to change teams-- sort again so that df is clean
    team_df2=team_df[team_df['date'].dt.date==today.date()].sort_values(by=['name','date']).drop_duplicates(subset=['name'], keep='last').sort_values(by=['team','name'],ascending=[True,True]).reset_index(drop=True)

    # Win By Win (df1)
    game_df2 =game_df[game_df['date'].dt.date==today.date()]
    team_nr=team_df2['team'].nunique()
    print(team_nr)


    #Today's Score (df2)
    score_df = game_df2.groupby('team').size().reset_index(name='Score')
    if len(score_df):
        score_df['Score'] = score_df.apply(lambda row:cond_divide(row['Score'],team_nr),axis=1)

    # Ensure the 'timecolumn' is in datetime format (only time part)
    game_df2['time'] = pd.to_datetime(game_df2['time'], format='%H:%M:%S').dt.time

    # Select the row with the maximum time
    #df00= game_df.sort_values(by=['date','time'],ascending=[False,False])
    df00 =  game_df[game_df['type']=='Sequence'] #.sort_values(by=['date','time'],ascending=[False,False]).head(1)
    nxtTurn = gen_first_player(df00)

    # Convert DataFrame to list of lists
    headings = game_df2.columns.tolist()
    data = game_df2.values.tolist()

    if current_user.role == 'admin':
        return render_template('admin.html',headings=headings,data=data,seq=game_df2,team=team_df2,nxtTurn=nxtTurn,name=current_user.username)
    elif current_user.role == 'user':
        return render_template('user.html',seq=game_df2[game_df2['type']=='Sequence'],team=team_df2,ass=game_df2[game_df2['type']=='Assist'] ,block=game_df2[game_df2['type']=='Block'],name=current_user.username)
    return redirect(url_for('login'))
# Combine date and time into a single datetime column for sorting
#df['datetime'] = df.apply(lambda row: pd.datetime.combine(row['datecolumn'], row['timecolumn']), axis=1)

# Sort the DataFrame by the combined datetime column
#df = df.sort_values(by='datetime')

# Select the row with the maximum datetime
#max_datetime_row = df.loc[df['datetime'].idxmax()]


@app.route('/submit_form', methods=['POST', 'GET'])
@login_required
def submit_form():
    date=request.form.get('date','')
    time=request.form.get('time','')
    #team=request.form.get('teamwin','')
    name=request.form.get('name','')
    #card=request.form.get('card','')
    type =request.form.get('type','')

    new_row={'date':date,'time':time,'team':'','name':name,'card':'','type':type}
    global game_df,game_df2

    with lock:
        game_df.loc[len(game_df)]=new_row

    game_df['date'] = pd.to_datetime(game_df['date']) # what does this do? puts to date ome type of casting

    game_df['date'] = game_df['date'].dt.date # what about this?

    game_df.to_csv('games.csv', index=False)
    game_df=gen_all_game_df()
    game_df2=daily_team_score()

    return redirect(url_for('dashboard'))

@app.route('/submit_form_team',methods=['POST','GET'])
@login_required

def submit_form_team():
    team=request.form.get('team','')
    date=request.form.get('datetime','')
    new_row={'name': current_user.username,'team':team,'date':date}

    global team_df
    with lock:
        team_df.loc[len(team_df)]=new_row

    team_df.sort_values(by=['name', 'date'], inplace=True)
    team_df.to_csv('./dailyteams.csv',index=False)


    team_df=gen_team_df()
    return redirect(url_for('dashboard'))




@app.route('/halloffame')
@login_required
def halloffame():
    df = pd.read_csv('./games.csv')
    current_year = datetime.now().year
    #df_filtered = df[df['date'].dt.year == current_year]

    #df_filtered0=pd.to_datetime(df['date'], errors='coerce')
    print('LADYYYYYYYYYYYYY GAGAAAAAAAAAAA')
    print()
    #print(df_filtered0.dtypes)
    print()
    print()
    #df_filtered = df_filtered0[df_filtered0['date'].dt.year == current_year]

    df0=df[df['type']=='Block'].groupby(['name']).size().reset_index(name='TotalFinishes').sort_values(by=['TotalFinishes'],ascending=[False]).reset_index(drop=True)
    #print(df0.head())
    print(df0.columns)
    print()
    print()
    df1=df[df['type']=='Assist'].groupby(['name']).size().reset_index(name='TotalFinishes').sort_values(by=['TotalFinishes'],ascending=[False]).reset_index(drop=True)
    #print(df1.head())

    df2=df[df['type']=='Sequence'].groupby(['name']).size().reset_index(name='TotalFinishes').sort_values(by=['TotalFinishes'],ascending=[False]).reset_index(drop=True)
    print(df2.head())
    df3= pd.read_csv('./games.csv').groupby(['card']).size().reset_index(name='TotalFinishes').sort_values(by=['TotalFinishes'],ascending=[False]).reset_index(drop=True)
    #print(df3.head())
    return render_template('halloffame.html',dataframe0block=df0,dataframe1assist=df1,dataframe2seq=df2,dataframe3=df3.loc[df3['TotalFinishes']>5])



def admin_update_data(data_to_process):

    global game_df
    date=data_to_process['date']
    time=data_to_process['time']
    #team=data_to_process['team']
    name=data_to_process['name']
    #card=data_to_process['card']
    type=data_to_process['type']

    new_row={'date':date,
             'time':time,
             'name':name,
             'card':'',
             'type':type
             }

    # Locate the specific row using 'date' and 'time' as the composite key
    mask = (game_df['date'] == new_row['date']) & (game_df['time'] == new_row['time'])

    print(new_row)
    # Check if the row exists
    # if mask.any():
    #     # Overwrite the row with new data
    #     game_df.loc[mask, :] = pd.DataFrame([new_row])


@app.route('/send-data', methods=['POST'])
@login_required
def send_data():
    print('yo diggity')

    data = request.json
    admin_update_data(data)
    return render_template('players.html')


    #team_nr=team_df2['team'].nunique()
    #score_df['Score'] = score_df.apply(lambda row:cond_divide(row['Score'],team_nr),axis=1)
    return render_template('halloffame.html',dataframe0block=df0,dataframe1assist=df1,dataframe2seq=df2,dataframe3=df3.loc[df3['TotalFinishes']>5])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)


'''
1. historical data is removed in teams
'''