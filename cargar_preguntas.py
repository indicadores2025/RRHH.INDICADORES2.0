import pandas as pd
from models import db, Pregunta, Unidad, Usuario
from app import app

def obtener_unidad_id(nombre_unidad):
    unidad = Unidad.query.filter_by(nombre=nombre_unidad.strip()).first()
    if not unidad:
        print(f"[ADVERTENCIA] No existe la unidad: {nombre_unidad}")
        return None
    return unidad.id

def obtener_usuario_id(nombre_usuario):
    usuario = Usuario.query.filter_by(usuario=nombre_usuario.strip()).first()
    if not usuario:
        print(f"[ADVERTENCIA] No existe el usuario: {nombre_usuario}")
        return None
    return usuario.id

def obtener_pregunta_id_por_texto(texto_pregunta):
    pregunta = Pregunta.query.filter_by(texto=texto_pregunta.strip()).first()
    if pregunta:
        return pregunta.id
    return None

def cargar_preguntas_desde_excel(nombre_archivo="preguntas.xlsx"):
    df = pd.read_excel(nombre_archivo)
    total = 0

    with app.app_context():
        for idx, fila in df.iterrows():
            texto = str(fila['TEXTO DE LA PREGUNTA']).strip()
            unidad_nombre = str(fila['UNIDAD']).strip()
            tipo = str(fila['TIPO']).strip()
            nivel_texto = str(fila['NIVEL']).strip()
            padre_texto = str(fila['PADRE_ID']).strip() if not pd.isnull(fila['PADRE_ID']) else None
            usuario_nombre = str(fila['USUARIO']).strip() if not pd.isnull(fila['USUARIO']) else None

            # Convertir nivel
            if nivel_texto.startswith("1"):
                nivel = 1
            elif nivel_texto.startswith("2"):
                nivel = 2
            elif nivel_texto.startswith("3"):
                nivel = 3
            else:
                nivel = 1  # Por defecto

            unidad_id = obtener_unidad_id(unidad_nombre) if unidad_nombre else None
            usuario_id = obtener_usuario_id(usuario_nombre) if usuario_nombre else None

            # Buscar el padre por el texto
            padre_id = None
            if padre_texto and padre_texto.lower() != "nan":
                padre_id = obtener_pregunta_id_por_texto(padre_texto)
                if padre_id is None:
                    print(f"[ADVERTENCIA] No se encontró PADRE_ID para: '{padre_texto}' (fila {idx+2})")

            # Verifica si ya existe la pregunta (por texto)
            existente = Pregunta.query.filter_by(texto=texto).first()
            if existente:
                print(f"[INFO] Pregunta ya existe: '{texto}'. Se omite.")
                continue

            nueva_pregunta = Pregunta(
                texto=texto,
                unidad_id=unidad_id,
                tipo=tipo,
                nivel=nivel,
                padre_id=padre_id,
                usuario_id=usuario_id
            )
            db.session.add(nueva_pregunta)
            total += 1

        db.session.commit()
    print(f"Preguntas cargadas: {total}")

if __name__ == "__main__":
    cargar_preguntas_desde_excel("preguntas.xlsx")
