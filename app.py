from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os , json, random, requests, uuid
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "key"

USER_DATA_FILE = "users.json"

if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    """Load user data from JSON file."""
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    """Save user data to JSON file."""
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)


@app.route("/delete_entry", methods=["POST"])
def delete_entry():
    if "user" not in session:  
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    data = request.json
    entry_id = data.get("entry_id")

    users = load_users()  # Load the JSON data
    if username in users:
        updated_journal = [entry for entry in users[username]["journal"] if entry["id"] != entry_id]
        users[username]["journal"] = updated_journal
        save_users(users)  # Ensure it's saved

        return jsonify({"message": "Entry deleted successfully"})

    return jsonify({"error": "User not found"}), 404

@app.route("/edit_entry", methods=["POST"])
def edit_entry():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    data = request.json
    entry_id = data.get("entry_id")
    new_text = data.get("new_text")

    users = load_users()
    if username in users:
        for entry in users[username].get("journal", []):
            if entry["id"] == entry_id:
                entry["journal"] = new_text
                entry["edited_at"] = datetime.now().isoformat()  # Optional: Track edits
                save_users(users)
                return jsonify({"message": "Entry updated successfully"})
    return jsonify({"error": "Entry not found"}), 404

def get_daily_scripture():
    try:
        # Path to the JSON file containing the entire Bible
        bible_path = os.path.join(os.getcwd(), 'json', 'en_bbe.json')

        # Load the Bible's JSON data with utf-8-sig encoding to handle BOM issue
        with open(bible_path, 'r', encoding="utf-8-sig") as file:
            bible_data = json.load(file)

        print("Loaded JSON successfully!")  # Debugging step

        # Ensure the JSON data is a list and has content
        if not isinstance(bible_data, list) or not bible_data:
            return "Error: JSON structure is incorrect or empty."

        # Seed the random number generator with today's date
        random.seed(date.today().toordinal())

        # Choose a random book
        random_book = random.choice(bible_data)

        # **FIX: The book name is stored under "name", not "book"**
        if "name" not in random_book or "chapters" not in random_book:
            return "Error: JSON format missing 'name' or 'chapters' keys."

        # Extract book name
        book_name = random_book["name"]

        # Ensure chapters exist
        if not random_book["chapters"]:
            return f"Error: No chapters available for {book_name}."

        # Choose a random chapter
        random_chapter_index = random.randint(0, len(random_book["chapters"]) - 1)
        chapter = random_book["chapters"][random_chapter_index]

        print(f"Chosen Book: {book_name}, Chapter: {random_chapter_index + 1}")  # Debugging step

        # Ensure the chapter has verses
        if not isinstance(chapter, list) or not chapter:
            return f"Error: No verses available for {book_name} Chapter {random_chapter_index + 1}."

        # Choose a random verse
        random_verse_index = random.randint(0, len(chapter) - 1)
        verse_text = chapter[random_verse_index]

        print(f"Chosen Verse: {random_verse_index + 1}")  # Debugging step

        # Construct the reference
        chapter_number = random_chapter_index + 1
        verse_number = random_verse_index + 1
        reference = f"{book_name} {chapter_number}:{verse_number}"

        return f"{reference} - {verse_text}"

    except Exception as e:
        print(f"Error retrieving daily scripture: {e}")  # Print error in console
        return f"Error: {e}"  # Show error on screen for debugging

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
        return redirect(url_for('login')) #if no user returns back to login
    username = session["user"]
    users = load_users()
    user_data = users.get(username, {"journal": [], "bookmarks": []})
    scripture = get_daily_scripture()
    return render_template('index.html', username=username, scripture=scripture, user_data=user_data)


@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for('login'))

@app.route('/journal', methods=["POST"])
def save_journal():
    """Save a journal entry for the logged-in user with the date."""
    if "user" not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session["user"]
    journal_entry = request.form.get("entry").strip()  # Clean input

    if journal_entry:
        users[username]["journal"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "journal": journal_entry, # Updated key from 'text' to 'journal'
            "id": str(uuid.uuid4())
        })
        save_users(users)

    return redirect(url_for('home'))



@app.route('/bookmark', methods=["POST"])
def bookmark_prayer():
    """Bookmark a prayer for the logged-in user."""
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
    data = request.json
    index = data.get("index")

    users = load_users()
    if username in users:
        try:
            users[username]["bookmarks"].pop(index - 1)  # Remove by index (1-based index)
            save_users(users)
            return jsonify({"message": "Bookmark deleted successfully"})
        except IndexError:
            return jsonify({"error": "Invalid bookmark index"}), 400

    return jsonify({"error": "User not found"}), 404

@app.route("/edit_bookmark", methods=["POST"])
def edit_bookmark():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    username = session["user"]
    data = request.json
    index = data.get("index")
    new_text = data.get("new_text")

    users = load_users()
    if username in users:
        try:
            users[username]["bookmarks"][index - 1] = new_text  # Update bookmark
            save_users(users)
            return jsonify({"message": "Bookmark updated successfully"})
        except IndexError:
            return jsonify({"error": "Invalid bookmark index"}), 400

    return jsonify({"error": "User not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)