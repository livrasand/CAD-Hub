from flask import Flask, render_template, request, redirect, url_for, g, flash, session
import sqlite3
from datetime import datetime
import secrets
import os
import shutil
from flask_mail import Mail, Message
import logging
import random
import datetime
import string
import uuid  

app = Flask(__name__)
app.secret_key = '14b9856a0a051c5e80e072f4de6dfe306f913c3ea5c946f1'

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'noresponder.kha@gmail.com'
app.config['MAIL_PASSWORD'] = 'sdlj izlj wpix ipsn'
app.config['MAIL_DEFAULT_SENDER'] = ('Join CAD Hub', 'noresponder.kha@gmail.com')

mail = Mail(app)

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

@app.route('/delete')
def delete():
    return render_template('delete.html')

@app.route('/account/delete', methods=['POST'])
def delete_account():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not verify_credentials(email, password):
            flash('Credenciales incorrectas. Por favor, inténtalo de nuevo.')
            return redirect(url_for('account_settings'))

        delete_user(email)

        flash('Tu cuenta ha sido eliminada exitosamente.')
        return redirect(url_for('index'))  # Redirigir al usuario a la página de logout o a donde sea adecuado
    else:
        flash('Método no permitido.')
        return redirect(url_for('home'))

def verify_credentials(email, password):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def delete_user(email):
    db_name = f'{email.split("@")[0]}-cadhub.db'

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    try:
        os.remove(db_name)
        flash(f'La base de datos {db_name} ha sido eliminada.')
    except FileNotFoundError:
        flash(f'Error: la base de datos {db_name} no se encontró.')
    except Exception as e:
        flash(f'Error al eliminar la base de datos: {str(e)}')

@app.route('/email_invitation')
def email_invitation():
    return render_template('email_invitation.html')

@app.route('/invite')
def invite():
    return render_template('invite.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/accessing', methods=['POST'])
def accessing():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        
        if user:
            g.email = email  # Esto debería configurar el correo electrónico en g correctamente
            
            return redirect(url_for('home', email=email))
        else:
            return redirect(url_for('invalid'))
    return render_template('login.html')

@app.route('/home')
def home():
    email = request.args.get('email')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users")
    user = cursor.fetchone()

    id = email
    cursor.execute("SELECT code, fecha FROM events_codes WHERE id=?", (id,))
    codes = cursor.fetchall()

    # Buscar la base de datos asociada al código del evento
    cursor.execute("SELECT id, code FROM events_codes WHERE id=?", (id,))
    row = cursor.fetchall()
    print("Base de datos recibida: ", row)

    users = row

    return render_template('home.html', user=user, codes=codes, email=email, events=row, users=users)

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
        event_code = request.form['eventCode']
        print(f"Event code received: {event_code}")  # Depuración
        
        if validar_codigo(event_code):
            if es_colaborador(event_code):
                return redirect(url_for('cad', colaborador_code=event_code))
            else:
                return redirect(url_for('cad', event_code=event_code))
        else:
            return redirect('/invalid')
    else:
        return render_template('index.html')

@app.route('/inviting', methods=['POST'])
def inviting():
    if request.method == 'POST':
        email = request.form['email']
        correo = request.form['userEmail']  # Obtiene el correo electrónico del formulario
        code = generar_codigo()
        guardar_codigo(correo, code)
        enviar_invitacion(email, code)
        return redirect('/invite')  # Redirige a una página de éxito
    else:
        return render_template('invite.html')

def generar_codigo():
    return ''.join(random.choices(string.digits, k=6))

def guardar_codigo(correo, code):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO colaboradores (id, code) VALUES (?, ?)", (correo, code))
    db.commit()

def enviar_invitacion(email, codigo):
    # Mensaje de la invitación con el código
    mensaje = f"""
    Hola, soy Livrädo Sandoval de CAD Hub.\n\n

    Has sido invitado a ser colaborador en una administración de CAD Hub para tu próxima asamblea de circuito. Usa el siguiente código de acceso para acceder. ¡Esperan contar contigo!\n\n
    
    Tu código de acceso es: {codigo}\n\n
    
    Para aceptar la invitación, ve a cadhub.org e ingresa con tu código.
    """
    
    # Crear un objeto de mensaje
    msg = Message(subject="CAD Hub: Invitación a ser colaborador", recipients=[email])
    
    # Establecer el cuerpo del mensaje
    msg.html = mensaje
    
    # Enviar el correo electrónico
    mail.send(msg)
    
    print("Correo electrónico de invitación enviado a:", email, "con código:", codigo)

# Función para validar si un código existe en events_codes o colaboradores
def validar_codigo(event_code):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM events_codes WHERE code=?", (event_code,))
    row = cursor.fetchone()
    if row:
        return True

    cursor.execute("SELECT id FROM colaboradores WHERE code=?", (event_code,))
    row = cursor.fetchone()
    if row:
        return True
    
    return False

# Función para obtener la base de datos asociada a un evento
def obtener_database_evento(event_code, cursor):
    cursor.execute("SELECT database FROM events_codes WHERE code=?", (event_code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    return None

def es_colaborador(event_code):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM colaboradores WHERE code=?", (event_code,))
    row = cursor.fetchone()
    
    return row is not None

# Función para obtener la base de datos asociada a un colaborador
def obtener_database_colaborador(colaborador_code, cursor):
    cursor.execute("SELECT id FROM colaboradores WHERE code=?", (colaborador_code,))
    row = cursor.fetchone()
    
    if row:
        correo = row[0]
        cursor.execute("SELECT database FROM users WHERE email=?", (correo,))
        row = cursor.fetchone()
        if row:
            return row[0]
    
    return None

# Variable global para almacenar el nombre de la base de datos
current_database = None

@app.route('/cad', methods=['GET', 'POST'])
def cad():
    global current_database
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM events_codes")
    events = cursor.fetchall()

    event_code = request.args.get('event_code')
    colaborador_code = request.args.get('colaborador_code')

    user = events[0]
    
    if colaborador_code:
        specific_database = obtener_database_colaborador(colaborador_code, cursor)
        if specific_database:
            current_database = specific_database  # Actualizar la variable global
            db.close()

            try:
                new_db = sqlite3.connect(specific_database)
                cursor = new_db.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
                table_exists = cursor.fetchone()
                
                if table_exists:
                    cursor.execute("SELECT * FROM users")
                    users = cursor.fetchall()
                    return render_template('cad_admin.html', users=users, events=events, current_database=current_database)
                else:
                    print("Tabla 'users' no encontrada en la base de datos especificada.")
                    return render_template('cad_admin.html', users=user, events=events, error="La base de datos especificada no contiene la tabla 'users'.")
            except sqlite3.Error as e:
                print(f"Error al conectar con la base de datos específica: {e}")
                return render_template('cad.html', events=events, error="Error al conectar con la base de datos específica.")
        else:
            print("Base de datos no encontrada para el colaborador")
            return render_template('cad.html', events=events, error="Base de datos asociada al colaborador no encontrada.")
    
    elif event_code:
        cursor.execute("SELECT database FROM events_codes WHERE code=?", (event_code,))
        row = cursor.fetchone()
        if row:
            specific_database = row[0]
            current_database = specific_database  # Actualizar la variable global
            db.close()

            try:
                new_db = sqlite3.connect(specific_database)
                cursor = new_db.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
                table_exists = cursor.fetchone()
                
                if table_exists:
                    cursor.execute("SELECT * FROM users")
                    users = cursor.fetchall()
                    return render_template('cad.html', users=users, events=events, current_database=current_database)
                else:
                    print("Tabla 'users' no encontrada en la base de datos especificada.")
                    return render_template('cad.html', events=events, error="La base de datos especificada no contiene la tabla 'users'.")
            except sqlite3.Error as e:
                print(f"Error al conectar con la base de datos específica: {e}")
                return render_template('cad.html', events=events, error="Error al conectar con la base de datos específica.")
        else:
            print("Base de datos no encontrada para el evento")
            return render_template('cad.html', events=events, error="Base de datos asociada al evento no encontrada.")
    
    # Si no se proporcionó ni colaborador_code ni event_code, retornar la página inicial de cad.html
    return render_template('cad.html', events=events)


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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y") 
    
    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Presidencia:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


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

        # Redireccionar a /cad con el parámetro event_code actualizado
        event_code = request.args.get('event_code', '')
        return redirect(url_for('cad', event_code=event_code))
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
        departamento += " (ADMIN)"
        table = "administracion"

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")
    
    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Administración:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Acomodadores:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")

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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Instalacion:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")

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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Bautismo:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y") 

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Primeros auxilios:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")

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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Limpieza:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y") 
    
    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Guardarropa y objetos perdidos:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


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

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y") 

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Plataforma:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


@app.route('/estacionamiento')
@app.route('/estacionamiento_ADMIN')
def estacionamiento():
    global current_database

    departamento = "Estacionamiento"
    table = "estacionamiento"

    if request.path.endswith("_ADMIN"):
        departamento = "Estacionamiento"
        table = "estacionamiento"

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Estacionamiento:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


@app.route('/audio_video')
@app.route('/audio_video_ADMIN')
def audio_video():
    global current_database

    departamento = "Audio y video"
    table = "audio_video"

    if request.path.endswith("_ADMIN"):
        departamento = "Audio y video"
        table = "audio_video"

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y") 

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Audio y video:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


@app.route('/contabilidad')
@app.route('/contabilidad_ADMIN')
def contabilidad():
    global current_database

    departamento = "Contabilidad"
    table = "contabilidad"

    if request.path.endswith("_ADMIN"):
        departamento = "Contabilidad"
        table = "contabilidad"

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Contabilidad:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")


@app.route('/agua_purificada')
@app.route('/agua_purificada_ADMIN')
def agua_purificada():
    global current_database

    departamento = "Agua purificada"
    table = "agua_purificada"

    if request.path.endswith("_ADMIN"):
        departamento = "Agua purificada"
        table = "agua_purificada"

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            departamento_data = cursor.fetchone()

            print("Base de datos en Agua purificada:", current_database)

            return render_template('detail-cad.html', users=None, departamento=departamento, departamento_data=departamento_data, fecha_actual=fecha_actual, table=table)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-cad.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-cad.html', error="Base de datos no especificada.")

@app.route('/asistencia')
@app.route('/asistencia_ADMIN')
def asistencia():
    global current_database

    departamento = "Asistencia"
    table = "sections"

    if request.path.endswith("_ADMIN"):
        departamento = "Asistencia"
        table = "sections"

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")

    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            secciones = cursor.fetchall()

            cursor.execute(f"SELECT SUM(attendance) FROM {table}")
            total_asistencia = cursor.fetchone()[0] or 0  # Si es None, usar 0

            print("Base de datos en Asistencia:", current_database)

            return render_template('detail-attendance.html', users=None, departamento=departamento, secciones=secciones, fecha_actual=fecha_actual, table=table, total_asistencia=total_asistencia)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-attendance.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-attendance.html', error="Base de datos no especificada.")

@app.route('/secciones', methods=['POST'])
def crear_seccion():
    if request.method == 'POST':
        nombre_seccion = request.form['nombre_seccion']
        
        # Verifica si la base de datos está especificada
        if current_database:
            try:
                # Establecer una conexión a la base de datos especificada
                new_db = sqlite3.connect(current_database)
                cursor = new_db.cursor()
                
                # Insertar la nueva sección en la base de datos
                cursor.execute("INSERT INTO sections (name) VALUES (?)", (nombre_seccion,))
                new_db.commit()
                
                # Cerrar la conexión
                cursor.close()
                new_db.close()
                
                # Redirigir de vuelta a la página principal
                return redirect(url_for('asistencia'))
            except sqlite3.Error as e:
                print(f"Error al conectar con la base de datos específica: {e}")
                return render_template('detail-attendance.html', error="Error al conectar con la base de datos específica.")
        else:
            print("Base de datos no especificada")
            return render_template('detail-attendance.html', error="Base de datos no especificada.")

@app.route('/eliminar_seccion/<string:id_seccion>', methods=['GET'])
def eliminar_seccion(id_seccion):
    global current_database
    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()
            
            # Eliminar la sección de la base de datos
            cursor.execute("DELETE FROM sections WHERE name = ?", (id_seccion,))
            new_db.commit()
            
            # Cerrar la conexión
            cursor.close()
            new_db.close()
            
            # Redirigir de vuelta a la página principal
            return redirect(url_for('asistencia'))
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('detail-attendance.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('detail-attendance.html', error="Base de datos no especificada.")

@app.route('/ver_seccion/<string:id_seccion>')
def ver_seccion(id_seccion):
    global current_database
    if current_database:
        try:
            # Establecer una conexión a la base de datos especificada
            new_db = sqlite3.connect(current_database)
            cursor = new_db.cursor()

            cursor.execute("SELECT * FROM sections WHERE name = ?", (id_seccion,))
            asistentes = cursor.fetchone()

            print("Base de datos de Asistentes:", current_database)

            return render_template('attendance.html', asistentes=asistentes, id_seccion=id_seccion)
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos específica: {e}")
            return render_template('attendance.html', error="Error al conectar con la base de datos específica.")
    else:
        print("Base de datos no especificada")
        return render_template('attendance.html', error="Base de datos no especificada.")

@app.route('/guardar_asistencia', methods=['POST'])
def guardar_asistencia():
    id_seccion = request.form.get('id_seccion')
    attendance = request.form.get('attendance')
    
    if not id_seccion or not attendance:
        return "Error: Missing section ID or attendance number", 400
    
    try:
        new_db = sqlite3.connect(current_database)
        cursor = new_db.cursor()
        
        cursor.execute("UPDATE sections SET attendance = ? WHERE name = ?", (attendance, id_seccion))
        new_db.commit()
        
        return redirect(url_for('ver_seccion', id_seccion=id_seccion))
    except sqlite3.Error as e:
        print(f"Error al actualizar la base de datos: {e}")
        return "Error al actualizar la base de datos", 500
    finally:
        new_db.close()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def generate_random_number_string(length=5):
    return ''.join(random.choices('0123456789', k=length))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        token = secrets.token_urlsafe(16)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        requester_ip = get_requester_ip()
        sender = app.config['MAIL_USERNAME']
        send_email(sender, email, confirm_url, requester_ip)
        
        # Insertar en la base de datos
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (email, token, database) VALUES (?, ?, ?)", (email, token, f'{email.split("@")[0]}-cadhub.db'))
        db.commit()
        db.close()
        
        # Copiar la base de datos base y renombrarla
        try:
            shutil.copy("cad_hub_base.db", f"{email.split('@')[0]}-cadhub.db")
        except FileNotFoundError:
            flash('Error: la base de datos "cad_hub_base.db" no se encontró.')
            return redirect(url_for('register'))
        except Exception as e:
            flash(f'Error al copiar la base de datos: {str(e)}')
            return redirect(url_for('register'))
        
        return redirect(url_for('register'))
    return redirect(url_for('login'))

def get_requester_ip():
    if request.headers.get('X-Forwarded-For'):
        # Para soportar aplicaciones detrás de un proxy como Nginx o Heroku
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip

def send_email(sender, recipient, confirm_url, requester_ip):
    msg = Message('CAD Hub: Completa tu registro', sender=sender, recipients=[recipient])
    msg.body = (
        f"🗝\n\n"
        f"Hola, soy Livrädo Sandoval de CAD Hub.\n\n"
        f"Estás a un clic de terminar tu registro en CAD Hub. Por favor, confirma tu correo "
        f"electrónico haciendo clic en el siguiente enlace:\n{confirm_url}\n\n"
        "💡 Consejo: ¿Quieres que CAD Hub recuerde tu contraseña la próxima vez?\n"
        "Acepta el recordatorio de contraseñas de tu navegador.\n\n"
        f"Este correo electrónico fue solicitado por {requester_ip}. Si no ha solicitado este registro, infórmenos a livrasand@outlook.com."
    )
    mail.send(msg)

@app.route('/confirm')
def confirm():
    return render_template('confirm.html') 

@app.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    # Crear una conexión directa a cavea.db
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE token = ?", (token,))
    result = cursor.fetchone()
    
    if result:
        email = result['email']
        if request.method == 'POST':
            password = request.form['password']
            
            # Actualizar la entrada en la base de datos con la contraseña y last_login
            now = datetime.datetime.now()
            logging.debug(f"Actualizando last_login a: {now}")
            cursor.execute("UPDATE users SET password = ?, last_login = ? WHERE email = ?", (password, now, email))
            conn.commit()
            conn.close()

            flash('Correo confirmado y contraseña establecida.')
            return redirect(url_for('login'))
        conn.close()
        return render_template('confirm.html', token=token)
    else:
        conn.close()
        flash('El enlace de confirmación es inválido o ha expirado.')
        return redirect(url_for('register'))

@app.route('/crear_evento', methods=['POST'])
def crear_evento():
    # Obtener el correo del usuario que está creando el evento desde sessionStorage
    usuario_correo = request.form.get('userEmail')

    if usuario_correo is None:
        # Si el correo del usuario no está en sessionStorage, redirige a alguna página de error o de inicio de sesión
        return redirect('/invalid')  # Por ejemplo, si el usuario necesita iniciar sesión primero

    # Generar un nuevo código de evento
    nuevo_codigo = generar_codigo_evento()

    # Guardar el nuevo código en la base de datos
    guardar_codigo_evento(usuario_correo, nuevo_codigo)

    # Crear una nueva base de datos con el nombre del código y copiar la estructura de cad_hub_base.db
    crear_nueva_base_datos(nuevo_codigo)

    return redirect(request.referrer or '/home')


def generar_codigo_evento():
    # Aquí puedes definir tu lógica para generar un código único, por ejemplo, utilizando el módulo uuid
    nuevo_codigo = str(uuid.uuid4()).replace('-', '').upper()[:5]  # Ejemplo de generación de código UUID

    return nuevo_codigo

def guardar_codigo_evento(usuario_correo, nuevo_codigo):
    # Establecer conexión con la base de datos principal
    conn_principal = sqlite3.connect('cad.db')
    cursor_principal = conn_principal.cursor()

    # Insertar el nuevo código en la tabla events_codes
    fecha_actual = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Añadir la extensión '.db' al nombre del código al guardarlo en la columna 'database'
    cursor_principal.execute("INSERT INTO events_codes (id, code, fecha, database) VALUES (?, ?, ?, ?)",
                              (usuario_correo, nuevo_codigo, fecha_actual, f"{nuevo_codigo}.db"))
    
    # Guardar los cambios y cerrar la conexión con la base de datos principal
    conn_principal.commit()
    conn_principal.close()

@app.route('/eliminar_evento/<codigo>', methods=['GET'])
def eliminar_evento(codigo):
    if not codigo:
        flash('Código de evento no proporcionado.')
        return redirect(url_for('home'))

    try:
        eliminar_codigo_evento(codigo)
        eliminar_base_datos_evento(codigo)
        flash('Evento eliminado exitosamente.')
        return redirect(request.referrer or url_for('home'))
    except Exception as e:
        flash(f'Error al eliminar el evento: {str(e)}')
        return redirect(request.referrer or url_for('home'))

def eliminar_codigo_evento(codigo):
    conn_principal = sqlite3.connect('cad.db')
    cursor_principal = conn_principal.cursor()
    cursor_principal.execute("DELETE FROM events_codes WHERE code = ?", (codigo,))
    conn_principal.commit()
    conn_principal.close()

def eliminar_base_datos_evento(codigo):
    db_name = f"{codigo}.db"
    try:
        os.remove(db_name)
    except FileNotFoundError:
        raise Exception(f'Error: la base de datos {db_name} no se encontró.')
    except Exception as e:
        raise Exception(f'Error al eliminar la base de datos: {str(e)}')

def crear_nueva_base_datos(nombre_codigo):
    # Copiar la estructura de la base de datos cad_hub_base.db a una nueva base de datos con el nombre del código
    shutil.copyfile('cad_hub_base.db', f'{nombre_codigo}.db')

    # Actualizar el nombre de la base de datos en la tabla events_codes
    conn_nueva_db = sqlite3.connect(f'{nombre_codigo}.db')
    
@app.route('/ver-informes', methods=['POST'])
def ver_informes():
    global current_database

    # Obtener el código del evento seleccionado del formulario
    event_code = request.form.get('evento')
    print("Código de evento recibido: ", event_code)

    if event_code:
        db = get_db()
        cursor = db.cursor()
        
        # Buscar la base de datos asociada al código del evento
        cursor.execute("SELECT id, database FROM events_codes WHERE code=?", (event_code,))
        row = cursor.fetchone()
        print("Base de datos recibida: ", row[1])
        if row:
            specific_database = row[1]
            current_database = specific_database  # Actualizar la variable global
            db.close()

            users = row[0]

            print("Administración de: ", users)

            try:
                new_db = sqlite3.connect(specific_database)
                cursor = new_db.cursor()
                return render_template('cad_admin_select.html', users=users)
            except sqlite3.Error as e:
                print(f"Error al conectar con la base de datos específica: {e}")
                return render_template('cad_admin_select.html', users=users)
        else:
            print("Base de datos no encontrada para el evento")
            return render_template('cad_admin_select.html', users=users)
    else:
        print("No se recibió el código del evento.")
        return render_template('cad_admin_select.html', users=users)


if __name__ == '__main__':
    app.run(debug=True)
