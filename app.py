from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Usuario, Unidad, Pregunta, Periodo, Respuesta
from sqlalchemy import func
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'supersecreto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# --------------------- LOGIN ---------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        user = Usuario.query.filter_by(usuario=usuario, password=password, activo=True).first()
        if user:
            login_user(user)
            if user.rol == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('usuario_panel'))
        else:
            error = "Usuario o contraseña incorrectos, o usuario inactivo."
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ------------------- PANEL ADMIN Y USUARIO -------------------

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))
    return render_template('admin_panel.html', usuario=current_user.usuario)

@app.route('/usuario')
@login_required
def usuario_panel():
    if current_user.rol != 'usuario':
        return redirect(url_for('admin_panel'))
    return render_template('usuario_panel.html', usuario=current_user.usuario)

# ------------------- GESTIÓN DE UNIDADES -------------------

@app.route('/unidades', methods=['GET', 'POST'])
@login_required
def gestion_unidades():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    error = request.args.get("error", "")
    mensaje = ""

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if not nombre:
            mensaje = "El nombre de la unidad no puede estar vacío."
        elif Unidad.query.filter_by(nombre=nombre).first():
            mensaje = "¡Ya existe una unidad con ese nombre!"
        else:
            nueva_unidad = Unidad(nombre=nombre)
            db.session.add(nueva_unidad)
            db.session.commit()
            mensaje = "Unidad creada exitosamente."

    unidades = Unidad.query.order_by(Unidad.fecha_creacion.desc()).all()
    return render_template('unidades.html', unidades=unidades, mensaje=mensaje, error=error, usuario=current_user.usuario)

@app.route('/unidades/editar/<int:unidad_id>', methods=['POST'])
@login_required
def editar_unidad(unidad_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    nombre = request.form['nombre'].strip()
    if not nombre:
        return redirect(url_for('gestion_unidades'))

    unidad = Unidad.query.get_or_404(unidad_id)
    if Unidad.query.filter(Unidad.nombre == nombre, Unidad.id != unidad_id).first():
        return redirect(url_for('gestion_unidades', error="Ya existe una unidad con ese nombre."))

    unidad.nombre = nombre
    db.session.commit()
    return redirect(url_for('gestion_unidades'))

@app.route('/unidades/eliminar/<int:unidad_id>', methods=['POST'])
@login_required
def eliminar_unidad(unidad_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))
    unidad = Unidad.query.get_or_404(unidad_id)
    db.session.delete(unidad)
    db.session.commit()
    return redirect(url_for('gestion_unidades'))

# ------------------- GESTIÓN DE USUARIOS -------------------

@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def gestion_usuarios():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    mensaje = ""
    error = ""
    unidades = Unidad.query.order_by(Unidad.nombre.asc()).all()

    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        password = request.form['password'].strip()
        rol = request.form['rol']
        activo = request.form.get('activo') == 'on'
        unidad_id = request.form.get('unidad_id')
        if unidad_id == '': unidad_id = None

        if not usuario or not password or not rol:
            error = "Todos los campos obligatorios deben estar completos."
        elif Usuario.query.filter_by(usuario=usuario).first():
            error = "Ya existe un usuario con ese nombre."
        else:
            nuevo_usuario = Usuario(
                usuario=usuario,
                password=password,
                rol=rol,
                activo=activo,
                unidad_id=unidad_id
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            mensaje = "Usuario creado correctamente."

    usuarios = Usuario.query.order_by(Usuario.usuario.asc()).all()
    return render_template('usuarios.html', usuarios=usuarios, mensaje=mensaje, error=error, unidades=unidades)

@app.route('/usuarios/activar/<int:usuario_id>')
@login_required
def activar_usuario(usuario_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.activo = True
    db.session.commit()
    return redirect(url_for('gestion_usuarios'))

@app.route('/usuarios/desactivar/<int:usuario_id>')
@login_required
def desactivar_usuario(usuario_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.activo = False
    db.session.commit()
    return redirect(url_for('gestion_usuarios'))

@app.route('/usuarios/editar/<int:usuario_id>', methods=['POST'])
@login_required
def editar_usuario(usuario_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.usuario = request.form['usuario'].strip()
    usuario.password = request.form['password'].strip()
    usuario.rol = request.form['rol']
    usuario.unidad_id = request.form.get('unidad_id')
    if usuario.unidad_id == '': usuario.unidad_id = None
    usuario.activo = request.form.get('activo') == 'on'
    db.session.commit()
    return redirect(url_for('gestion_usuarios'))

# ------------------- GESTIÓN DE PREGUNTAS -------------------

# ------------------- CONTROL DE PERIODOS -------------------

@app.route('/periodos', methods=['GET', 'POST'])
@login_required
def control_periodos():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    mensaje = ""
    error = ""

    if request.method == 'POST':
        mes = int(request.form['mes'])
        anio = int(request.form['anio'])
        accion = request.form['accion']

        periodo = Periodo.query.filter_by(mes=mes, anio=anio).first()
        ahora = datetime.now()

        if accion == "abrir":
            if periodo:
                if periodo.abierto:
                    error = f"El período {mes:02d}/{anio} ya está abierto."
                else:
                    periodo.abierto = True
                    periodo.fecha_apertura = ahora
                    periodo.fecha_cierre = None
                    db.session.commit()
                    mensaje = f"Período {mes:02d}/{anio} abierto correctamente."
            else:
                nuevo = Periodo(mes=mes, anio=anio, abierto=True, fecha_apertura=ahora)
                db.session.add(nuevo)
                db.session.commit()
                mensaje = f"Período {mes:02d}/{anio} creado y abierto."
        elif accion == "cerrar":
            if periodo and periodo.abierto:
                periodo.abierto = False
                periodo.fecha_cierre = ahora
                db.session.commit()
                mensaje = f"Período {mes:02d}/{anio} cerrado correctamente."
            else:
                error = f"El período {mes:02d}/{anio} no está abierto o no existe."

    periodos = Periodo.query.order_by(Periodo.anio.desc(), Periodo.mes.desc()).all()
    return render_template('periodos.html', periodos=periodos, mensaje=mensaje, error=error)

# ------------------- ESTADÍSTICAS -------------------

@app.route('/estadisticas', methods=['GET', 'POST'])
@login_required
def estadisticas():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    # Parámetros de filtro (si vienen del formulario)
    unidad_id = request.form.get('unidad_id') if request.method == 'POST' else None
    pregunta_ids = request.form.getlist('pregunta_id') if request.method == 'POST' else []
    periodos = Periodo.query.order_by(Periodo.anio.desc(), Periodo.mes.desc()).all()

    # Filtra preguntas según unidad (solo las asignadas a la unidad o globales)
    if unidad_id and unidad_id != 'todas':
        preguntas = Pregunta.query.filter(
            (Pregunta.unidad_id == int(unidad_id)) | (Pregunta.unidad_id == None)
        ).all()
    else:
        preguntas = Pregunta.query.all()
    unidades = Unidad.query.all()

    # Filtro de respuestas
    query = db.session.query(
        Periodo.anio, Periodo.mes, Pregunta.id.label('pregunta_id'), Pregunta.texto, func.avg(Respuesta.valor).label('promedio')
    ).join(Respuesta, Respuesta.periodo_id == Periodo.id)\
     .join(Pregunta, Pregunta.id == Respuesta.pregunta_id)

    if unidad_id and unidad_id != 'todas':
        query = query.filter(Respuesta.unidad_id == int(unidad_id))
    if pregunta_ids:
        query = query.filter(Respuesta.pregunta_id.in_(pregunta_ids))

    query = query.group_by(Periodo.anio, Periodo.mes, Pregunta.id).order_by(Periodo.anio, Periodo.mes)
    resultados = query.all()

    # Proyección simple a fin de año para cada pregunta seleccionada
    proyeccion = {}
    if resultados:
        # Agrupa resultados por pregunta y año
        for preg in preguntas:
            datos_preg = [r for r in resultados if r.pregunta_id == preg.id]
            if datos_preg:
                ultimo_anio = max(r.anio for r in datos_preg)
                ultimo_mes = max(r.mes for r in datos_preg if r.anio == ultimo_anio)
                promedio_anual = sum(r.promedio for r in datos_preg if r.anio == ultimo_anio) / len([r for r in datos_preg if r.anio == ultimo_anio])
                # Proyecta meses faltantes del año
                for m in range(ultimo_mes + 1, 13):
                    proyeccion[(ultimo_anio, m, preg.id)] = promedio_anual

    return render_template('estadisticas.html',
                           unidades=unidades,
                           preguntas=preguntas,
                           periodos=periodos,
                           resultados=resultados,
                           proyeccion=proyeccion,
                           unidad_id=unidad_id,
                           pregunta_ids=pregunta_ids)

import pandas as pd
from flask import send_file, make_response
from xhtml2pdf import pisa
from io import BytesIO, StringIO

@app.route('/reporte_respuestas', methods=['GET'])
@login_required
def reporte_respuestas():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    # Consulta todas las respuestas, ordenadas por unidad, pregunta, usuario, periodo
    respuestas = db.session.query(
        Unidad.nombre.label('Unidad'),
        Pregunta.texto.label('Pregunta'),
        Usuario.usuario.label('Usuario'),
        Periodo.mes,
        Periodo.anio,
        Respuesta.valor
    ).join(Pregunta, Pregunta.id == Respuesta.pregunta_id) \
     .join(Unidad, Unidad.id == Respuesta.unidad_id) \
     .join(Usuario, Usuario.id == Respuesta.usuario_id) \
     .join(Periodo, Periodo.id == Respuesta.periodo_id) \
     .order_by(Unidad.nombre, Pregunta.texto, Usuario.usuario, Periodo.anio, Periodo.mes).all()

    return render_template('reporte_respuestas.html', respuestas=respuestas)

@app.route('/descargar_excel')
@login_required
def descargar_excel():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    # Igual que arriba, pero formato DataFrame
    respuestas = db.session.query(
        Unidad.nombre.label('Unidad'),
        Pregunta.texto.label('Pregunta'),
        Usuario.usuario.label('Usuario'),
        Periodo.mes,
        Periodo.anio,
        Respuesta.valor
    ).join(Pregunta, Pregunta.id == Respuesta.pregunta_id) \
     .join(Unidad, Unidad.id == Respuesta.unidad_id) \
     .join(Usuario, Usuario.id == Respuesta.usuario_id) \
     .join(Periodo, Periodo.id == Respuesta.periodo_id) \
     .order_by(Unidad.nombre, Pregunta.texto, Usuario.usuario, Periodo.anio, Periodo.mes).all()

    df = pd.DataFrame(respuestas, columns=["Unidad", "Pregunta", "Usuario", "Mes", "Año", "Respuesta"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Respuestas')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="reporte_respuestas.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/descargar_pdf')
@login_required
def descargar_pdf():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    respuestas = db.session.query(
        Unidad.nombre.label('Unidad'),
        Pregunta.texto.label('Pregunta'),
        Usuario.usuario.label('Usuario'),
        Periodo.mes,
        Periodo.anio,
        Respuesta.valor
    ).join(Pregunta, Pregunta.id == Respuesta.pregunta_id) \
     .join(Unidad, Unidad.id == Respuesta.unidad_id) \
     .join(Usuario, Usuario.id == Respuesta.usuario_id) \
     .join(Periodo, Periodo.id == Respuesta.periodo_id) \
     .order_by(Unidad.nombre, Pregunta.texto, Usuario.usuario, Periodo.anio, Periodo.mes).all()

    # Renderizar tabla HTML
    rendered = render_template('reporte_respuestas_pdf.html', respuestas=respuestas)
    pdf = BytesIO()
    pisa.CreatePDF(StringIO(rendered), dest=pdf)
    pdf.seek(0)
    return send_file(pdf, as_attachment=True, download_name="reporte_respuestas.pdf", mimetype="application/pdf")

from flask_login import current_user
from sqlalchemy import and_
from datetime import datetime

from sqlalchemy import or_

@app.route('/responder', methods=['GET', 'POST'])
@login_required
def responder_preguntas():
    if current_user.rol != 'usuario':
        return redirect(url_for('admin_panel'))

    periodo = Periodo.query.filter_by(abierto=True).order_by(Periodo.anio.desc(), Periodo.mes.desc()).first()
    mensaje = ""
    ya_respondio = False

    if not periodo:
        return render_template('responder.html', periodo=None, mensaje=mensaje, ya_respondio=False)

    # Paso 1: Busca la lista de preguntas principales asignadas a la unidad del usuario
    preguntas_principales = Pregunta.query.filter(
        or_(Pregunta.unidad_id == current_user.unidad_id, Pregunta.unidad_id == None),
        Pregunta.nivel == 1
    ).order_by(Pregunta.id).all()

    # Obtén todas las respuestas previas de este usuario/periodo
    respuestas_previas = Respuesta.query.filter_by(usuario_id=current_user.id, periodo_id=periodo.id).all()
    respuestas_dict = {r.pregunta_id: r for r in respuestas_previas}

    # Si ya respondió todas las preguntas del flujo, no puede responder más
    total_preguntas = 0
    for pregunta1 in preguntas_principales:
        total_preguntas += 1
        subpregs = Pregunta.query.filter_by(nivel=2, padre_id=pregunta1.id).all()
        for sp in subpregs:
            total_preguntas += 1
            subsubpregs = Pregunta.query.filter_by(nivel=3, padre_id=sp.id).all()
            total_preguntas += len(subsubpregs)
    if len(respuestas_dict) >= total_preguntas:
        return render_template('responder.html', periodo=periodo, mensaje=mensaje, ya_respondio=True)

    # Determina cuál es la próxima pregunta a responder en el flujo
    pregunta = None
    # 1. Encuentra la primera pregunta principal sin responder
    for pregunta1 in preguntas_principales:
        if pregunta1.id not in respuestas_dict:
            pregunta = pregunta1
            break
        # 2. Busca si tiene subpregunta sin responder
        subpregs = Pregunta.query.filter_by(nivel=2, padre_id=pregunta1.id).all()
        for sp in subpregs:
            if sp.id not in respuestas_dict:
                pregunta = sp
                break
            # 3. Busca sub-subpreguntas sin responder
            subsubpregs = Pregunta.query.filter_by(nivel=3, padre_id=sp.id).all()
            for ssp in subsubpregs:
                if ssp.id not in respuestas_dict:
                    pregunta = ssp
                    break
            if pregunta: break
        if pregunta: break

    # Si POST, guardar la respuesta actual y refrescar el flujo
    if request.method == 'POST' and pregunta:
        valor = request.form.get(f"preg_{pregunta.id}")
        if valor is not None and valor != "":
            nueva_respuesta = Respuesta(
                usuario_id=current_user.id,
                pregunta_id=pregunta.id,
                unidad_id=current_user.unidad_id,
                periodo_id=periodo.id,
                valor=valor,  # string, acepta texto o número
                fecha_registro=datetime.utcnow()
            )
            db.session.add(nueva_respuesta)
            db.session.commit()
            # Recargar para mostrar la siguiente pregunta del flujo
            return redirect(url_for('responder_preguntas'))

    return render_template('responder.html',
                           periodo=periodo,
                           pregunta=pregunta,
                           mensaje=mensaje,
                           ya_respondio=False)

@app.route('/graficos', methods=['GET', 'POST'])
@login_required
def graficos():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    from sqlalchemy import func

    unidades = Unidad.query.all()
    preguntas = Pregunta.query.all()
    periodos = Periodo.query.order_by(Periodo.anio, Periodo.mes).all()

    unidad_id = request.form.get('unidad_id') if request.method == 'POST' else None
    pregunta_ids = request.form.getlist('pregunta_id') if request.method == 'POST' else []
    tipo_grafico = request.form.get('tipo_grafico') if request.method == 'POST' else 'bar'

    # Filtro por unidad y preguntas
    query = db.session.query(
        Periodo.anio, Periodo.mes, Pregunta.id.label('pregunta_id'), Pregunta.texto, func.avg(Respuesta.valor).label('promedio')
    ).join(Respuesta, Respuesta.periodo_id == Periodo.id)\
     .join(Pregunta, Pregunta.id == Respuesta.pregunta_id)

    if unidad_id and unidad_id != 'todas':
        query = query.filter(Respuesta.unidad_id == int(unidad_id))
    if pregunta_ids:
        query = query.filter(Respuesta.pregunta_id.in_(pregunta_ids))
    query = query.group_by(Periodo.anio, Periodo.mes, Pregunta.id).order_by(Periodo.anio, Periodo.mes)
    resultados = query.all()

    # Prepara datos para la gráfica
    etiquetas = sorted(list({f"{r.mes:02d}/{r.anio}" for r in resultados}))
    datos_grafico = {}
    for p in preguntas:
        if pregunta_ids and str(p.id) not in pregunta_ids:
            continue
        serie = []
        for etiqueta in etiquetas:
            mes, anio = map(int, etiqueta.split('/'))
            valor = next((r.promedio for r in resultados if r.pregunta_id == p.id and r.mes == mes and r.anio == anio), None)
            serie.append(valor)
        datos_grafico[p.texto] = serie

    return render_template('graficos.html',
                           unidades=unidades,
                           preguntas=preguntas,
                           etiquetas=etiquetas,
                           datos_grafico=datos_grafico,
                           unidad_id=unidad_id,
                           pregunta_ids=pregunta_ids,
                           tipo_grafico=tipo_grafico)

@app.route('/gestion_preguntas', methods=['GET', 'POST'])
@login_required
def gestion_preguntas():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    mensaje = ""
    error = ""
    unidades = Unidad.query.order_by(Unidad.nombre.asc()).all()
    usuarios = Usuario.query.filter(Usuario.rol == 'usuario').order_by(Usuario.usuario.asc()).all()
    preguntas_principales = Pregunta.query.filter_by(nivel=1).all()
    preguntas = Pregunta.query.order_by(Pregunta.nivel, Pregunta.padre_id, Pregunta.id).all()

    if request.method == 'POST':
        texto = request.form['texto']
        tipo = request.form['tipo']
        nivel = int(request.form['nivel'])
        padre_id = request.form.get('padre_id')
        unidad_id = request.form.get('unidad_id') or None
        usuario_id = request.form.get('usuario_id') or None

        if not texto or not tipo or not nivel:
            error = "Todos los campos obligatorios."
        else:
            nueva_pregunta = Pregunta(
                texto=texto,
                tipo=tipo,
                nivel=nivel,
                padre_id=int(padre_id) if padre_id else None,
                unidad_id=int(unidad_id) if unidad_id else None,
                usuario_id=int(usuario_id) if usuario_id else None,
            )
            db.session.add(nueva_pregunta)
            db.session.commit()
            mensaje = "Pregunta agregada correctamente."

    return render_template(
        'gestion_preguntas.html',
        mensaje=mensaje,
        error=error,
        unidades=unidades,
        usuarios=usuarios,
        preguntas_principales=preguntas_principales,
        preguntas=preguntas
    )

@app.route('/preguntas/editar/<int:pregunta_id>', methods=['GET', 'POST'])
@login_required
def editar_pregunta(pregunta_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    pregunta = Pregunta.query.get_or_404(pregunta_id)
    unidades = Unidad.query.all()
    usuarios = Usuario.query.filter(Usuario.rol == 'usuario').all()
    preguntas_principales = Pregunta.query.filter_by(nivel=1).all()
    mensaje = ""

    if request.method == 'POST':
        pregunta.texto = request.form['texto']
        pregunta.tipo = request.form['tipo']
        pregunta.nivel = int(request.form['nivel'])
        padre_id = request.form.get('padre_id') or None
        pregunta.padre_id = int(padre_id) if padre_id else None
        unidad_id = request.form.get('unidad_id') or None
        pregunta.unidad_id = int(unidad_id) if unidad_id else None
        usuario_id = request.form.get('usuario_id') or None
        pregunta.usuario_id = int(usuario_id) if usuario_id else None

        db.session.commit()
        mensaje = "Pregunta editada correctamente."
        return redirect(url_for('gestion_preguntas'))

    return render_template('editar_pregunta.html',
                           pregunta=pregunta,
                           unidades=unidades,
                           usuarios=usuarios,
                           preguntas_principales=preguntas_principales,
                           mensaje=mensaje)

@app.route('/preguntas/eliminar/<int:pregunta_id>', methods=['POST'])
@login_required
def eliminar_pregunta(pregunta_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    pregunta = Pregunta.query.get_or_404(pregunta_id)
    db.session.delete(pregunta)
    db.session.commit()
    return redirect(url_for('gestion_preguntas'))

# ------------------- MAIN -------------------

if __name__ == "__main__":
    app.run(debug=True)
