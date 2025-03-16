from OpenGL.GL import *
import os

def compile_shader(source, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    # Sprawdzenie, czy kompilacja się powiodła
    success = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not success:
        # Pobranie i wyświetlenie logu błędu
        info_log = glGetShaderInfoLog(shader).decode('utf-8')
        print(f"ERROR::SHADER::{shader_type}::COMPILATION_FAILED\n{info_log}")
        glDeleteShader(shader)
        raise Exception(f"Shader compilation failed ({shader_type}): {info_log}")

    return shader

def load_and_compile_shader(filename, shader_type):
    # Pobranie ścieżki katalogu skryptu
    script_dir = os.path.dirname(os.path.abspath(__file__))
    shader_path = os.path.join(script_dir, filename)
    
    if not os.path.isfile(shader_path):
        raise FileNotFoundError(f"Shader file '{filename}' not found in '{script_dir}'")
    
    # Wczytanie kodu shadera z pliku
    with open(shader_path, 'r', encoding='utf-8') as file:
        shader_source = file.read()
    
    # Kompilacja shadera
    return compile_shader(shader_source, shader_type)

	