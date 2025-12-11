from setuptools import setup, Extension
import pybind11

# Pega o caminho onde o pybind11 está instalado
include_dirs = [pybind11.get_include()]

# Define o módulo
ext_modules = [
    Extension(
        "motor_cpp",              # Nome que vamos usar no Python
        ["motor_tinta.cpp"],      # Nome do arquivo C++
        include_dirs=include_dirs,
        language="c++"
    ),
]

setup(
    name="motor_cpp",
    version="1.0",
    ext_modules=ext_modules,
)