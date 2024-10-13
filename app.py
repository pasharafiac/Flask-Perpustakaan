from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, timedelta, datetime
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/', methods=['GET'])
def index():
    books = json.load(open('database/books/books.json'))
    return render_template('index.html', books=books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Load the existing users from the JSON file
        users_file = 'database/users/users.json'
        users_registered = json.load(open(users_file))
        
        # Periksa apakah username ada dalam daftar pengguna terdaftar
        if username in users_registered:
            # Jika username ada, periksa apakah password benar
            if users_registered[username]['password'] == password:
                # Jika password benar, simpan data pengguna dalam sesi
                session['user'] = users_registered[username]
                # Arahkan ke halaman dashboard
                return redirect(url_for('dashboard'))
            else:
                # Jika password salah, tampilkan halaman login dengan pesan kesalahan
                return render_template('login.html', password_incorrect=True)
        else:
            # Jika username tidak ditemukan, tampilkan halaman login dengan pesan kesalahan
            return render_template('login.html', username_not_found=True)
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname').title()
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Load the existing users from the JSON file
        users_file = 'database/users/users.json'
        users_registered = json.load(open(users_file)).keys()
        
        if username in users_registered:
            return render_template('register.html', username_taken=True)
        
        user_regist_data = {
            "fullname": fullname,
            "username": username,
            "email": email,
            "password": password,
            "role": "user"
        }

        # Load existing data
        with open(users_file, 'r') as f:
            existing_data = json.load(f)
        
        # Append new user data
        existing_data[username] = user_regist_data
        
        # Write updated data back to file
        with open(users_file, 'w') as f:
            json.dump(existing_data, f, indent=4)

        # store user regist data to session
        session['user'] = user_regist_data

        return redirect(url_for('dashboard'))
    
    return render_template('register.html', username_taken=False)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # If user is logged in, render the dashboard
    books = json.load(open('database/books/books.json'))
    return render_template('dashboard.html', username=session['user'], books=books)

@app.route('/history_transaction', methods=['GET', 'POST'])
def history_transaction():
    user = request.args.get('user')

    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # cek method post
    if request.method == 'POST':
        # Memuat data transaksi
        with open('database/books/transaction.json', 'r') as f:
            transactions = json.load(f)
        
        # Mencari transaksi yang akan diperbarui
        for transaction in transactions['user_records_transaction']:
            if transaction['account_info']['username'] == session['user']['username'] and transaction['status'] == 'Dipinjam':
                # Memperbarui status transaksi
                transaction['status'] = 'Dikembalikan'
                transaction['return_date'] = datetime.now().strftime('%Y-%m-%d')
                
                # Memperbarui ketersediaan buku
                with open('database/books/books.json', 'r') as f:
                    books = json.load(f)
                
                category = transaction['category'].lower()
                for book in books[category]:
                    if book['id'] == transaction['book_id']:
                        book['available'] = True
                        break
                
                # Menyimpan data buku yang diperbarui
                with open('database/books/books.json', 'w') as f:
                    json.dump(books, f, indent=4)
                
                break
        
        # Menyimpan data transaksi yang diperbarui
        with open('database/books/transaction.json', 'w') as f:
            json.dump(transactions, f, indent=4)
        
        # Mengarahkan kembali ke halaman riwayat
        return redirect(url_for('history_transaction', user=session['user']['username']))

    with open('database/books/transaction.json', 'r') as f:
        all_transactions = json.load(f)
        
        if session['user']['role'] == 'admin':
            transactions = all_transactions
        else:
            transactions = {
                'user_records_transaction': [
                    transaction for transaction in all_transactions['user_records_transaction']
                    if transaction['account_info']['username'] == session['user']['username']
                ]
            }

    return render_template('history_transaction.html', user=user, transactions=transactions)

@app.route('/borrow_book')
def borrow_book():
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Load book data from JSON file
    with open('database/books/books.json', 'r') as f:
        books = json.load(f)
    
    # Pass the book data to the template
    selected_category = request.args.get('category')
    
    return render_template('borrow_book.html', books=books, selected_category=selected_category)

@app.route('/book_checkout', methods=['GET', 'POST'])
def book_checkout():
    # Memeriksa apakah pengguna sudah login
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Mengambil data dari form
        borrow_date = datetime.strptime(request.form.get('borrowDate'), '%Y-%m-%d')
        return_date = datetime.strptime(request.form.get('returnDate'), '%Y-%m-%d')

        # Memuat data transaksi dari file JSON
        with open('database/books/transaction.json', 'r') as f:
            transactions = json.load(f)
        
        # Memuat data buku dari file JSON
        with open('database/books/books.json', 'r') as f:
            books = json.load(f)
        
        # Mencari buku dalam kategori yang ditentukan
        book = next((b for b in books[request.args.get('category')] if b['id'] == request.args.get('book_id')), None)
        
        if book: 
            # Membuat record transaksi user baru
            new_user_transaction = {
                "account_info": session['user'],
                "book_id": request.args.get('book_id'),
                "book_title": book['title'],
                "category": request.args.get('category'),
                "borrow_date": borrow_date.strftime('%Y-%m-%d'),
                "return_date": return_date.strftime('%Y-%m-%d'),
                "status": "Dipinjam",
                "transaction_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Menambahkan transaksi user baru ke dalam user_records_transaction
            transactions['user_records_transaction'].append(new_user_transaction)
            
            # Mengubah status ketersediaan buku menjadi false
            book['available'] = False
            
            # Menyimpan perubahan pada file transaction.json
            with open('database/books/transaction.json', 'w') as f:
                json.dump(transactions, f, indent=4)
            
            # Menyimpan perubahan pada file books.json
            with open('database/books/books.json', 'w') as f:
                json.dump(books, f, indent=4)
            
            # Redirect ke halaman history transaction
            return redirect(url_for('history_transaction', user=session['user']['username']))
        
        # Jika buku tidak ditemukan, kembali ke halaman peminjaman
        return redirect(url_for('borrow_book'))
    
    # Mengambil ID buku dan kategori dari parameter URL
    book_id = request.args.get('book_id')
    category = request.args.get('category')

    # Memeriksa apakah parameter book_id dan category ada di URL
    if not book_id or not category:
        return redirect(url_for('borrow_book'))
    
    # Memuat data buku dari file JSON
    with open('database/books/books.json', 'r') as f:
        books = json.load(f)
    
    # Mencari buku dalam kategori yang ditentukan
    book = next((b for b in books[category] if b['id'] == book_id), None)

    # Jika buku tidak ditemukan, kembali ke halaman peminjaman
    if not book:
        return redirect(url_for('borrow_book'))
    
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Mengirim data buku ke template
    return render_template('book_checkout.html', book_id=book_id, category=category, book=book, today=today, tomorrow=tomorrow)

@app.route('/logout')
def logout():
    # Clear the user's session
    session.clear()
    # Redirect to the login page
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
