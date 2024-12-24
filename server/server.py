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

@app.route('/moder')
def admin_page():
    if 'username' in session and session.get('role_id') == 2:
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

            if role_id ==2:
                return jsonify({'success': True, 'redirect': '/moder'})
            else:
                return jsonify({'success': False, 'message': 'Нет доступа.'})
        else:
            return jsonify({'success': False, 'message': 'Неверное имя пользователя или пароль.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка'})
    finally:
        if conn:
            conn.close()


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    passwordConf = data.get('passwordConf')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Имя пользователя и пароль обязательны.'})
    if (len(username) > 32 or len(username) < 4):
        return jsonify({'success': False, 'message': 'Длина вашего имени пользователя не должна быть не менее 4 и не более 32'})
    if (username == " "):
        return jsonify({'success': False, 'message': 'Имя пользователя не должно быть пустым'})
    if (passwordConf != password):
        return jsonify({'success': False, 'message': 'Пароли не совпадают'})
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Пользователь уже существует.'})


        hashed_password = generate_password_hash(password)
        role_id = 2

        cur.execute(
            "INSERT INTO users (username, password_hash, role_id) VALUES (%s, %s, %s)",
            (username, hashed_password, role_id)
        )
        conn.commit()
        session['username'] = username
        session['role_id'] = role_id

        return jsonify({'success': True, 'redirect': '/moder', 'message': f'Успешно'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера'})
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
        city = request.args.get('city', '').strip()
        store = request.args.get('store', '').strip()
        quantity_min = request.args.get('quantityMin')
        quantity_max = request.args.get('quantityMax')
        price_min = request.args.get('priceMin')
        price_max = request.args.get('priceMax')

        query = """
            SELECT 
                p.id, 
                sl.city, 
                sl.store, 
                p.name, 
                p.quantity, 
                p.purchase_price 
            FROM 
                products p
            INNER JOIN 
                store_locations sl ON p.store_id = sl.id
            WHERE 1=1
        """
        params = []

        if name:
            query += " AND p.name ILIKE %s"
            params.append(f"%{name}%")
        if city:
            query += " AND sl.city = %s"
            params.append(city)
        if store:
            query += " AND sl.store = %s"
            params.append(int(store))
        if quantity_min:
            query += " AND p.quantity >= %s"
            params.append(int(quantity_min))
        if quantity_max:
            query += " AND p.quantity <= %s"
            params.append(int(quantity_max))
        if price_min:
            query += " AND p.purchase_price >= %s"
            params.append(float(price_min))
        if price_max:
            query += " AND p.purchase_price <= %s"
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
                'price': float(p[5])
            }
            for p in products
        ])
    except Exception as e:
        return jsonify({"error": "Внутренняя ошибка сервера."}), 500
    finally:
        conn.close()


@app.route('/store_locations', methods=['GET'])
def get_store_locations():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT city, store FROM store_locations")
        rows = cur.fetchall()

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
    name = data.get('name', '').strip()

    try:
        quantity = int(data.get('quantity', -1))
        price = float(data.get('price', -1))
        store = int(data.get('store', -1))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Цена и количество товара должны быть числами.'})

    city = data.get('city', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Название товара некорректно.'})
    if quantity < 0:
        return jsonify({'success': False, 'message': 'Количество товара некорректное.'})
    if price < 0:
        return jsonify({'success': False, 'message': 'Цена за товар не может быть меньше 0.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id FROM store_locations
            WHERE city = %s AND store = %s
            """,
            (city, store)
        )
        store_row = cur.fetchone()

        if not store_row:
            return jsonify({'success': False, 'message': 'Указанный город и склад не существуют.'})

        store_id = store_row[0]

        cur.execute(
            """
            INSERT INTO products (name, quantity, purchase_price, store_id)
            VALUES (%s, %s, %s, %s)
            """,
            (name, quantity, price, store_id)
        )

        conn.commit()
        return jsonify({'success': True, 'message': 'Товар успешно добавлен.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка при добавлении товара: {str(e)}'})
    finally:
        conn.close()



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
    query = request.args.get('query', '').strip()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT sl.city, sl.store, p.name, p.quantity, p.purchase_price
            FROM products p
            INNER JOIN store_locations sl ON p.store_id = sl.id
            WHERE p.name ILIKE %s
            """,
            (f"%{query}%",)
        )

        products = cur.fetchall()

        return jsonify([
            {
                'city': p[0],
                'store': p[1],
                'name': p[2],
                'quantity': p[3],
                'price': p[4]
            }
            for p in products
        ])
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

        cur.execute("UPDATE products SET quantity = %s WHERE id = %s", (new_quantity, product_id))
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


@app.route('/update_product_store', methods=['POST'])
def update_product_store():
    data = request.json
    city = data.get('city', '').strip()
    product_id = data.get('productId')

    try:
        store = int(data.get('store', -1))
        if store <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Неверный номер склада."}), 400

    try:
        product_id = int(product_id)
        if product_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Неверный идентификатор товара."}), 400

    if not city:
        return jsonify({"error": "Город не указан."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT store_id FROM products WHERE id = %s", (product_id,))
        product_row = cur.fetchone()
        if not product_row:
            return jsonify({"error": "Товар с указанным идентификатором не найден."}), 404

        current_store_id = product_row[0]

        cur.execute(
            "SELECT id FROM store_locations WHERE city = %s AND store = %s",
            (city, store)
        )
        store_row = cur.fetchone()
        if not store_row:
            return jsonify({"error": "Указанный город и склад не существуют."}), 404

        new_store_id = store_row[0]

        if current_store_id == new_store_id:
            return jsonify({"error": "Склад не изменен, текущий склад совпадает с указанным."}), 400

        cur.execute(
            "UPDATE products SET store_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (new_store_id, product_id)
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Ошибка при обновлении склада."}), 400

        conn.commit()
        return jsonify({"message": "Склад обновлен успешно."}), 200
    except Exception as e:
        return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()




@app.route('/add_role', methods=['POST'])
def add_role():
    data = request.json
    name = data.get('name')
    if (len(name) < 1 or len(name) > 32):
        return jsonify({'success': False, 'message': 'Название роли должно содержать от 1 до 32 символов.'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO roles (name) VALUES (%s)",
            (name,)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Роль успешно добавлена.'}), 201
    except Exception as a:
        return jsonify({'success': False, 'message': 'Ошибка при добавлении роли.'}), 500
    finally:
        conn.close()


@app.route('/delete_role', methods=['POST'])
def delete_role():
    data = request.json
    role_id = data.get('id') 

    if not role_id:
        return jsonify({'success': False, 'message': 'ID обязателен.'}), 400
    if (role_id == '1'):
        return jsonify({'success': False, 'message': 'Вы не можете удалить роль admin.'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM roles WHERE id = %s", (role_id)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Роль успешно удалена.'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Ошибка при удалении роли.'}), 500
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
    format_type = request.args.get('format', 'csv')  

    try:
        conn = get_db_connection()

        cur = conn.cursor()

        try:
            cur.execute("SELECT * FROM products")
            rows = cur.fetchall()
            column_names = [desc[0] for desc in cur.description]
        except Exception as e:
            return jsonify({'error': f'Ошибка при выполнении запроса к базе данных'}), 500

        if not rows:
            return jsonify({'error': 'Нет данных для экспорта'}), 404

        if format_type == 'csv':
            try:
                output = io.StringIO()
                writer = csv.writer(output)

                writer.writerow(column_names)

                writer.writerows(rows)
                output.seek(0)

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
    try:
        store = int(data.get('store', -1))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Номер склада должен быть целым числом.'})
    
    if (len(city) < 1 or len(city) > 50):
        return jsonify({'success': False, 'message': 'Название роли должно содержать от 1 до 50 символов.'}), 400
    
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
def delete_store():
    data = request.json
    city = data.get('city')  
    store = data.get('store')
    
    if not city or not store:
        return jsonify({'success': False, 'message': 'Поля не заполнены.'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM store_locations WHERE city = %s AND store = %s",
            (city, store)
        )
        store_id_row = cur.fetchone()

        if not store_id_row:
            return jsonify({'success': False, 'message': 'Склад не найден.'}), 404

        store_id = store_id_row[0]

        cur.execute(
            "SELECT COUNT(*) FROM products WHERE store_id = %s",
            (store_id,)
        )
        product_count = cur.fetchone()[0]

        if product_count > 0:
            return jsonify({'success': False, 'message': 'Невозможно удалить склад (он не пуст).'}), 400
        
        cur.execute(
            "DELETE FROM store_locations WHERE id = %s", (store_id,)
        )

        conn.commit()
        return jsonify({'success': True, 'message': 'Склад успешно удалён.'}), 201 
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Ошибка при удалении склада: {e}'}), 500
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


@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)