# setup.py - O Construtor do SamK Studio
from setuptools import setup, Extension
import pybind11

# Caminhos que você descobriu com o pkg-config
# Se um dia mudar de PC, rode 'pkg-config --cflags --libs libmypaint' para conferir
INCLUDE_DIRS = [
    pybind11.get_include(),
    "/usr/include/libmypaint",
    "/usr/include/json-c",
    "/usr/include/glib-2.0",
    "/usr/lib/x86_64-linux-gnu/glib-2.0/include"
]

# Bibliotecas para ligar (Linker)
LIBRARIES = ["mypaint", "json-c", "glib-2.0"]

ext_modules = [
    Extension(
        "motor_cpp",
        ["motor_tinta.cpp"],
        include_dirs=INCLUDE_DIRS,
        libraries=LIBRARIES,
        language="c++",
        extra_compile_args=["-std=c++11", "-O3", "-fopenmp"], # O3 = Otimização Máxima
        extra_link_args=["-fopenmp"]
    ),
]

setup(
    name="motor_cpp",
    version="1.0",
    ext_modules=ext_modules,
)