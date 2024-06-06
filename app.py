import streamlit as st
import pandas as pd
import os
from datetime import datetime
import subprocess
from functools import partial
import re 
import json
from firebase_config import db 

def load_data(student_file):
    base_name = student_file.split('_times')[0]
    times_path = f"Attendance/{student_file}"
    details_path = f"Attendance/{base_name}_details.csv"
    times_df = pd.read_csv(times_path)
    details_df = pd.read_csv(details_path)
    return times_df, details_df


def run_script(script_name, course_name=None, session_date=None):
    try:
        command = ['python', script_name]
        if course_name and session_date:
            # Añadimos los argumentos necesarios para el script de test.py
            command.extend([course_name, session_date.strftime('%Y-%m-%d')])
        # Ejecutar el comando completo
        subprocess.run(command, check=True)
        st.success(f"El proceso para {script_name} ha comenzado con éxito.")
    except subprocess.CalledProcessError as e:
        st.error(f"Falló la ejecución de {script_name}: {e}")
    except Exception as e:
        st.error(f"Error desconocido al ejecutar {script_name}: {str(e)}")

def setup_course_page():
    st.title("Configuración del Curso")
    with st.form("course_form"):
        class_name = st.text_input("Nombre del Curso")
        start_date = st.date_input("Fecha de Inicio")
        end_date = st.date_input("Fecha Fin")
        submitted = st.form_submit_button("Guardar Configuración del Curso")
    if submitted:
        course_info = {
            'class_name': class_name,
            'start_date': str(start_date),
            'end_date': str(end_date)
        }
        # Guardar en Firestore
        db.collection('courses').add(course_info)
        st.success(f"Configuración guardada para el curso {class_name} desde {start_date} hasta {end_date}")
        st.button("Agregar caras al curso", on_click=lambda: run_script('add_faces.py'))

def list_files(course_name, date):
    session_date_str = date.strftime('%Y-%m-%d')
    folder_path = "Attendance"
    if not os.path.exists(folder_path):
        st.sidebar.write(f"Directorio no encontrado: {folder_path}")
        return [], []
    all_files = os.listdir(folder_path)
    detail_files = [f for f in all_files if f.startswith(f"{course_name}_{session_date_str}") and "_details.csv" in f]
    time_files = [f for f in all_files if f.startswith(f"{course_name}_{session_date_str}") and "_times.csv" in f]
    return detail_files, time_files

def view_file(file_path):
    df = pd.read_csv(f"Attendance/{file_path}")
    st.write(df)
    
def session_page():
    st.title("Registro de Sesión")
    courses_ref = db.collection('courses')
    courses = courses_ref.stream()
    courses_data = {course.id: course.to_dict() for course in courses}

    if courses_data:
        course_list = [course['class_name'] for course in courses_data.values()]
        selected_course = st.selectbox('Selecciona un curso', course_list)
        with st.form("session_form"):
            session_date = st.date_input("Fecha de la Sesión")
            session_start = st.time_input("Hora de Inicio")
            session_end = st.time_input("Hora de Fin")
            session_submit = st.form_submit_button("Registrar Sesión")
        if session_submit:
            session_info = {
                'date': str(session_date),
                'start': str(session_start),
                'end': str(session_end)
            }
            # Actualizar curso en Firestore
            for course_id, course in courses_data.items():
                if course['class_name'] == selected_course:
                    if 'sessions' not in course:
                        course['sessions'] = []
                    course['sessions'].append(session_info)
                    courses_ref.document(course_id).set(course)
                    break

            st.success(f"Sesión registrada para {selected_course} el {session_date} de {session_start} a {session_end}")

            button_callback = partial(run_script, 'test.py', selected_course, session_date)
            st.button("Iniciar Asistencia", on_click=button_callback)
    else:
        st.error("No se ha configurado ningún curso aún.")
def main():
    st.sidebar.title("Navegación")
    page = st.sidebar.radio("Ir a", ["Configuración del Curso", "Registro de Sesión", "Visualizar Archivos"])

    if page == "Configuración del Curso":
        setup_course_page()
    elif page == "Registro de Sesión":
        session_page()
    elif page == "Visualizar Archivos":
        # Cargar los nombres de los cursos desde Firestore
        courses_ref = db.collection('courses')
        courses = courses_ref.stream()
        courses_data = {course.id: course.to_dict() for course in courses}

        if courses_data:
            course_list = [course['class_name'] for course in courses_data.values()]
            selected_course = st.selectbox('Selecciona un Curso para visualizar archivos', course_list)
            selected_date = st.date_input("Selecciona la fecha del curso")
            detail_files, time_files = list_files(selected_course, selected_date)

            if detail_files or time_files:
                file_type = st.radio("Tipo de Archivo", ("Reporte de Entradas y Salidas", "Reporte Actitudinal Diario"))
                selected_file_list = detail_files if file_type == "Reporte Actitudinal Diario" else time_files
                selected_file = st.selectbox('Selecciona un archivo', selected_file_list)
                if st.button('Cargar Archivo'):
                    view_file(selected_file)
            else:
                st.error("No se encontraron archivos para este curso y fecha.")
        else:
            st.error("No hay cursos configurados.")
            
if __name__ == "__main__":
    main()
