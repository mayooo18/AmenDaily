from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os, json, random, uuid
from datetime import date, datetime
import requests

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
HUGGINGFACE_API_KEY = os.environ.get("HF_API_KEY")

headers = {
    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
}

def get_ai_generated_prayer(mood, name):
    prompt = (
        f"Write a short, sincere prayer for someone named {name} who is feeling {mood}. "
        "Make it gentle and encouraging. Keep it under 60 words. "
    )

    try:
        response = requests.post(
            HUGGINGFACE_API_URL,
            headers=headers,
            json={"inputs": prompt}
        )
        result = response.json()
        full_text = result[0]["generated_text"]
        prayer_only = full_text.split("Keep it under 60 words.")[-1].strip()
        return prayer_only

    except Exception as e:
        print("Hugging Face Error:", e)
        if 'response' in locals():
            print("Response status:", response.status_code)
            print("Response content:", response.text)
        else:
            print("No response object.")
        return "Dear God, meet me where I am today."




app = Flask(__name__)
app.secret_key = "key"
HUGGINGFACE_API_KEY = os.environ.get("HF_API_KEY")

USER_DATA_FILE = "users.json"

if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form["username"].strip()
        pin = request.form["pin"].strip()

        if username and pin:
            session["user"] = username
            users = load_users()

            if username not in users:
                users[username] = {"pin": pin, "journal": [], "bookmarks": []}
                save_users(users)

            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/home')
def home():
    if "user" not in session:
        return redirect(url_for('login'))

    username = session["user"]
    users = load_users()
    user_data = users.get(username, {"journal": [], "bookmarks": []})
    scripture = get_daily_scripture()

    return render_template('index.html', username=username, scripture=scripture, user_data=user_data)

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for('login'))

@app.route('/select_mood', methods=['POST'])
def select_mood():
    if "user" not in session:
        return redirect(url_for('login'))

    mood = request.form.get('mood')
    if not mood:
        return redirect(url_for('home'))

    username = session["user"]
    users = load_users()
    user = users.get(username)

    today_str = str(date.today())
    prayer = get_ai_generated_prayer(mood, username)


    entry = {
    "date": today_str,
    "journal": prayer,
    "mood": mood,
    "type": "mood_prayer",
    "id": str(uuid.uuid4())
}

    user['journal'].append(entry)
    save_users(users)

    scripture = get_daily_scripture()
    return render_template('index.html', username=username, scripture=scripture, user_data=user, mood_prayer=entry)

@app.route('/journal', methods=["POST"])
def save_journal():
    if "user" not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session["user"]
    journal_entry = request.form.get("entry").strip()

    if journal_entry:
        users[username]["journal"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "journal": journal_entry,
            "id": str(uuid.uuid4())
        })
        save_users(users)

    return redirect(url_for('home'))

@app.route('/bookmark', methods=["POST"])
def bookmark_prayer():
    if "user" not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session["user"]
    prayer = request.form.get("prayer")

    if prayer and prayer not in users[username]["bookmarks"]:
        users[username]["bookmarks"].append(prayer)
        save_users(users)

    return redirect(url_for('home'))

@app.route("/delete_bookmark", methods=["POST"])
def delete_bookmark():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    index = request.json.get("index")

    users = load_users()
    try:
        users[username]["bookmarks"].pop(index - 1)
        save_users(users)
        return jsonify({"message": "Bookmark deleted successfully"})
    except (IndexError, KeyError):
        return jsonify({"error": "Invalid bookmark index"}), 400

@app.route("/edit_bookmark", methods=["POST"])
def edit_bookmark():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    index = request.json.get("index")
    new_text = request.json.get("new_text")

    users = load_users()
    try:
        users[username]["bookmarks"][index - 1] = new_text
        save_users(users)
        return jsonify({"message": "Bookmark updated successfully"})
    except (IndexError, KeyError):
        return jsonify({"error": "Invalid bookmark index"}), 400

@app.route("/delete_entry", methods=["POST"])
def delete_entry():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    entry_id = request.json.get("entry_id")

    users = load_users()
    users[username]["journal"] = [entry for entry in users[username]["journal"] if entry["id"] != entry_id]
    save_users(users)

    return jsonify({"message": "Entry deleted successfully"})

@app.route("/edit_entry", methods=["POST"])
def edit_entry():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    entry_id = request.json.get("entry_id")
    new_text = request.json.get("new_text")

    users = load_users()
    for entry in users[username].get("journal", []):
        if entry["id"] == entry_id:
            entry["journal"] = new_text
            entry["edited_at"] = datetime.now().isoformat()
            save_users(users)
            return jsonify({"message": "Entry updated successfully"})

    return jsonify({"error": "Entry not found"}), 404

def get_daily_scripture():
    try:
        bible_path = os.path.join(os.getcwd(), 'json', 'en_bbe.json')
        with open(bible_path, 'r', encoding="utf-8-sig") as file:
            bible_data = json.load(file)

        random.seed(date.today().toordinal())
        book = random.choice(bible_data)
        book_name = book.get("name")
        chapters = book.get("chapters", [])
        chapter_index = random.randint(0, len(chapters) - 1)
        chapter = chapters[chapter_index]
        verse_index = random.randint(0, len(chapter) - 1)
        verse_text = chapter[verse_index]
        return f"{book_name} {chapter_index + 1}:{verse_index + 1} - {verse_text}"
    except Exception as e:
        return f"Scripture error: {e}"

if __name__ == '__main__':
    app.run(debug=True)
