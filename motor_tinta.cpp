#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <mypaint-brush.h>
#include <mypaint-surface.h>
#include <mypaint-brush-settings.h> // Importante: Traduz nomes de settings
#include <vector>
#include <cmath>
#include <string>
#include <algorithm>

namespace py = pybind11;

// Estrutura do pingo de tinta
struct Dab {
    float x, y, radius, color_r, color_g, color_b, opaque;
};

// Superfície gravadora (finge que desenha, mas só anota)
class SurfaceRecorder : public MyPaintSurface {
public:
    std::vector<Dab> dabs;

    SurfaceRecorder() {
        this->draw_dab = draw_dab_callback;
        this->get_color = get_color_callback;
        this->begin_atomic = nullptr;
        this->end_atomic = nullptr;
        this->destroy = nullptr;
        this->save_png = nullptr;
    }

    static int draw_dab_callback(MyPaintSurface *self, float x, float y,
                                 float radius,
                                 float color_r, float color_g, float color_b,
                                 float opaque, float hardness,
                                 float alpha_eraser, float aspect_ratio,
                                 float angle, float lock_alpha,
                                 float colorize) {
        SurfaceRecorder* recorder = (SurfaceRecorder*)self;
        Dab d = {x, y, radius, color_r, color_g, color_b, opaque};
        recorder->dabs.push_back(d);
        return 1;
    }

    static void get_color_callback(MyPaintSurface *self, float x, float y,
                                   float radius,
                                   float *color_r, float *color_g, float *color_b,
                                   float *color_a) {
        // Retorna branco por padrão (pode ser melhorado depois para ler da tela)
        *color_r = 1.0; *color_g = 1.0; *color_b = 1.0; *color_a = 1.0;
    }
};

class MotorMyPaint {
private:
    MyPaintBrush *brush;
    SurfaceRecorder surface;

public:
    MotorMyPaint() {
        brush = mypaint_brush_new();
        mypaint_brush_from_defaults(brush);
    }

    ~MotorMyPaint() {
        mypaint_brush_unref(brush);
    }

    // --- NOVA FUNÇÃO CRÍTICA ---
    // Permite que o Python envie configurações pelo NOME (ex: "radius_logarithmic")
    // Isso é essencial para ler arquivos .myb
    void set_parametro_por_nome(std::string nome, float valor) {
        MyPaintBrushSetting id = mypaint_brush_setting_from_cname(nome.c_str());
        if (id < MYPAINT_BRUSH_SETTINGS_COUNT) {
            mypaint_brush_set_base_value(brush, id, valor);
        }
    }

    // Função manual antiga (ainda útil para sliders manuais)
    void set_config(int id_setting, float valor) {
        if (id_setting == 0) 
            mypaint_brush_set_base_value(brush, MYPAINT_BRUSH_SETTING_RADIUS_LOGARITHMIC, std::log(valor));
        else if (id_setting == 1)
            mypaint_brush_set_base_value(brush, MYPAINT_BRUSH_SETTING_OPAQUE, valor);
    }

    std::vector<std::vector<float>> atualizar_traco(float x, float y, float pressure, float dt) {
        surface.dabs.clear();
        
        // O MyPaint calcula a física aqui
        mypaint_brush_stroke_to(brush, (MyPaintSurface*)&surface, x, y, pressure, 0, 0, dt);
        
        // Devolve os pontos calculados para o Python
        std::vector<std::vector<float>> retorno;
        for (const auto& d : surface.dabs) {
            retorno.push_back({d.x, d.y, d.radius, d.opaque});
        }
        return retorno;
    }

    void reset() {
        mypaint_brush_reset(brush);
    }
};

PYBIND11_MODULE(motor_cpp, m) {
    m.doc() = "Motor C++ Avançado SamK Studio";
    py::class_<MotorMyPaint>(m, "MotorMyPaint")
        .def(py::init<>())
        .def("set_config", &MotorMyPaint::set_config)
        .def("set_parametro_por_nome", &MotorMyPaint::set_parametro_por_nome) // Exporta a nova função
        .def("atualizar_traco", &MotorMyPaint::atualizar_traco)
        .def("reset", &MotorMyPaint::reset);
}