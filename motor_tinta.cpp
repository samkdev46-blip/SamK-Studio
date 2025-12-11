#include <pybind11/pybind11.h>
#include <pybind11/stl.h> 
#include <cmath>
#include <vector>
#include <cstdlib>   
#include <algorithm> 

namespace py = pybind11;

// Função C++ otimizada para calcular o traço
std::vector<std::vector<float>> calcular_trajeto(
    float x1, float y1, float x2, float y2, 
    float dist_sobra,                       
    float espacamento,                      
    float tamanho_base,                     
    float pressao,                          
    bool dinamica_tam,                      
    bool dinamica_alpha,                    
    float jitter_angle,                     
    float jitter_size                       
) {
    std::vector<std::vector<float>> resultados;
    
    float dx = x2 - x1;
    float dy = y2 - y1;
    float distancia_total = std::sqrt(dx*dx + dy*dy);
    
    if (distancia_total == 0) return resultados;

    float vx = dx / distancia_total;
    float vy = dy / distancia_total;

    float percorrido = dist_sobra;
    
    while (percorrido <= distancia_total) {
        float px = x1 + (vx * percorrido);
        float py = y1 + (vy * percorrido);
        
        float tam_final = tamanho_base;
        if (dinamica_tam) tam_final = std::max(1.0f, tamanho_base * pressao);
        
        if (jitter_size > 0) {
            float var = ((float)rand() / RAND_MAX) * (jitter_size * 2) - jitter_size;
            tam_final *= (1.0f + var);
        }

        float alpha_final = 1.0f;
        if (dinamica_alpha) alpha_final = pressao;

        float angulo_final = 0;
        if (jitter_angle > 0) {
            angulo_final = ((float)rand() / RAND_MAX) * jitter_angle;
        }

        resultados.push_back({px, py, tam_final, alpha_final, angulo_final});
        percorrido += std::max(1.0f, tam_final * espacamento);
    }

    float sobra = percorrido - distancia_total;
    resultados.push_back({-999.0f, sobra, 0.0f, 0.0f, 0.0f});

    return resultados;
}

PYBIND11_MODULE(motor_cpp, m) {
    m.doc() = "Motor C++ Otimizado do SamK";
    m.def("calcular_trajeto", &calcular_trajeto, "Calcula pontos interpolados");
}