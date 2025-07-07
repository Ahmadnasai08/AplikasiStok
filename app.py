from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Membuat filter kustom untuk pemisah ribuan
@app.template_filter('number_format')
def number_format(value):
    """Membuat format angka dengan pemisah ribuan."""
    try:
        return '{:,.0f}'.format(value)
    except (ValueError, TypeError):
        return value

# Fungsi untuk menghubungkan ke database
def get_db_connection():
    conn = sqlite3.connect('stok.db')
    conn.row_factory = sqlite3.Row
    return conn

# Fungsi untuk inisialisasi database (buat tabel jika belum ada)
def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS produk (
        id INTEGER PRIMARY KEY,
        produk TEXT NOT NULL,
        harga_satuan INTEGER NOT NULL
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS stok_masuk (
        id INTEGER PRIMARY KEY,
        produk_id INTEGER NOT NULL,
        jumlah INTEGER NOT NULL,
        FOREIGN KEY (produk_id) REFERENCES produk(id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS stok_terjual (
        id INTEGER PRIMARY KEY,
        produk_id INTEGER NOT NULL,
        jumlah INTEGER NOT NULL,
        FOREIGN KEY (produk_id) REFERENCES produk(id)
    )
    ''')

    conn.commit()
    conn.close()

# Fungsi untuk halaman utama (Dashboard)
@app.route('/')
def home():
    conn = get_db_connection()
    c = conn.cursor()

    # Mengambil total stok masuk
    c.execute('SELECT SUM(jumlah) FROM stok_masuk')
    stok_masuk = c.fetchone()[0] or 0

    # Mengambil total stok terjual
    c.execute('SELECT SUM(jumlah) FROM stok_terjual')
    stok_terjual = c.fetchone()[0] or 0

    # Menghitung stok tersedia
    c.execute('''
        SELECT SUM(stok_masuk.jumlah) - IFNULL(SUM(stok_terjual.jumlah), 0)
        FROM stok_masuk
        LEFT JOIN stok_terjual ON stok_masuk.produk_id = stok_terjual.produk_id
    ''')
    stok_tersedia = c.fetchone()[0] or 0

    # Menghitung total pendapatan
    c.execute('''
        SELECT SUM(stok_terjual.jumlah * produk.harga_satuan) 
        FROM stok_terjual 
        JOIN produk ON stok_terjual.produk_id = produk.id
    ''')
    total_pendapatan = c.fetchone()[0] or 0
    total_pendapatan = "{:,.0f}".format(total_pendapatan)

    conn.close()

    return render_template('index.html', stok_masuk=stok_masuk, stok_terjual=stok_terjual, stok_tersedia=stok_tersedia, total_pendapatan=total_pendapatan)

# Fungsi untuk menambah produk baru
@app.route('/tambah_produk', methods=['GET', 'POST'])
def tambah_produk():
    if request.method == 'POST':
        produk = request.form['produk']
        harga_satuan = request.form['harga_satuan']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO produk (produk, harga_satuan) VALUES (?, ?)', (produk, harga_satuan))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))  # Kembali ke dashboard setelah data disimpan

    return render_template('tambah_produk.html')

# Fungsi untuk menampilkan daftar produk
@app.route('/daftar_produk')
def daftar_produk():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM produk')
    produk = c.fetchall()
    conn.close()

    return render_template('daftar_produk.html', produk=produk)

# Fungsi untuk melihat laporan penjualan
@app.route('/sales_report')
def sales_report():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Query untuk menghitung total terjual dan total pendapatan per produk
    c.execute('''
        SELECT produk.produk, 
               SUM(COALESCE(stok_terjual.jumlah, 0)) AS total_terjual, 
               SUM(COALESCE(stok_terjual.jumlah * produk.harga_satuan, 0)) AS total_pendapatan,
               produk.harga_satuan
        FROM produk
        LEFT JOIN stok_terjual ON stok_terjual.produk_id = produk.id
        GROUP BY produk.id
    ''')
    sales_data = c.fetchall()

    conn.close()

    # Kirimkan data penjualan ke template
    return render_template('sales_report.html', sales_data=sales_data)

# Fungsi untuk entri penjualan
@app.route('/sales_entry', methods=['GET', 'POST'])
def sales_entry():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM produk')
    produk_tersedia = c.fetchall()
    conn.close()

    if request.method == 'POST':
        produk_id = request.form['produk']
        jumlah = request.form['jumlah']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO stok_terjual (produk_id, jumlah) VALUES (?, ?)', (produk_id, jumlah))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('sales_entry.html', produk_tersedia=produk_tersedia)

# Fungsi untuk entri stok
@app.route('/stock_entry', methods=['GET', 'POST'])
def stock_entry():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM produk')
    produk_tersedia = c.fetchall()
    conn.close()

    if request.method == 'POST':
        produk_id = request.form['produk']
        jumlah = request.form['jumlah']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO stok_masuk (produk_id, jumlah) VALUES (?, ?)', (produk_id, jumlah))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('stock_entry.html', produk_tersedia=produk_tersedia)

# Fungsi untuk melihat stok yang tersedia
@app.route('/available_stock')
def available_stock():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT produk.produk, 
               SUM(stok_masuk.jumlah) - IFNULL(SUM(stok_terjual.jumlah), 0) AS stok_tersedia
        FROM produk
        LEFT JOIN stok_masuk ON produk.id = stok_masuk.produk_id
        LEFT JOIN stok_terjual ON produk.id = stok_terjual.produk_id
        GROUP BY produk.id
    ''')
    available_stocks = c.fetchall()
    conn.close()

    return render_template('available_stock.html', available_stocks=available_stocks)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
