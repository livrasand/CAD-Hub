from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Configura la ruta de la base de datos
DATABASE = 'cad.db'

# Función para conectar a la base de datos
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.route('/')
def index():
    return render_template('index.html')

# Ruta para el inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Verifica las credenciales en la base de datos
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM administracion WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        
        if user:
            # Redirige a la página de inicio y pasa el correo electrónico como un parámetro en la URL
            return redirect(url_for('home', email=email))
        else:
            return redirect(url_for('invalid'))
    return render_template('login.html')

@app.route('/home')
def home():
    email = request.args.get('email')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM administracion")
    user = cursor.fetchone()

    id = email
    cursor.execute("SELECT code, fecha FROM events_codes WHERE id=?", (id,))
    codes = cursor.fetchall()

    return render_template('home.html', user=user, codes=codes, email=email)

@app.route('/invalid')
def invalid():
    return render_template('invalid.html')

@app.route('/logout')
def logout():
    return render_template('login.html')

@app.route('/create')
def create():
    return render_template('create.html')

@app.route('/access', methods=['GET', 'POST'])
def access():
    if request.method == 'POST':
        # Obtener el código del evento del formulario
        event_code = request.form['eventCode']
        
        # Realizar la validación en la base de datos
        if validar_codigo(event_code):
            return redirect('/cad')
        else:
            return redirect('/invalid')
    else:
        return render_template('/')

# Función para validar el código del evento en la base de datos
def validar_codigo(event_code):
    # Establecer conexión con la base de datos
    db = get_db()
    cursor = db.cursor()
    
    # Consultar si el código existe en la tabla events_codes
    cursor.execute("SELECT id FROM events_codes WHERE code=?", (event_code,))
    row = cursor.fetchone()
    print("Resultado de la consulta a events_codes:", row)
    
    if row:
        # Si el código existe, buscar el texto de la columna 'id' en la misma fila
        user_id = row[0]
        cursor.execute("SELECT * FROM administracion WHERE email=?", (user_id,))
        user_email = cursor.fetchone()
        print("Resultado de la consulta a administracion:", user_email)
        
        if user_email:
            # Si el email existe en la tabla administracion, la validación es exitosa
            return True
    
    # Cerrar la conexión a la base de datos

    # Si no se encontró el código en la tabla events_codes o el email en la tabla administracion, devolver False
    return False

# Variable global para almacenar el nombre de la base de datos
current_database = None

@app.route('/cad')
def cad():
    global current_database
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT * FROM events_codes")
    events = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        # Realizar operaciones en la nueva base de datos
        # Por ejemplo, realizar una consulta
        # cursor.execute("SELECT * FROM tabla_en_nueva_db")
        # data_from_new_db = cursor.fetchall()

        print("Base de datos:", current_database)

        return render_template('cad.html', administracion=administracion, events=events)
    else:
        print("Base de datos no encontrada")

@app.route('/presidencia')
@app.route('/presidencia_ADMIN')
def presidencia():
    global current_database

    departamento = "Presidencia"
    table = "presidencia"

    # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Presidencia"
        table = "presidencia"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/guardar_informe', methods=['POST'])
def guardar_informe():
    presidencia()

    departamento = request.form['departamento']
    desempeno = request.form['desempeno']
    funcionalidad = request.form['funcionalidad']
    observaciones = request.form['observaciones']

    print("Base de datos a guardar:", current_database)
    
    if current_database is not None:
        # Abrir una conexión a la base de datos
        new_db = sqlite3.connect(current_database)
        cursor = new_db.cursor()
        print("Acceso a la base de datos ", current_database)

        # Insertar los datos del informe en la tabla correspondiente
        cursor.execute("INSERT INTO {} (Desempeno, Funcionalidad, Observaciones_generales) VALUES (?, ?, ?)".format(departamento), (desempeno, funcionalidad, observaciones))
        new_db.commit()

        # Cerrar la conexión a la base de datos
        new_db.close()

        return redirect('/cad')
    else:
        # Manejar el caso cuando current_database es None
        return "Error: No se ha especificado la base de datos."

@app.route('/administracion')
@app.route('/administracion_ADMIN')
def administracion():
    global current_database

    departamento = "Administración"
    table = "administracion"

    # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Administración"
        table = "administracion"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute(f"SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute(f"SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")


@app.route('/acomodadores')
@app.route('/acomodadores_ADMIN')
def acomodadores():
    global current_database

    departamento = "Acomodadores"
    table = "acomodadores"

     # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Acomodadores"
        table = "acomodadores"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/instalacion')
@app.route('/instalacion_ADMIN')
def instalacion():
    global current_database

    departamento = "Instalación"
    table = "instalacion"

    # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Instalación"
        table = "instalacion"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/bautismo')
@app.route('/bautismo_ADMIN')
def bautismo():
    global current_database

    departamento = "Bautismo"
    table = "bautismo"

    # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Bautismo"
        table = "bautismo"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/primeros_auxilios')
@app.route('/primeros_auxilios_ADMIN')
def primeros_auxilios():
    global current_database

    departamento = "Primeros auxilios"
    table = "primeros_auxilios"

    # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Primeros auxilios"
        table = "primeros_auxilios"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/limpieza')
@app.route('/limpieza_ADMIN')
def limpieza():
    global current_database

    departamento = "Limpieza"
    table = "limpieza"

     # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Limpieza"
        table = "limpieza"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/guardarropa_objetos_perdidos')
@app.route('/guardarropa_objetos_perdidos_ADMIN')
def guardarropa_objetos_perdidos():
    global current_database

    departamento = "Guardarropa y objetos perdidos"
    table = "guardarropa_objetos_perdidos"

     # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Guardarropa y objetos perdidos"
        table = "guardarropa_objetos_perdidos"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/plataforma')
@app.route('/plataforma_ADMIN')
def plataforma():
    global current_database

    departamento = "Plataforma"
    table = "plataforma"

     # Verificar si se agregó "_ADMIN" a la URL
    if request.path.endswith("_ADMIN"):
        departamento = "Plataforma"
        table = "plataforma"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/estacionamiento')
@app.route('/estacionamiento_ADMIN')
def estacionamiento():
    global current_database

    departamento = "Estacionamiento"
    table = "estacionamiento"

    if request.path.endswith("_ADMIN"):
        departamento = "Estacionamiento"
        table = "estacionamiento"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/audio_video')
@app.route('/audio_video_ADMIN')
def audio_video():
    global current_database

    departamento = "Audio y video"
    table = "audio_video"

    if request.path.endswith("_ADMIN"):
        departamento = "Audio y video"
        table = "audio_video"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/contabilidad')
@app.route('/contabilidad_ADMIN')
def contabilidad():
    global current_database

    departamento = "Contabilidad"
    table = "contabilidad"

    if request.path.endswith("_ADMIN"):
        departamento = "Contabilidad"
        table = "contabilidad"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

@app.route('/agua_purificada')
@app.route('/agua_purificada_ADMIN')
def agua_purificada():
    global current_database

    departamento = "Agua purificada"
    table = "agua_purificada"

    if request.path.endswith("_ADMIN"):
        departamento = "Agua purificada"
        table = "agua_purificada"

    fecha_actual = datetime.now().strftime("%d de %B de %Y") 
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM administracion")
    administracion = cursor.fetchone()

    cursor.execute("SELECT database FROM administracion")
    database = cursor.fetchone()

    if database:
        database_name = database[0]
        current_database = database_name  # Actualizar la variable global
        # Cerrar la conexión actual
        db.close()

        # Establecer una nueva conexión a la base de datos especificada
        new_db = sqlite3.connect(database_name)
        cursor = new_db.cursor()

        cursor.execute(f"SELECT * FROM {table}")
        departamento_data = cursor.fetchone()

        print("Base de datos:", current_database)

        return render_template('detail-cad.html', administracion=administracion, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
    else:
        print("Base de datos no encontrada")

if __name__ == '__main__':
    app.run(debug=True)
