import pandas as pd
from app import db
from models import Unidad, Pregunta, Usuario, Periodo, Respuesta
from datetime import datetime

def cargar_respuestas():
    archivo = "respuestas.xlsx"
    hoja = "RESPUESTAS"
    try:
        df = pd.read_excel(archivo, sheet_name=hoja)
    except Exception as e:
        print(f"Error leyendo el archivo: {e}")
        return

    errores = 0
    cargadas = 0
    for idx, fila in df.iterrows():
        try:
            nombre_unidad = str(fila['Unidad']).strip()
            texto_pregunta = str(fila['Pregunta']).strip()
            usuario_nombre = str(fila['Usuario']).strip()
            mes = int(fila['Mes'])
            anio = int(fila['Año'])
            valor = fila['Respuesta']

            # Busca la unidad
            unidad = Unidad.query.filter_by(nombre=nombre_unidad).first()
            if not unidad:
                print(f"Unidad NO encontrada: {nombre_unidad}")
                errores += 1
                continue

            # Busca la pregunta
            pregunta = Pregunta.query.filter_by(texto=texto_pregunta).first()
            if not pregunta:
                print(f"Pregunta NO encontrada: {texto_pregunta}")
                errores += 1
                continue

            # Busca el usuario
            usuario = Usuario.query.filter_by(usuario=usuario_nombre).first()
            if not usuario:
                print(f"Usuario NO encontrado: {usuario_nombre}")
                errores += 1
                continue

            # Busca o crea el periodo
            periodo = Periodo.query.filter_by(mes=mes, anio=anio).first()
            if not periodo:
                periodo = Periodo(mes=mes, anio=anio, abierto=False)
                db.session.add(periodo)
                db.session.commit()

            # Verifica si ya existe la respuesta
            respuesta_existente = Respuesta.query.filter_by(
                usuario_id=usuario.id,
                pregunta_id=pregunta.id,
                unidad_id=unidad.id,
                periodo_id=periodo.id
            ).first()
            if respuesta_existente:
                print(f"Ya existe respuesta para {usuario_nombre}, {texto_pregunta}, {mes}/{anio}")
                continue

            respuesta = Respuesta(
                usuario_id=usuario.id,
                pregunta_id=pregunta.id,
                unidad_id=unidad.id,
                periodo_id=periodo.id,
                valor=valor,
                fecha_registro=datetime.utcnow()
            )
            db.session.add(respuesta)
            cargadas += 1
        except Exception as e:
            print(f"Error en fila {idx+2}: {e}")
            errores += 1
            continue

    db.session.commit()
    print(f"Respuestas cargadas correctamente: {cargadas}")
    print(f"Respuestas con error: {errores}")

if __name__ == "__main__":
    from app import app
    with app.app_context():
        cargar_respuestas()
