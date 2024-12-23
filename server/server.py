from flask import *
import psycopg2
from werkzeug.security import *
import csv
import io

app = Flask(__name__)

app.secret_key = 'abobaBOOBA' 
app.config['SESSION_TYPE'] = 'filesystem'

DB_CONFIG = {
    'dbname': 'store',
    'user': 'postgres',
    'password': '123',
    'host': 'db',
    'port': 5432
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def login_page():
    if 'username' in session:
        role = session.get('role_id')
        if role == 1:
            return redirect(url_for('admin_page'))
        
    return send_from_directory('static', 'login.html')

@app.route('/register')
def register_page():
    return send_from_directory('static', 'register.html')

@app.route('/admin')
def admin_page():
    if 'username' in session and session.get('role_id') == 1:
        return render_template('admin.html', username=session.get('username'))
    return redirect(url_for('login_page'))

@app.route('/user')
def user_page():
    if 'username' in session and session.get('role_id') == 1:
        return send_from_directory('static', 'userpage.html')
    return redirect(url_for('login_page'))

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Имя пользователя и пароль обязательны.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT password_hash, role_id FROM users WHERE username = %s", (username,))
        result = cur.fetchone()

        if result and check_password_hash(result[0], password):
            role_id = result[1]
            session['username'] = username
            session['role_id'] = role_id

            if role_id ==1:
                return jsonify({'success': True, 'redirect': '/admin'})
            elif role_id == 1:
                return jsonify({'success': True, 'redirect': '/user'})
            else:
                return jsonify({'success': False, 'message': 'Нет доступа.'})
        else:
            return jsonify({'success': False, 'message': 'Неверное имя пользователя или пароль.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера'})
    finally:
        if conn:
            conn.close()


# Обработка регистрации
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Имя пользователя и пароль обязательны.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверяем, существует ли пользователь
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Пользователь уже существует.'})

        # Хэшируем пароль
        hashed_password = generate_password_hash(password)

        # Добавляем пользователя с ролью role_id = 777
        cur.execute(
            "INSERT INTO users (username, password_hash, role_id) VALUES (%s, %s, %s)",
            (username, hashed_password, 1)
        )
        conn.commit()

        return jsonify({'success': True, 'message': 'Пользователь успешно зарегистрирован.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера'})
    finally:
        if conn:
            conn.close()

# Выход из системы
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/products', methods=['GET'])
def get_products():
    try:
        # Получаем параметры фильтрации
        name = request.args.get('name', '').strip()
        city = request.args.get('city', '').strip()
        store = request.args.get('store', '').strip()
        quantity_min = request.args.get('quantityMin')
        quantity_max = request.args.get('quantityMax')
        price_min = request.args.get('priceMin')
        price_max = request.args.get('priceMax')

        query = "SELECT id, city, store, name, quantity, purchase_price FROM products WHERE 1=1"
        params = []

        if name:
            query += " AND name ILIKE %s"
            params.append(f"%{name}%")
        if city:
            query += " AND city = %s"
            params.append(city)
        if store:
            query += " AND store = %s"
            params.append(store)
        if quantity_min:
            query += " AND quantity >= %s"
            params.append(int(quantity_min))
        if quantity_max:
            query += " AND quantity <= %s"
            params.append(int(quantity_max))
        if price_min:
            query += " AND purchase_price >= %s"
            params.append(float(price_min))
        if price_max:
            query += " AND purchase_price <= %s"
            params.append(float(price_max))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        products = cur.fetchall()

        return jsonify([
            {
                'id': p[0],
                'city': p[1],
                'store': p[2],
                'name': p[3],
                'quantity': p[4],
                'price': p[5]
            }
            for p in products
        ])
    finally:
        conn.close()

@app.route('/store_locations', methods=['GET'])
def get_store_locations():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Извлекаем данные из таблицы store_locations
        cur.execute("SELECT city, store FROM store_locations")
        rows = cur.fetchall()

        # Преобразуем данные в формат { "город": [номера складов] }
        store_locations = {}
        for city, store_number in rows:
            if city not in store_locations:
                store_locations[city] = []
            store_locations[city].append(store_number)

        return jsonify(store_locations)
    finally:
        conn.close()

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json
    name = data.get('name')
    quantity = data.get('quantity')
    price = data.get('price')
    city = data.get('city')
    store = data.get('store')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, quantity, purchase_price, city, store) VALUES (%s, %s, %s, %s, %s)",
            (name, quantity, price, city, store)
        )
        conn.commit()
        return '', 201
    finally:
        conn.close()

# Удаление товара полностью
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product_completely(product_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Товар успешно удалён.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервераS'}), 500
    finally:
        if conn:
            conn.close()

# Поиск товара
@app.route('/search_product', methods=['GET'])
def search_product():
    query = request.args.get('query', '')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT city, store, name, quantity, purchase_price FROM products WHERE name ILIKE %s", (f"%{query}%",))
        products = cur.fetchall()
        return jsonify([
    {
        'city': p[0],
        'store': p[1],
        'name': p[2],
        'quantity': p[3],
        'price': p[4]
    }
    for p in products])
    finally:
        conn.close()

@app.route('/modify_product/<int:product_id>', methods=['POST'])
def modify_product(product_id):
    data = request.json
    action = data.get('action')
    quantity = data.get('quantity')

    if action not in ['add', 'delete'] or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({'success': False, 'message': 'Некорректные данные.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем текущее количество товара
        cur.execute("SELECT quantity FROM products WHERE id = %s", (product_id,))
        result = cur.fetchone()

        if not result:
            return jsonify({'success': False, 'message': 'Товар не найден.'}), 404

        current_quantity = result[0]

        # Рассчитываем новое количество
        if action == 'add':
            new_quantity = current_quantity + quantity
        elif action == 'delete':
            new_quantity = current_quantity - quantity
            if new_quantity < 0:
                return jsonify({'success': False, 'message': 'Недостаточное количество товара.'}), 400

        # Обновляем количество в базе данных
        cur.execute("UPDATE products SET quantity = %s WHERE id = %s", (new_quantity, product_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Количество успешно обновлено.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/update_price/<int:product_id>', methods=['POST'])
def update_price(product_id):
    data = request.json
    new_price = data.get('price')

    if not new_price or not isinstance(new_price, (int, float)) or new_price <= 0:
        return jsonify({'success': False, 'message': 'Некорректная цена.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверяем, существует ли товар
        cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Товар не найден.'}), 404

        # Обновляем цену
        cur.execute("UPDATE products SET purchase_price = %s WHERE id = %s", (new_price, product_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Цена успешно обновлена.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/change_store/<int:product_id>', methods=['POST'])
def change_store(product_id):
    data = request.json
    city_id = data.get('city_id')
    store_id = data.get('store_id')

    if not city_id or not store_id:
        return jsonify({'success': False, 'message': 'Данные не заполнены.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Обновляем склад для товара
        cur.execute("""
            UPDATE products
            SET city = %s, store = %s
            WHERE id = %s
        """, (city_id, store_id, product_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Склад успешно обновлен.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/add_role', methods=['POST'])
def add_role():
    data = request.json
    id = data.get('id')
    name = data.get('name')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO roles (id, name) VALUES (%s, %s)",
            (id, name)
        )
        conn.commit()
        return '', 201
    finally:
        conn.close()

@app.route('/delete_role', methods=['POST'])
def delete_role():
    data = request.json
    role_id = data.get('id') 

    if not role_id:
        return jsonify({'error': 'ID роли обязателен'}), 400
    if (role_id == '777'):
        return jsonify({'error':'Вы не можете удалить роль admin'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM roles WHERE id = %s", (role_id,)
        )
        conn.commit()
        return '', 204  # Код 204 (No Content), если удаление успешно
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Ошибка при удалении роли'}), 500
    finally:
        conn.close()

@app.route('/roles', methods=['GET'])
def get_roles():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM roles")
        roles = cur.fetchall()
        return jsonify([{"id": role[0], "name": role[1]} for role in roles])
    finally:
        conn.close()

@app.route('/update_user_role', methods=['POST'])
def update_user_role():
    data = request.json
    username = data.get('username')
    new_role = data.get('role')

    if not username or not new_role:
        return jsonify({"error": "Не указаны все данные"}), 400

    current_user = session.get('username')
    if username == current_user:
        return jsonify({"error": "Вы не можете изменить свою роль"}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверка существования пользователя
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "Пользователь не найден"}), 404

        # Обновление роли
        cur.execute("UPDATE users SET role_id = %s WHERE username = %s", (new_role, username))
        conn.commit()

        return '', 200
    finally:
        conn.close()

@app.route('/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получение списка пользователей и их ролей
        cur.execute("""
            SELECT u.username, u.role_id, r.name AS role_name FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
        """)
        users = cur.fetchall()

        return jsonify([
            {
                "username": user[0],
                "role": user[2]
            }
            for user in users
        ])
    except Exception as e:
        return jsonify({"error": f"Ошибка сервера"}), 500
    finally:
        if conn:
            conn.close()
            
@app.route('/download-csv', methods=['GET'])
def export_data():
    format_type = request.args.get('format', 'csv')  # По умолчанию формат CSV

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Не удалось установить соединение с базой данных'}), 500

        cur = conn.cursor()
        if not cur:
            return jsonify({'error': 'Не удалось создать курсор базы данных'}), 500

        # Получение всех данных из таблицы `products`
        try:
            cur.execute("SELECT * FROM products")
            rows = cur.fetchall()
            column_names = [desc[0] for desc in cur.description]
        except Exception as e:
            return jsonify({'error': f'Ошибка при выполнении запроса к базе данных: {str(e)}'}), 500

        if not rows:
            return jsonify({'error': 'Нет данных для экспорта'}), 404

        if format_type == 'csv':
            try:
                output = io.StringIO()
                writer = csv.writer(output)

                # Добавляем заголовок
                writer.writerow(column_names)

                # Добавляем данные
                writer.writerows(rows)
                output.seek(0)

                # Формируем CSV для отправки клиенту
                return send_file(
                    io.BytesIO(output.getvalue().encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name='products.csv'
                )
            except Exception as e:
                return jsonify({'error': f'Ошибка при генерации CSV'}), 500

        else:
            return jsonify({'error': 'Неподдерживаемый формат данных'}), 400

    except Exception as e:
        return jsonify({'error': f'Общая ошибка сервера'}), 500

    finally:
        try:
            if conn:
                conn.close()
        except Exception as e:
            print(f'Ошибка при закрытии соединения с базой данных')

@app.route('/add_store', methods=['POST'])
def add_store():
    data = request.json
    city = data.get('city')
    store = data.get('store')

    try:
       
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO store_locations (city, store) VALUES (%s, %s)",
            (city, store)
        )
        conn.commit()
        return '', 201
    finally:
        conn.close()

@app.route('/delete_store', methods=['POST'])
def delete_store():
    data = request.json
    city = data.get('city')  
    store = data.get('store')
    
    if not city or not store:
        return jsonify({'error': 'Поля обязательны для заполнения'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Удаление из таблицы products
        cur.execute(
            """
            UPDATE products
            SET city = %s
            WHERE city = %s AND store = %s
            """,
            (city+'(удален)', city, store)
        )
        # Удаление из таблицы store_locations
        cur.execute(
            "DELETE FROM store_locations WHERE city = %s AND store = %s", (city, store)
        )
        
        conn.commit()
        return '', 204  # Успешный запрос, но тело ответа пустое
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Ошибка при удалении'}), 500
    finally:
        conn.close()

@app.route('/get_stores', methods=['GET'])
def get_stores():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT city, store FROM store_locations")
        rows = cur.fetchall()

        # Формируем список складов в формате JSON
        stores = [{'city': row[0], 'store': row[1]} for row in rows]
        return jsonify(stores), 200
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({'error': 'Ошибка при получении данных складов'}), 500
    finally:
        conn.close()

@app.route('/update_product_store', methods=['POST'])
def update_product_store():
    data = request.json
    product_id = data['productId']
    city = data['city']
    store = data['store']

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Обновление данных товара
        cur.execute("""
            UPDATE products
            SET city = %s, store = %s
            WHERE id = %s
        """, (city, store, product_id))
        conn.commit()

        return jsonify({"message": "Склад обновлен успешно."}), 200
    except Exception as e:
        return jsonify({"error": "Ошибка"}), 500
    finally:
        conn.close()

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)