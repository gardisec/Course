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
    if 'username' in session and session.get('role_id') == 2:
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

            if role_id == 1:
                return jsonify({'success': True, 'redirect': '/admin'})
            else:
                return jsonify({'success': False, 'message': 'Нет доступа.'})
        else:
            return jsonify({'success': False, 'message': 'Неверное имя пользователя или пароль.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка сервера.'})
    finally:
        if conn:
            conn.close()


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    password_conf = data.get('passwordConf')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Имя пользователя и пароль обязательны.'})
    if len(username) < 4 or len(username) > 32:
        return jsonify({'success': False, 'message': 'Длина имени пользователя должна быть от 4 до 32 символов.'})
    if password_conf != password:
        return jsonify({'success': False, 'message': 'Пароли не совпадают.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Пользователь уже существует.'})

        hashed_password = generate_password_hash(password)
        default_role_id = 1

        cur.execute(
            "INSERT INTO users (username, password_hash, role_id, created_at) VALUES (%s, %s, %s, NOW())",
            (username, hashed_password, default_role_id)
        )
        conn.commit()
        session['username'] = username
        session['role_id'] = default_role_id

        return jsonify({'success': True, 'redirect': '/admin', 'message': 'Успешная регистрация.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка сервера.'})
    finally:
        if conn:
            conn.close()


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/products', methods=['GET'])
def get_products():
    try:
        name = request.args.get('name', '').strip()
        store_id = request.args.get('store_id')
        quantity_min = request.args.get('quantityMin')
        quantity_max = request.args.get('quantityMax')
        price_min = request.args.get('priceMin')
        price_max = request.args.get('priceMax')

        query = """
            SELECT id, name, quantity, purchase_price, created_at, updated_at
            FROM products
            WHERE 1=1
        """
        params = []

        if name:
            query += " AND name ILIKE %s"
            params.append(f"%{name}%")
        if store_id:
            query += " AND store_id = %s"
            params.append(store_id)
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

        query += " ORDER BY name"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        products = cur.fetchall()

        return jsonify([
            {
                'id': p[0],
                'name': p[1],
                'quantity': p[2],
                'price': p[3],
                'created_at': p[4],
                'updated_at': p[5]
            }
            for p in products
        ])
    except Exception as e:
        return jsonify({'error': 'Ошибка при получении данных'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/store_locations', methods=['GET'])
def get_store_locations():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT city, store_number FROM store_locations")
        rows = cur.fetchall()

        store_locations = {}
        for city, store_number in rows:
            if city not in store_locations:
                store_locations[city] = []
            store_locations[city].append(store_number)

        return jsonify(store_locations)
    except Exception as e:
        return jsonify({'error': 'Ошибка при получении данных о расположении складов'}), 500
    finally:
        conn.close()


@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json
    name = data.get('name', '').strip()
    try:
        quantity = int(data.get('quantity', -1))
        price = float(data.get('price', -1))
        store_id = int(data.get('store_id', -1))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Цена и количество товара должны быть числами.'})

    if not name:
        return jsonify({'success': False, 'message': 'Название товара некорректно.'})
    if quantity < 0:
        return jsonify({'success': False, 'message': 'Количество товара некорректное.'})
    if price < 0:
        return jsonify({'success': False, 'message': 'Цена за товар не может быть меньше 0.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM store_locations WHERE id = %s", (store_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Указанный склад не существует.'})

        cur.execute(
            """
            INSERT INTO products (name, quantity, purchase_price, store_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            """,
            (name, quantity, price, store_id)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Товар успешно добавлен.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка при добавлении товара.'}), 500
    finally:
        if conn:
            conn.close()
########################################################################

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product_completely(product_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Товар успешно удалён.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'Невозможно удалить товар'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/search_product', methods=['GET'])
def search_product():
    try:
        name = request.args.get('name', '').strip()
        store_id = request.args.get('store_id')
        
        query = "SELECT id, name, quantity, purchase_price FROM products WHERE 1=1"
        params = []

        if name:
            query += " AND name ILIKE %s"
            params.append(f"%{name}%")
        if store_id:
            query += " AND store_id = %s"
            params.append(store_id)
        
        query += " ORDER BY name"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        products = cur.fetchall()

        return jsonify([{'id': p[0], 'name': p[1], 'quantity': p[2], 'price': p[3]} for p in products])
    except Exception:
        return jsonify({'error': 'Ошибка поиска продукта'}), 500
    finally:
        conn.close()
###########################################

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

        cur.execute("SELECT quantity FROM products WHERE id = %s", (product_id,))
        result = cur.fetchone()

        if not result:
            return jsonify({'success': False, 'message': 'Товар не найден.'}), 404

        current_quantity = result[0]

        if action == 'add':
            new_quantity = current_quantity + quantity
        elif action == 'delete':
            new_quantity = current_quantity - quantity
            if new_quantity < 0:
                return jsonify({'success': False, 'message': 'Недостаточное количество товара.'}), 400

        cur.execute(
            "UPDATE products SET quantity = %s, updated_at = NOW() WHERE id = %s",
            (new_quantity, product_id)
        )
        conn.commit()

        return jsonify({'success': True, 'message': 'Количество успешно обновлено.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка при изменении количества'}), 500
    finally:
        if conn:
            conn.close()



@app.route('/update_price/<int:product_id>', methods=['POST'])
def update_price(product_id):
    data = request.json
    new_price = data.get('price')

    if not new_price or not isinstance(new_price, (int, float)) or new_price < 0:
        return jsonify({'success': False, 'message': 'Некорректная цена.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Товар не найден.'}), 404

        cur.execute("UPDATE products SET purchase_price = %s WHERE id = %s", (new_price, product_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Цена успешно обновлена.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка при изменении цены'}), 500
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

        cur.execute("""
            UPDATE products
            SET city = %s, store = %s
            WHERE id = %s
        """, (city_id, store_id, product_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Склад успешно обновлен.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка сервера'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/add_role', methods=['POST'])
def add_role():
    data = request.json
    role_name = data.get('name', '').strip()
    if not role_name:
        return jsonify({'success': False, 'message': 'Имя роли некорректно.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Такая роль уже существует.'}), 400

        cur.execute("INSERT INTO roles (name) VALUES (%s)", (role_name,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Роль добавлена.'})
    except Exception:
        return jsonify({'error': 'Ошибка при добавлении роли'}), 500
    finally:
        conn.close()


@app.route('/delete_role', methods=['DELETE'])
def delete_role():
    data = request.json
    role_id  = data.get('id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE role_id = %s", (role_id,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Роль используется пользователями, её нельзя удалить.'}), 400

        cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Роль удалена.'})
    except Exception:
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
        return jsonify({'success': False, 'message': 'Поля не заполнены.'}), 400

    current_user = session.get('username')
    if username == current_user:
        return jsonify({'success': False, 'message': 'Нельзя изменять свою роль.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'пользователь не найден.'}), 201

        cur.execute("UPDATE users SET role_id = %s WHERE username = %s", (new_role, username))
        conn.commit()

        return jsonify({'success': True, 'message': 'Роль успешно обновлена.'}), 201
    finally:
        conn.close()


@app.route('/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

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
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получение данных из всех таблиц
        cur.execute("SELECT * FROM roles")
        roles = cur.fetchall()

        cur.execute("SELECT * FROM store_locations")
        stores = cur.fetchall()

        cur.execute("SELECT * FROM products")
        products = cur.fetchall()

        cur.execute("SELECT * FROM users")
        users = cur.fetchall()

        cur.execute("SELECT * FROM audit")
        audit = cur.fetchall()

        # Формирование ответа
        data = {
            'roles': [{'id': r[0], 'name': r[1]} for r in roles],
            'stores': [{'id': s[0], 'city': s[1], 'store_number': s[2]} for s in stores],
            'products': [{'id': p[0], 'name': p[1], 'quantity': p[2], 'purchase_price': p[3],
                          'created_at': p[4], 'updated_at': p[5], 'store_id': p[6]} for p in products],
            'users': [{'id': u[0], 'username': u[1], 'password_hash': u[2],
                       'role_id': u[3], 'created_at': u[4]} for u in users],
            'audit': [{'id': a[0], 'username': a[1], 'role_id': a[2],
                       'product_id': a[3], 'time': a[4]} for a in audit]
        }

        return jsonify(data)
    except Exception:
        return jsonify({'error': 'Ошибка при экспорте данных'}), 500
    finally:
        conn.close()


@app.route('/add_store', methods=['POST'])
def add_store():
    data = request.json
    city = data.get('city')
    try:
        store = int(data.get('store', -1))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Номер склада должен быть целым числом.'})
    
    if (len(city) < 1 or len(city) > 50):
        return jsonify({'success': False, 'message': 'Название города должно содержать от 1 до 50 символов.'}), 400
    
    try:
       
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO store_locations (city, store) VALUES (%s, %s)",
            (city, store)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Склад успешно добавлен.'}), 201
    finally:
        conn.close()


@app.route('/delete_store', methods=['POST'])
def delete_store(store_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM products WHERE store_id = %s", (store_id,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Невозможно удалить склад, он связан с продуктами.'}), 400

        cur.execute("DELETE FROM store_locations WHERE id = %s", (store_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Склад удалён.'})
    except Exception:
        return jsonify({'error': 'Ошибка при удалении склада'}), 500
    finally:
        conn.close()


@app.route('/get_stores', methods=['GET'])
def get_stores():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT city, store FROM store_locations")
        rows = cur.fetchall()

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
    city = data.get('city', '').strip()
    product_id = data.get('productId')
    try:
        store = int(data.get('store', -1))
        
    except (ValueError, TypeError):
        return jsonify({"error": "Неверный номер склада."}), 400

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"error": "Неверный идентификатор товара."}), 400


    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM products WHERE id = %s", (product_id,))
        if cur.fetchone() is None:
            return jsonify({"error": "Товар с указанным идентификатором не найден."}), 404

        cur.execute("""
            UPDATE products
            SET city = %s, store = %s
            WHERE id = %s
        """, (city, store, product_id))
        conn.commit()

        return jsonify({"message": "Склад обновлен успешно."}), 200
    except Exception as e:
        return jsonify({"error": "Внутренняя ошибка сервера."}), 500
    finally:
        conn.close()


@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)