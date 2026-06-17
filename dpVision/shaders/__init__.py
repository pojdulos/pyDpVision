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

def create_program(vertex_shader_name=None, geometry_shader_name=None, fragment_shader_name=None):
    shader_program = glCreateProgram()
    shaders = []

    try:
        if vertex_shader_name:
            vertex_shader = load_and_compile_shader(vertex_shader_name, GL_VERTEX_SHADER)
            shaders.append(vertex_shader)

        if geometry_shader_name:
            geometry_shader = load_and_compile_shader(geometry_shader_name, GL_GEOMETRY_SHADER)
            shaders.append(geometry_shader)

        if fragment_shader_name:
            fragment_shader = load_and_compile_shader(fragment_shader_name, GL_FRAGMENT_SHADER)
            shaders.append(fragment_shader)

        for shader in shaders:
            glAttachShader(shader_program, shader)

        glLinkProgram(shader_program)

        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            info_log = glGetProgramInfoLog(shader_program)
            raise Exception(f"Error linking shaders:\n{info_log.decode()}")

    except Exception as e:
        # Jeśli cokolwiek pójdzie nie tak - czyścimy program
        glDeleteProgram(shader_program)
        raise e

    finally:
        for shader in shaders:
            glDeleteShader(shader)

    return shader_program
