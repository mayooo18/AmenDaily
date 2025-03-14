from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secretKey = "key"

@app.route('/', methods=['GET', 'POST'])

def login():
    if request.method == 'POST':
        username = request.form["username"].strip()
        if username:
            session["user"] = username
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/home')
def home():
    if "user" in session:
        return redirect(url_for('login')) #if no user returns back to login
    username = session["user"]
    return render_template('index.html', username=username)

@app.route('/logout')
def logout():
    session.pop("user",None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)