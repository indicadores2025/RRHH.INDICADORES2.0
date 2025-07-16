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

from datetime import timedelta

app.permanent_session_lifetime = timedelta(days=7)  # La sesión dura 7 días (puedes cambiarlo)
@app.before_request
def keep_session_alive():
    session.permanent = True


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

    from sqlalchemy import func
    from collections import OrderedDict
    import calendar
    from datetime import datetime

    unidades = Unidad.query.all()
    preguntas = Pregunta.query.all()

    preguntas_por_unidad = {}
    for u in unidades:
        preguntas_por_unidad[str(u.id)] = [
            {"id": p.id, "texto": p.texto}
            for p in preguntas if p.unidad_id == u.id or p.unidad_id is None
        ]
    todas_preguntas = [{"id": p.id, "texto": p.texto} for p in preguntas]

    if request.method == 'POST':
        unidad_id = request.form.get('unidad_id', 'todas')
        pregunta_ids = request.form.getlist('pregunta_id')
        tipo_periodo = request.form.get('tipo_periodo', 'mensual')
    else:
        unidad_id = 'todas'
        pregunta_ids = []
        tipo_periodo = 'mensual'

    query = db.session.query(
        Periodo.anio, Periodo.mes, Pregunta.id.label('pregunta_id'),
        Pregunta.texto, func.avg(Respuesta.valor).label('promedio')
    ).join(Respuesta, Respuesta.periodo_id == Periodo.id)\
     .join(Pregunta, Pregunta.id == Respuesta.pregunta_id)

    if unidad_id and unidad_id != 'todas':
        query = query.filter(Respuesta.unidad_id == int(unidad_id))
    if pregunta_ids:
        query = query.filter(Respuesta.pregunta_id.in_(pregunta_ids))

    query = query.group_by(Periodo.anio, Periodo.mes, Pregunta.id).order_by(Periodo.anio, Periodo.mes)
    resultados = query.all()

    ahora = datetime.now()
    anio_actual = ahora.year
    mes_actual = ahora.month

    etiquetas = []
    if tipo_periodo == 'mensual':
        etiquetas = [f"{m:02d}/{anio_actual}" for m in range(1, 13)]
    elif tipo_periodo == 'trimestral':
        etiquetas = [f"T{t}/{anio_actual}" for t in range(1, 5)]
    elif tipo_periodo == 'semestral':
        etiquetas = [f"S{s}/{anio_actual}" for s in range(1, 3)]
    elif tipo_periodo == 'anual':
        etiquetas = [str(anio_actual)]

    datos_grafico = OrderedDict()
    datos_proyeccion = OrderedDict()

    preguntas_filtradas = [p for p in preguntas if (not pregunta_ids or str(p.id) in pregunta_ids)]
    for p in preguntas_filtradas:
        valores = []
        for etiqueta in etiquetas:
            if tipo_periodo == 'mensual' and '/' in etiqueta:
                mes, anio = map(int, etiqueta.split('/'))
            elif tipo_periodo == 'trimestral' and etiqueta.startswith('T'):
                trimestre = int(etiqueta[1])
                mes = (trimestre - 1) * 3 + 1
                anio = anio_actual
            elif tipo_periodo == 'semestral' and etiqueta.startswith('S'):
                semestre = int(etiqueta[1])
                mes = (semestre - 1) * 6 + 1
                anio = anio_actual
            else:
                mes, anio = None, anio_actual

            promedio = next(
                (r.promedio for r in resultados if r.pregunta_id == p.id and r.anio == anio and (r.mes == mes or tipo_periodo != 'mensual')), None
            )
            valores.append(promedio)

        datos_grafico[p.texto] = valores

        # 🧠 Proyección: simular tendencia lineal con crecimiento
        proy = []
        valores_validos = [v for v in valores if v is not None]
        if len(valores_validos) >= 2:
            inicio = next((i for i, v in enumerate(valores) if v is not None), None)
            fin = max(i for i, v in enumerate(valores) if v is not None)
            delta = (valores[fin] - valores[inicio]) / max((fin - inicio), 1)
            for i, v in enumerate(valores):
                if v is not None:
                    proy.append(None)
                else:
                    proy.append(round(valores[fin] + delta * (i - fin), 2))
        else:
            ultimo_valor = valores_validos[-1] if valores_validos else None
            proy = [None if v is not None else ultimo_valor for v in valores]

        datos_proyeccion[p.texto] = proy

    return render_template('estadisticas.html',
                           unidad_id=unidad_id,
                           pregunta_ids=pregunta_ids,
                           tipo_periodo=tipo_periodo,
                           unidades=unidades,
                           todas_preguntas=todas_preguntas,
                           preguntas_por_unidad=preguntas_por_unidad,
                           etiquetas=etiquetas,
                           datos_grafico=datos_grafico,
                           datos_proyeccion=datos_proyeccion)

import pandas as pd
from flask import send_file, make_response
from xhtml2pdf import pisa
from io import BytesIO, StringIO

@app.route('/reporte_respuestas', methods=['GET', 'POST'])
@login_required
def reporte_respuestas():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    # Obtener listas para los selectores
    unidades = Unidad.query.order_by(Unidad.nombre).all()
    preguntas = Pregunta.query.order_by(Pregunta.texto).all()
    usuarios = Usuario.query.order_by(Usuario.usuario).all()
    periodos = Periodo.query.order_by(Periodo.anio.desc(), Periodo.mes.desc()).all()

    # Valores de filtro recibidos
    filtros = {
        'unidad_id': request.args.get('unidad_id') or request.form.get('unidad_id') or '',
        'pregunta_id': request.args.get('pregunta_id') or request.form.get('pregunta_id') or '',
        'usuario_id': request.args.get('usuario_id') or request.form.get('usuario_id') or '',
        'periodo_id': request.args.get('periodo_id') or request.form.get('periodo_id') or '',
        'respuesta': request.args.get('respuesta') or request.form.get('respuesta') or '',
    }

    # Construir consulta filtrada
    consulta = db.session.query(Respuesta, Unidad, Pregunta, Usuario, Periodo) \
        .join(Unidad, Unidad.id == Respuesta.unidad_id) \
        .join(Pregunta, Pregunta.id == Respuesta.pregunta_id) \
        .join(Usuario, Usuario.id == Respuesta.usuario_id) \
        .join(Periodo, Periodo.id == Respuesta.periodo_id)

    if filtros['unidad_id']:
        consulta = consulta.filter(Unidad.id == filtros['unidad_id'])
    if filtros['pregunta_id']:
        consulta = consulta.filter(Pregunta.id == filtros['pregunta_id'])
    if filtros['usuario_id']:
        consulta = consulta.filter(Usuario.id == filtros['usuario_id'])
    if filtros['periodo_id']:
        consulta = consulta.filter(Periodo.id == filtros['periodo_id'])
    if filtros['respuesta']:
        consulta = consulta.filter(Respuesta.valor.like(f"%{filtros['respuesta']}%"))

    # Ordenar por Unidad, Pregunta y Periodo descendente
    consulta = consulta.order_by(Unidad.nombre, Pregunta.texto, Periodo.anio.desc(), Periodo.mes.desc())
    respuestas = consulta.all()

    return render_template(
        'reporte_respuestas.html',
        respuestas=respuestas,
        unidades=unidades,
        preguntas=preguntas,
        usuarios=usuarios,
        periodos=periodos,
        filtros=filtros
    )


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

from flask import session

from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Pregunta, Respuesta, Periodo
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

    # ¿Ya respondió en este periodo?
    respuestas_anteriores = Respuesta.query.filter_by(usuario_id=current_user.id, periodo_id=periodo.id).all()
    if respuestas_anteriores:
        return render_template('responder.html', periodo=periodo, mensaje=mensaje, ya_respondio=True)

    # Construir todas las preguntas (nivel 1, 2, 3)
    preguntas_principales = Pregunta.query.filter(
        or_(Pregunta.unidad_id == current_user.unidad_id, Pregunta.unidad_id == None),
        Pregunta.nivel == 1
    ).order_by(Pregunta.id).all()

    todas_preguntas = []
    for p1 in preguntas_principales:
        todas_preguntas.append(p1)
        sub2 = Pregunta.query.filter_by(nivel=2, padre_id=p1.id).all()
        for p2 in sub2:
            todas_preguntas.append(p2)
            sub3 = Pregunta.query.filter_by(nivel=3, padre_id=p2.id).all()
            todas_preguntas.extend(sub3)

    # Estado temporal de respuestas
    if 'respuestas_tmp' not in session or session.get('tmp_periodo_id') != periodo.id:
        session['respuestas_tmp'] = {}
        session['tmp_periodo_id'] = periodo.id

    respuestas_tmp = session['respuestas_tmp']

    # Primer ingreso: responder una a una
    if len(respuestas_tmp) < len(todas_preguntas):
        for p in todas_preguntas:
            if str(p.id) not in respuestas_tmp:
                if request.method == 'POST':
                    valor = request.form.get(f"preg_{p.id}")
                    if valor is not None and valor != "":
                        respuestas_tmp[str(p.id)] = valor
                        session['respuestas_tmp'] = respuestas_tmp
                        return redirect(url_for('responder_preguntas'))
                return render_template('responder.html',
                                       periodo=periodo,
                                       pregunta=p,
                                       mensaje=mensaje,
                                       ya_respondio=False,
                                       editar=False,
                                       valor_actual=""
                )
    # Ya todas respondidas, pasa a confirmación
    return redirect(url_for('confirmar_respuestas'))


@app.route('/confirmar_respuestas', methods=['GET', 'POST'])
@login_required
def confirmar_respuestas():
    if current_user.rol != 'usuario':
        return redirect(url_for('admin_panel'))

    periodo = Periodo.query.filter_by(abierto=True).order_by(Periodo.anio.desc(), Periodo.mes.desc()).first()
    if not periodo:
        return redirect(url_for('responder_preguntas'))

    # ¿Ya respondió?
    respuestas_anteriores = Respuesta.query.filter_by(usuario_id=current_user.id, periodo_id=periodo.id).all()
    if respuestas_anteriores:
        return redirect(url_for('responder_preguntas'))

    # Todas las preguntas
    preguntas_principales = Pregunta.query.filter(
        or_(Pregunta.unidad_id == current_user.unidad_id, Pregunta.unidad_id == None),
        Pregunta.nivel == 1
    ).order_by(Pregunta.id).all()
    todas_preguntas = []
    for p1 in preguntas_principales:
        todas_preguntas.append(p1)
        sub2 = Pregunta.query.filter_by(nivel=2, padre_id=p1.id).all()
        for p2 in sub2:
            todas_preguntas.append(p2)
            sub3 = Pregunta.query.filter_by(nivel=3, padre_id=p2.id).all()
            todas_preguntas.extend(sub3)

    respuestas_tmp = session.get('respuestas_tmp', {})
    preguntas_confirmar = []
    for p in todas_preguntas:
        preguntas_confirmar.append({
            "id": p.id,
            "texto": p.texto,
            "tipo": p.tipo,
            "valor": respuestas_tmp.get(str(p.id), "")
        })

    # Guardar edición de una sola pregunta
    if request.method == 'POST' and 'editar_id' in request.form:
        editar_id = request.form['editar_id']
        valor_editar = request.form.get(f"valor_editar_{editar_id}", "")
        if valor_editar != "":
            respuestas_tmp[editar_id] = valor_editar
            session['respuestas_tmp'] = respuestas_tmp
        return redirect(url_for('confirmar_respuestas'))

    # Guardar DEFINITIVAMENTE todas las respuestas
    if request.method == 'POST' and 'confirmar' in request.form:
        for pregunta_id, valor in respuestas_tmp.items():
            nueva_respuesta = Respuesta(
                usuario_id=current_user.id,
                pregunta_id=int(pregunta_id),
                unidad_id=current_user.unidad_id,
                periodo_id=periodo.id,
                valor=valor,
                fecha_registro=datetime.utcnow()
            )
            db.session.add(nueva_respuesta)
        db.session.commit()
        session.pop('respuestas_tmp', None)
        session.pop('tmp_periodo_id', None)
        return render_template('responder.html', periodo=periodo, mensaje="¡Tus respuestas fueron enviadas correctamente!", ya_respondio=True)

    # Si viene una petición de edición (mostrar input en la tabla)
    editar_id = request.args.get("editar")
    return render_template(
        'confirmar_respuestas.html',
        periodo=periodo,
        preguntas=preguntas_confirmar,
        editar_id=editar_id
    )

@app.route('/graficos', methods=['GET', 'POST'])
@login_required
def graficos():
    from sqlalchemy import func

    unidades = Unidad.query.all()
    preguntas = Pregunta.query.all()

    # --- Agrupa preguntas por unidad ---
    preguntas_por_unidad = {}
    for u in unidades:
        preguntas_por_unidad[str(u.id)] = [
            {"id": p.id, "texto": p.texto}
            for p in preguntas if p.unidad_id == u.id or p.unidad_id is None
        ]
    todas_preguntas = [{"id": p.id, "texto": p.texto} for p in preguntas]

    # --- Parámetros por POST ---
    if request.method == 'POST':
        unidad_id = request.form.get('unidad_id', 'todas')
        pregunta_ids = request.form.getlist('pregunta_id')
        tipo_grafico = request.form.get('tipo_grafico', 'bar')
        tipo_periodo = request.form.get('tipo_periodo', 'mensual')
    else:
        unidad_id = 'todas'
        pregunta_ids = []
        tipo_grafico = 'bar'
        tipo_periodo = 'mensual'

    # --- Consulta resultados según filtros ---
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

    # --- Armado de etiquetas según tipo_periodo ---
    from collections import OrderedDict
    def mes_nombre(mes):
        meses = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return meses[mes]

    etiquetas = []
    if tipo_periodo == 'mensual':
        etiquetas = sorted(list({f"{r.mes:02d}/{r.anio}" for r in resultados}))
    elif tipo_periodo == 'trimestral':
        etiquetas = sorted(list({f"T{((r.mes-1)//3)+1}/{r.anio}" for r in resultados}))
    elif tipo_periodo == 'semestral':
        etiquetas = sorted(list({f"S{((r.mes-1)//6)+1}/{r.anio}" for r in resultados}))
    elif tipo_periodo == 'anual':
        etiquetas = sorted(list({f"{r.anio}" for r in resultados}))

    # --- Preparar datos para el gráfico ---
    datos_grafico = OrderedDict()
    for p in preguntas:
        if pregunta_ids and str(p.id) not in pregunta_ids:
            continue
        serie = []
        for etiqueta in etiquetas:
            if tipo_periodo == 'mensual':
                mes, anio = map(int, etiqueta.split('/'))
                valor = next((r.promedio for r in resultados if r.pregunta_id == p.id and r.mes == mes and r.anio == anio), None)
            elif tipo_periodo == 'trimestral':
                t, anio = etiqueta.split('/')
                trimestre = int(t[1])
                valor = [r.promedio for r in resultados if r.pregunta_id == p.id and r.anio == int(anio) and ((r.mes-1)//3+1) == trimestre]
                valor = sum(valor)/len(valor) if valor else None
            elif tipo_periodo == 'semestral':
                s, anio = etiqueta.split('/')
                semestre = int(s[1])
                valor = [r.promedio for r in resultados if r.pregunta_id == p.id and r.anio == int(anio) and ((r.mes-1)//6+1) == semestre]
                valor = sum(valor)/len(valor) if valor else None
            elif tipo_periodo == 'anual':
                anio = int(etiqueta)
                valor = [r.promedio for r in resultados if r.pregunta_id == p.id and r.anio == anio]
                valor = sum(valor)/len(valor) if valor else None
            serie.append(valor)
        datos_grafico[p.texto] = serie

    return render_template(
        "graficos.html",
        unidades=unidades,
        preguntas=[],  # Solo las carga JS
        preguntas_por_unidad=preguntas_por_unidad,
        todas_preguntas=todas_preguntas,
        unidad_id=unidad_id,
        pregunta_ids=pregunta_ids,
        tipo_grafico=tipo_grafico,
        tipo_periodo=tipo_periodo,
        etiquetas=etiquetas,
        datos_grafico=datos_grafico,
    )


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

from flask import request, send_file
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import base64
from io import BytesIO

from flask import request, send_file
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader
import base64
from io import BytesIO

@app.route('/exportar_grafico_pdf', methods=['POST'])
@login_required
def exportar_grafico_pdf():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))
    import base64
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from io import BytesIO

    img_data = request.form['grafico_img'].split(',')[1]
    img_bytes = BytesIO(base64.b64decode(img_data))
    pdf_bytes = BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=landscape(A4))
    # Ajusta el tamaño del gráfico para que no se deforme
    c.drawImage(ImageReader(img_bytes), 40, 90, width=750, height=320, preserveAspectRatio=True, mask='auto')
    c.save()
    pdf_bytes.seek(0)
    return send_file(pdf_bytes, as_attachment=True, download_name="grafico.pdf", mimetype="application/pdf")

@app.route('/api/preguntas_unidad/<unidad_id>')
@login_required
def preguntas_por_unidad(unidad_id):
    if unidad_id == 'todas':
        preguntas = Pregunta.query.order_by(Pregunta.texto.asc()).all()
    else:
        preguntas = Pregunta.query.filter(
            (Pregunta.unidad_id == int(unidad_id)) | (Pregunta.unidad_id == None)
        ).order_by(Pregunta.texto.asc()).all()
    return {
        "preguntas": [
            {"id": p.id, "texto": p.texto}
            for p in preguntas
        ]
    }

@app.route('/respuestas/editar/<int:respuesta_id>', methods=['GET', 'POST'])
@login_required
def editar_respuesta(respuesta_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    respuesta = Respuesta.query.get_or_404(respuesta_id)
    pregunta = Pregunta.query.get(respuesta.pregunta_id)
    usuario = Usuario.query.get(respuesta.usuario_id)
    periodo = Periodo.query.get(respuesta.periodo_id)
    mensaje = ""

    if request.method == 'POST':
        nuevo_valor = request.form.get('valor')
        if nuevo_valor is not None and nuevo_valor != "":
            respuesta.valor = nuevo_valor
            db.session.commit()
            mensaje = "¡Respuesta editada exitosamente!"
            return redirect(url_for('reporte_respuestas'))
        else:
            mensaje = "El valor no puede estar vacío."

    return render_template(
        'editar_respuesta.html',
        respuesta=respuesta,
        pregunta=pregunta,
        usuario=usuario,
        periodo=periodo,
        mensaje=mensaje
    )

@app.route('/respuestas/eliminar/<int:respuesta_id>', methods=['POST'])
@login_required
def eliminar_respuesta(respuesta_id):
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    respuesta = Respuesta.query.get_or_404(respuesta_id)
    db.session.delete(respuesta)
    db.session.commit()
    return redirect(url_for('reporte_respuestas'))

import pandas as pd
from flask import send_file
from io import BytesIO
from xhtml2pdf import pisa
from flask import render_template, make_response

@app.route('/reporte_respuestas/excel')
@login_required
def exportar_respuestas_excel():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    respuestas = db.session.query(Respuesta, Unidad, Pregunta, Usuario, Periodo) \
        .join(Unidad, Unidad.id == Respuesta.unidad_id) \
        .join(Pregunta, Pregunta.id == Respuesta.pregunta_id) \
        .join(Usuario, Usuario.id == Respuesta.usuario_id) \
        .join(Periodo, Periodo.id == Respuesta.periodo_id) \
        .order_by(Unidad.nombre, Pregunta.texto, Usuario.usuario, Periodo.anio, Periodo.mes) \
        .all()

    data = []
    for r, unidad, pregunta, usuario, periodo in respuestas:
        data.append([
            unidad.nombre, pregunta.texto, usuario.usuario,
            f"{periodo.mes:02d}/{periodo.anio}", r.valor
        ])
    df = pd.DataFrame(data, columns=['Unidad', 'Pregunta', 'Usuario', 'Periodo', 'Respuesta'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Respuestas')
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="reporte_respuestas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route('/reporte_respuestas/pdf')
@login_required
def exportar_respuestas_pdf():
    if current_user.rol != 'admin':
        return redirect(url_for('usuario_panel'))

    respuestas = db.session.query(Respuesta, Unidad, Pregunta, Usuario, Periodo) \
        .join(Unidad, Unidad.id == Respuesta.unidad_id) \
        .join(Pregunta, Pregunta.id == Respuesta.pregunta_id) \
        .join(Usuario, Usuario.id == Respuesta.usuario_id) \
        .join(Periodo, Periodo.id == Respuesta.periodo_id) \
        .order_by(Unidad.nombre, Pregunta.texto, Usuario.usuario, Periodo.anio, Periodo.mes) \
        .all()

    rendered = render_template("reporte_respuestas_pdf.html", respuestas=respuestas)
    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(rendered.encode('utf-8')), dest=pdf)
    pdf.seek(0)
    return send_file(
        pdf,
        as_attachment=True,
        download_name="reporte_respuestas.pdf",
        mimetype="application/pdf"
    )

@app.route('/cambiar_contrasena', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena():
    mensaje = ""
    error = ""
    if request.method == 'POST':
        actual = request.form.get('contrasena_actual')
        nueva = request.form.get('nueva_contrasena')
        repetir = request.form.get('repetir_contrasena')
        # Validar la contraseña actual
        if actual != current_user.password:
            error = "La contraseña actual no es correcta."
        elif not nueva or not repetir:
            error = "Debes ingresar la nueva contraseña dos veces."
        elif nueva != repetir:
            error = "La nueva contraseña no coincide en ambos campos."
        elif nueva == actual:
            error = "La nueva contraseña debe ser diferente de la actual."
        else:
            # Actualiza la contraseña
            user = Usuario.query.get(current_user.id)
            user.password = nueva
            db.session.commit()
            mensaje = "¡Contraseña cambiada correctamente!"
    return render_template('cambiar_contrasena.html', mensaje=mensaje, error=error)

@app.route('/estadisticas_descriptivas', methods=['GET', 'POST'])
@login_required
def estadisticas_descriptivas():
    from sqlalchemy import func
    import numpy as np

    unidades = Unidad.query.all()

    unidad_id = request.form.get('unidad_id') if request.method == 'POST' else 'todas'
    pregunta_id = request.form.get('pregunta_id') if request.method == 'POST' else 'todas'

    # --- Para el filtro dinámico de preguntas ---
    if unidad_id and unidad_id != 'todas':
        preguntas = Pregunta.query.filter(
            (Pregunta.unidad_id == int(unidad_id)) | (Pregunta.unidad_id == None)
        ).order_by(Pregunta.texto.asc()).all()
    else:
        preguntas = Pregunta.query.order_by(Pregunta.texto.asc()).all()

    resultados = {}
    meses_calculados = []

    if request.method == 'POST' and pregunta_id and pregunta_id != 'todas':
        # Extrae valores y meses
        query = db.session.query(Respuesta.valor, Periodo.mes, Periodo.anio)\
            .join(Pregunta).join(Unidad).join(Periodo)
        if unidad_id and unidad_id != 'todas':
            query = query.filter(Respuesta.unidad_id == int(unidad_id))
        if pregunta_id and pregunta_id != 'todas':
            query = query.filter(Respuesta.pregunta_id == int(pregunta_id))
        datos_query = query.all()
        datos = [float(x[0]) for x in datos_query if x[0] is not None and str(x[0]).replace(".", "", 1).isdigit()]

        meses_set = set()
        for val, mes, anio in datos_query:
            if val is not None and str(val).replace(".", "", 1).isdigit():
                meses_set.add(f"{mes:02d}-{anio}")
        meses_calculados = sorted(meses_set)

        if datos:
            resultados = {
                "promedio": round(np.mean(datos), 2),
                "mediana": round(np.median(datos), 2),
                "maximo": round(np.max(datos), 2),
                "minimo": round(np.min(datos), 2),
                "suma": round(np.sum(datos), 2),
                "desviacion": round(np.std(datos), 2),
                "conteo": len(datos)
            }
        else:
            resultados = {"mensaje": "No hay datos para calcular."}

    return render_template(
        "estadisticas_descriptivas.html",
        unidades=unidades,
        preguntas=preguntas,
        resultados=resultados,
        unidad_id=unidad_id,
        pregunta_id=pregunta_id,
        meses_calculados=meses_calculados
    )

@app.route('/api/preguntas_por_unidad/<unidad_id>')
def api_preguntas_por_unidad(unidad_id):
    from models import Pregunta
    if unidad_id == 'todas':
        preguntas = Pregunta.query.order_by(Pregunta.texto.asc()).all()
    else:
        preguntas = Pregunta.query.filter(
            (Pregunta.unidad_id == int(unidad_id)) | (Pregunta.unidad_id == None)
        ).order_by(Pregunta.texto.asc()).all()
    return {
        "preguntas": [
            {"id": p.id, "texto": p.texto}
            for p in preguntas
        ]
    }


# ------------------- MAIN -------------------

if __name__ == "__main__":
    app.run(debug=True)
