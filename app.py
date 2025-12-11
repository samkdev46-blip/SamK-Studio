import sys
import random
import math
import zipfile
import io
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QColorDialog, 
                             QToolBar, QFileDialog, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QMessageBox, QDockWidget, QListWidget, 
                             QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QSlider, QInputDialog) 
from PyQt6.QtGui import (QPixmap, QPainter, QPen, QColor, QAction, QTabletEvent, 
                         QPointingDevice, QBrush, QIcon, QImage, QPainterPath,
                         QLinearGradient, QRadialGradient, QPolygonF, 
                         QShortcut, QKeySequence, QTransform) 
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QPointF
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as db 

# --- TENTA LIGAR O MOTOR C++ ---
try:
    import motor_cpp
    print("============================================")
    print("   🚀 SUCESSO: MOTOR C++ CARREGADO!         ")
    print("============================================")
    MOTOR_C_ATIVO = True
except ImportError:
    print("============================================")
    print("   🐢 AVISO: MOTOR C++ NÃO ENCONTRADO       ")
    print("============================================")
    MOTOR_C_ATIVO = False

# --- 1. GERENCIADOR DE ESTILOS ---
class GerenciadorPinceis:
    def __init__(self):
        self.estilos = {
            "Caneta Tinteiro": { 
                "dinamica_tamanho": True, "dinamica_alpha": False, "texturizado": False, "textura": None,
                "jitter_angle": 0, "jitter_size": 0, "mistura_padrao": 0
            },
            "Lápis HB": { 
                "dinamica_tamanho": False, "dinamica_alpha": True, "texturizado": False, "textura": None,
                "jitter_angle": 0, "jitter_size": 0, "mistura_padrao": 0
            },
            "Giz / Carvão (C++)": { 
                "dinamica_tamanho": False, "dinamica_alpha": True, "texturizado": True, "textura": self.gerar_textura_padrao(),
                "jitter_angle": 360, "jitter_size": 0.2, "mistura_padrao": 0
            },
            "Pincel a Óleo (Smudge)": { 
                "dinamica_tamanho": True, "dinamica_alpha": False, "texturizado": True, "textura": self.gerar_textura_padrao(),
                "jitter_angle": 10, "jitter_size": 0.05, "mistura_padrao": 50 
            },
            "Borracha Dura": { 
                "dinamica_tamanho": True, "dinamica_alpha": True, "texturizado": False, "textura": None,
                "jitter_angle": 0, "jitter_size": 0, "mistura_padrao": 0
            },
            "Borracha Limpa-Tipos (C++)": { 
                "dinamica_tamanho": False, "dinamica_alpha": True, "texturizado": True, "textura": self.gerar_textura_forte(), # Textura mais forte pra apagar
                "jitter_angle": 360, "jitter_size": 0.2, "mistura_padrao": 0
            }
        }
        self.pincel_atual = "Caneta Tinteiro"

    def gerar_textura_padrao(self):
        img = QPixmap(64, 64)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 20)) # Opacidade baixa (pintura suave)
        p.drawEllipse(2, 2, 60, 60)
        for _ in range(400):
            x = random.randint(0, 64); y = random.randint(0, 64)
            dx = x - 32; dy = y - 32
            if dx*dx + dy*dy < 30*30:
                p.setPen(QColor(0, 0, 0, random.randint(50, 150)))
                p.drawPoint(x, y)
        p.end()
        return img

    def gerar_textura_forte(self): # Nova textura para borracha
        img = QPixmap(64, 64)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 150)) # Opacidade ALTA (para apagar bem)
        p.drawEllipse(2, 2, 60, 60)
        for _ in range(600):
            x = random.randint(0, 64); y = random.randint(0, 64)
            dx = x - 32; dy = y - 32
            if dx*dx + dy*dy < 30*30:
                p.setPen(QColor(0, 0, 0, 255)) # Pontos pretos sólidos
                p.drawPoint(x, y)
        p.end()
        return img
    
    def gerar_icone_generico(self, tipo):
        img = QPixmap(64, 64)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.GlobalColor.white) 
        p.setBrush(Qt.GlobalColor.white)
        
        if "Borracha" in tipo:
            if "Limpa-Tipos" in tipo:
                p.setBrush(QColor(200, 200, 200, 150))
                p.setPen(Qt.PenStyle.DotLine)
                p.drawEllipse(10, 10, 44, 44)
            else:
                p.setBrush(Qt.BrushStyle.NoBrush) 
                p.setPen(QPen(Qt.GlobalColor.white, 3, Qt.PenStyle.DashLine))
                p.drawEllipse(10, 10, 44, 44)
        elif "Óleo" in tipo:
            p.setBrush(QColor(200, 200, 255, 100))
            p.drawEllipse(10, 10, 44, 44)
            p.setPen(Qt.GlobalColor.white)
            p.drawText(QRect(0,0,64,64), Qt.AlignmentFlag.AlignCenter, "MIX")
        elif tipo == "Caneta Tinteiro":
            p.drawEllipse(16, 16, 32, 32)
        elif tipo == "Lápis HB":
            p.setPen(QPen(Qt.GlobalColor.white, 2))
            p.drawLine(10, 54, 54, 10)
            
        p.end()
        return img

    def criar_novo_pincel_customizado(self, nome, pixmap_textura):
        base_nome = nome; contador = 1
        while nome in self.estilos: nome = f"{base_nome} ({contador})"; contador += 1
        self.estilos[nome] = {
            "dinamica_tamanho": False, "dinamica_alpha": True, "texturizado": True, "textura": pixmap_textura,
            "jitter_angle": 360, "jitter_size": 0.1, "mistura_padrao": 0
        }
        return nome

    def pegar_config(self, nome=None):
        if not nome: nome = self.pincel_atual
        return self.estilos.get(nome, self.estilos["Caneta Tinteiro"])
    
    def pegar_textura_atual(self):
        config = self.pegar_config()
        if config["textura"]: return config["textura"]
        return self.gerar_textura_padrao() 

# --- 2. CANVAS VIEW ---
class CanvasView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse) 
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setMouseTracking(True)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            angulo = event.angleDelta().y() / 8 
            self.rotate(angulo)
        else:
            zoom_in = event.angleDelta().y() > 0
            fator = 1.2 if zoom_in else 1.0 / 1.2
            self.scale(fator, fator)
        event.accept()

    def tabletEvent(self, event):
        if self.parent(): self.parent().tabletEvent(event)
        super().tabletEvent(event)

    def mousePressEvent(self, event):
        if self.parent(): self.parent().tratar_mouse_press(event, self.mapToScene(event.pos()))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent(): self.parent().tratar_mouse_move(event, self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parent(): self.parent().tratar_mouse_release(event)
        super().mouseReleaseEvent(event)

# --- 3. SELETOR DE CORES 8-BIT ---
class SeletorCoresAvancado8Bit(QWidget):
    corChanged = db.pyqtSignal(QColor)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 260)
        self.hue = 0.0; self.sat = 0.0; self.val = 0.0
        self.cor_atual = QColor(Qt.GlobalColor.black)
        self.pix_hue = None; self.pix_sv = None
        self.rect_sv = QRect(10, 10, 200, 200)
        self.rect_hue = QRect(10, 220, 200, 30)
        self.gerar_barra_hue_8bit()
        self.atualizar_quadrado_sv_8bit()

    def gerar_barra_hue_8bit(self):
        img = QImage(32, 5, QImage.Format.Format_RGB32)
        p = QPainter(img)
        grad = QLinearGradient(0, 0, 32, 0)
        for i, c in enumerate([Qt.GlobalColor.red, Qt.GlobalColor.yellow, Qt.GlobalColor.green, Qt.GlobalColor.cyan, Qt.GlobalColor.blue, Qt.GlobalColor.magenta, Qt.GlobalColor.red]):
            grad.setColorAt(i/6, c)
        p.fillRect(0, 0, 32, 5, grad); p.end()
        self.pix_hue = QPixmap.fromImage(img).scaled(self.rect_hue.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

    def atualizar_quadrado_sv_8bit(self):
        img = QImage(32, 32, QImage.Format.Format_RGB32)
        cor_base = QColor.fromHsvF(self.hue, 1.0, 1.0)
        p = QPainter(img)
        grad_h = QLinearGradient(0, 0, 32, 0)
        grad_h.setColorAt(0, Qt.GlobalColor.white); grad_h.setColorAt(1, cor_base)
        p.fillRect(0, 0, 32, 32, grad_h)
        grad_v = QLinearGradient(0, 0, 0, 32)
        grad_v.setColorAt(0, QColor(0, 0, 0, 0)); grad_v.setColorAt(1, QColor(0, 0, 0, 255))
        p.fillRect(0, 0, 32, 32, grad_v); p.end()
        self.pix_sv = QPixmap.fromImage(img).scaled(self.rect_sv.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

    def paintEvent(self, event):
        p = QPainter(self); p.fillRect(self.rect(), QColor("#303030"))
        p.drawPixmap(self.rect_sv.topLeft(), self.pix_sv); p.drawPixmap(self.rect_hue.topLeft(), self.pix_hue)
        xh = int(self.rect_hue.x() + self.hue * self.rect_hue.width())
        p.setPen(Qt.GlobalColor.black); p.drawLine(xh, 218, xh, 252); p.setPen(Qt.GlobalColor.white); p.drawLine(xh, 218, xh, 252)
        xs, ys = int(self.rect_sv.x() + self.sat * 200), int(self.rect_sv.y() + (1-self.val) * 200)
        p.setPen(Qt.GlobalColor.black); p.drawEllipse(QPoint(xs, ys), 6, 6); p.setPen(Qt.GlobalColor.white); p.drawEllipse(QPoint(xs, ys), 6, 6)
        p.fillRect(180, 235, 30, 15, self.cor_atual); p.setPen(Qt.GlobalColor.white); p.drawRect(180, 235, 30, 15); p.end()

    def mousePressEvent(self, e): self.proc_mouse(e.pos())
    def mouseMoveEvent(self, e): self.proc_mouse(e.pos())
    def proc_mouse(self, pos):
        if self.rect_hue.contains(pos):
            self.hue = max(0, min(1, (pos.x() - 10)/200))
            self.atualizar_quadrado_sv_8bit()
        elif self.rect_sv.contains(pos):
            self.sat = max(0, min(1, (pos.x() - 10)/200))
            self.val = 1 - max(0, min(1, (pos.y() - 10)/200))
        self.cor_atual = QColor.fromHsvF(self.hue, self.sat, self.val)
        self.corChanged.emit(self.cor_atual); self.update()

# --- 4. ESTRUTURA DE DADOS ---
class DadosCamada:
    def __init__(self, nome, w, h, z):
        self.nome = nome; self.visivel = True; self.trancada = False
        self.pixmap = QPixmap(w, h); self.pixmap.fill(Qt.GlobalColor.transparent)
        self.item = QGraphicsPixmapItem(self.pixmap); self.item.setZValue(z)

class WidgetItemCamada(QWidget):
    def __init__(self, texto, trancada, callback):
        super().__init__()
        l = QHBoxLayout(self); l.setContentsMargins(2,2,2,2)
        self.btn = QPushButton("👁️"); self.btn.setCheckable(True); self.btn.setChecked(True)
        self.btn.clicked.connect(callback); self.btn.setFixedSize(30,30)
        self.btn.setStyleSheet("border:none; font-size:16px;")
        l.addWidget(self.btn); lbl = QLabel(texto); lbl.setStyleSheet("color:#DDD; font-weight:bold")
        l.addWidget(lbl)
        if trancada: l.addWidget(QLabel("🔒"))
        l.addStretch()

# --- 5. JANELA PRINCIPAL ---
class MeuDesenhoPro(QMainWindow):
    def __init__(self):
        super().__init__()
        
        if MOTOR_C_ATIVO:
            self.setWindowTitle("SamK Art Studio - 🚀 MOTOR V8 (C++) ATIVADO!")
        else:
            self.setWindowTitle("SamK Art Studio - 🐢 MODO PYTHON (LENTO)")
            
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("QMainWindow { background-color: #404040; } QMenuBar { background-color: #303030; color: white; } QMenuBar::item:selected { background-color: #505050; } QMenu { background-color: #303030; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #007ACC; } QToolBar { border: none; } QDockWidget { color: white; font-weight: bold; background-color: #353535; } QListWidget { background-color: #353535; } QLabel { color: white; }")
        
        self.motor = GerenciadorPinceis()
        self.tam_base = 30; self.opac_global = 1.0; self.cor_pincel = QColor("black")
        self.fator_mistura = 0.0
        self.ferramenta = "pincel"; self.modo_zen = False
        self.ultimo_ponto = None; self.resto_dist = 0.0
        self.camadas = []; self.historico = []; self.idx_ativa = 0
        self.cache_leitura = None 
        
        self.modos_blend = {
            "Normal": QPainter.CompositionMode.CompositionMode_SourceOver,
            "Multiplicar": QPainter.CompositionMode.CompositionMode_Multiply,
            "Tela": QPainter.CompositionMode.CompositionMode_Screen,
            "Sobrepor": QPainter.CompositionMode.CompositionMode_Overlay
        }
        self.blend_atual = self.modos_blend["Normal"]

        self.scene = QGraphicsScene(0, 0, 2000, 2000)
        self.scene.setBackgroundBrush(QColor("#202020"))
        
        self.view = CanvasView(self.scene, self)
        self.setCentralWidget(self.view)

        self.setup_docks(); self.setup_toolbar(); self.setup_menus()
        
        bg = DadosCamada("Papel", 2000, 2000, 0); bg.pixmap.fill(QColor("#F5F5F0"))
        bg.item.setPixmap(bg.pixmap); self.scene.addItem(bg.item); self.camadas.append(bg)
        self.nova_camada(); self.idx_ativa = 1; self.atualizar_lista_camadas()

        self.sh_tab = QShortcut(QKeySequence("Tab"), self)
        self.sh_tab.activated.connect(self.toggle_zen_mode)

    # --- PROCESSAMENTO DO DESENHO (CORRIGIDO) ---
    def processar_desenho(self, pos, pressao, eraser):
        if self.idx_ativa >= len(self.camadas): return
        cam = self.camadas[self.idx_ativa]
        if not cam.visivel or cam.trancada: return

        conf = self.motor.pegar_config()
        tam = self.tam_base
        
        # --- LÓGICA DE BORRACHA CORRIGIDA ---
        # Se a ferramenta é borracha ou a caneta está invertida
        eh_borracha = (self.ferramenta == "borracha") or eraser
        
        if eh_borracha:
            if conf["texturizado"]:
                # Borracha com textura (suave)
                modo = QPainter.CompositionMode.CompositionMode_DestinationOut
            else:
                # Borracha dura (padrão)
                modo = QPainter.CompositionMode.CompositionMode_Clear
        else:
            # Pincel normal
            modo = self.blend_atual
        
        p1, p2 = self.ultimo_ponto, pos
        dist = math.hypot(p2.x()-p1.x(), p2.y()-p1.y())
        if dist == 0: return

        p = QPainter(cam.pixmap)
        p.setCompositionMode(modo)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # MISTURA (Smudge) - Não mistura se estiver apagando
        cor_uso = self.cor_pincel
        if self.fator_mistura > 0 and self.cache_leitura and not eh_borracha:
            x_read = max(0, min(self.cache_leitura.width()-1, int(p1.x())))
            y_read = max(0, min(self.cache_leitura.height()-1, int(p1.y())))
            cor_fundo = self.cache_leitura.pixelColor(x_read, y_read)
            r = int(self.cor_pincel.red() * (1 - self.fator_mistura) + cor_fundo.red() * self.fator_mistura)
            g = int(self.cor_pincel.green() * (1 - self.fator_mistura) + cor_fundo.green() * self.fator_mistura)
            b = int(self.cor_pincel.blue() * (1 - self.fator_mistura) + cor_fundo.blue() * self.fator_mistura)
            cor_uso = QColor(r, g, b, self.cor_pincel.alpha())

        # MODO PYTHON (SIMPLES)
        if not conf["texturizado"] or (eh_borracha and not conf["texturizado"]):
            tam_final = max(1, tam * pressao) if conf["dinamica_tamanho"] else tam
            alpha_final = pressao if conf["dinamica_alpha"] else 1.0
            p.setOpacity(alpha_final * self.opac_global)
            pen = QPen(Qt.GlobalColor.transparent if eh_borracha else cor_uso, tam_final, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen); p.drawLine(p1, p2)
        
        # MODO C++ (ACELERADO - Pincel ou Borracha Texturizada)
        elif MOTOR_C_ATIVO and conf["texturizado"]:
            pontos = motor_cpp.calcular_trajeto(
                p1.x(), p1.y(), p2.x(), p2.y(),
                self.resto_dist, max(1, tam * 0.15), tam, pressao,
                conf["dinamica_tamanho"], conf["dinamica_alpha"],
                conf.get("jitter_angle", 0), conf.get("jitter_size", 0)
            )
            
            if pontos:
                ultimo = pontos.pop()
                self.resto_dist = ultimo[1]

            tex = self.motor.pegar_textura_atual()
            for pt in pontos:
                p.setOpacity(pt[3] * self.opac_global)
                tam_i = int(pt[2]) if int(pt[2]) > 0 else 1
                tex_scaled = tex.scaled(tam_i, tam_i, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                if pt[4] > 0:
                    p.save(); p.translate(pt[0], pt[1]); p.rotate(pt[4])
                    p.drawPixmap(int(-tam_i/2), int(-tam_i/2), tex_scaled); p.restore()
                else:
                    p.drawPixmap(int(pt[0] - tam_i/2), int(pt[1] - tam_i/2), tex_scaled)
        
        else: pass

        p.end(); cam.item.setPixmap(cam.pixmap); self.ultimo_ponto = pos

    def tabletEvent(self, e: QTabletEvent):
        pos = self.view.mapToScene(self.view.mapFromGlobal(e.globalPosition().toPoint()))
        eraser = e.pointerType() == QPointingDevice.PointerType.Eraser
        if e.type() == db.QEvent.Type.TabletPress:
            self.tratar_inicio_traco(pos); self.salvar_undo()
        elif e.type() == db.QEvent.Type.TabletMove and self.ultimo_ponto:
            self.processar_desenho(pos, e.pressure(), eraser)
        elif e.type() == db.QEvent.Type.TabletRelease:
            self.tratar_fim_traco()

    def tratar_mouse_press(self, e, pos):
        if e.button() == Qt.MouseButton.LeftButton:
            self.tratar_inicio_traco(pos); self.salvar_undo()
    
    def tratar_mouse_move(self, e, pos):
        if self.ultimo_ponto and (e.buttons() & Qt.MouseButton.LeftButton):
            self.processar_desenho(pos, 1.0, False) 

    def tratar_mouse_release(self, e, pos=None): 
        if e.button() == Qt.MouseButton.LeftButton: self.tratar_fim_traco()

    def tratar_inicio_traco(self, pos):
        self.ultimo_ponto = pos
        self.resto_dist = 0
        if self.idx_ativa < len(self.camadas):
            self.cache_leitura = self.camadas[self.idx_ativa].pixmap.toImage()

    def tratar_fim_traco(self):
        self.ultimo_ponto = None
        self.cache_leitura = None 

    def setup_docks(self):
        self.dk_cor = QDockWidget("Cores", self); w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0)
        self.sel_cor = SeletorCoresAvancado8Bit(); self.sel_cor.corChanged.connect(lambda c: setattr(self, 'cor_pincel', c))
        l.addWidget(self.sel_cor); l.addStretch(); self.dk_cor.setWidget(w); self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dk_cor)
        
        self.dk_brush = QDockWidget("Pincéis", self); w2 = QWidget(); l2 = QVBoxLayout(w2); l2.setContentsMargins(0,0,0,0)
        self.lst_brush = QListWidget(); self.lst_brush.setViewMode(QListWidget.ViewMode.IconMode); self.lst_brush.setIconSize(QSize(40,40))
        self.lst_brush.itemClicked.connect(lambda i: self.mudar_pincel(i.text()))
        btn_imp = QPushButton("Importar"); btn_imp.clicked.connect(self.importar_brush)
        l2.addWidget(self.lst_brush); l2.addWidget(btn_imp); self.dk_brush.setWidget(w2); self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dk_brush)
        self.atualizar_lista_pinceis()

        self.dk_layer = QDockWidget("Camadas", self); w3 = QWidget(); l3 = QVBoxLayout(w3)
        b_add = QPushButton("+"); b_add.clicked.connect(self.nova_camada)
        b_del = QPushButton("-"); b_del.clicked.connect(self.del_camada)
        hl = QHBoxLayout(); hl.addWidget(b_add); hl.addWidget(b_del); l3.addLayout(hl)
        self.lst_layer = QListWidget(); self.lst_layer.itemClicked.connect(self.ativar_camada)
        l3.addWidget(self.lst_layer); self.dk_layer.setWidget(w3); self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dk_layer)
        self.tabifyDockWidget(self.dk_brush, self.dk_layer); self.dk_brush.raise_()

    def setup_toolbar(self):
        tb = self.addToolBar("Tools")
        tb.addWidget(QLabel("📏")); sl_tam = QSlider(Qt.Orientation.Horizontal); sl_tam.setRange(1, 300); sl_tam.setValue(30)
        sl_tam.valueChanged.connect(lambda v: setattr(self, 'tam_base', v)); tb.addWidget(sl_tam)
        tb.addWidget(QLabel("💧")); sl_op = QSlider(Qt.Orientation.Horizontal); sl_op.setRange(0, 100); sl_op.setValue(100)
        sl_op.valueChanged.connect(lambda v: setattr(self, 'opac_global', v/100)); tb.addWidget(sl_op)
        tb.addWidget(QLabel("🌀")); self.sl_mix = QSlider(Qt.Orientation.Horizontal); self.sl_mix.setRange(0, 100); self.sl_mix.setValue(0)
        self.sl_mix.valueChanged.connect(lambda v: setattr(self, 'fator_mistura', v/100)); tb.addWidget(self.sl_mix)
        cb_blend = QComboBox(); cb_blend.addItems(self.modos_blend.keys())
        cb_blend.currentTextChanged.connect(lambda t: setattr(self, 'blend_atual', self.modos_blend[t]))
        tb.addWidget(cb_blend)
        tb.addAction("💾", self.salvar); tb.addAction("📂", self.abrir); tb.addAction("🧼", lambda: setattr(self, 'ferramenta', 'borracha'))

    def setup_menus(self):
        m = self.menuBar().addMenu("Exibir")
        m.addAction(self.dk_cor.toggleViewAction()); m.addAction(self.dk_brush.toggleViewAction())
        m.addAction(self.dk_layer.toggleViewAction()); m.addAction("Tela Cheia (Tab)", self.toggle_zen_mode)

    def toggle_zen_mode(self):
        self.modo_zen = not self.modo_zen
        if self.modo_zen:
            self.showFullScreen(); self.menuBar().hide(); self.dk_cor.hide(); self.dk_brush.hide(); self.dk_layer.hide()
        else:
            self.showNormal(); self.menuBar().show(); self.dk_cor.show(); self.dk_brush.show(); self.dk_layer.show()

    def nova_camada(self):
        idx = len(self.camadas); c = DadosCamada(f"Camada {idx}", 2000, 2000, idx)
        self.scene.addItem(c.item); self.camadas.append(c); self.idx_ativa = idx; self.atualizar_lista_camadas()

    def del_camada(self):
        if self.idx_ativa > 0 and len(self.camadas) > 1:
            c = self.camadas.pop(self.idx_ativa); self.scene.removeItem(c.item)
            self.idx_ativa -= 1; self.atualizar_lista_camadas()

    def ativar_camada(self, item): self.idx_ativa = item.data(Qt.ItemDataRole.UserRole)
    
    def atualizar_lista_camadas(self):
        self.lst_layer.clear()
        for i in range(len(self.camadas)-1, -1, -1):
            c = self.camadas[i]; it = QListWidgetItem(self.lst_layer); it.setData(Qt.ItemDataRole.UserRole, i)
            w = WidgetItemCamada(c.nome, c.trancada, lambda chk, x=i: self.toggle_vis(x))
            if not c.visivel: w.btn.setChecked(False)
            it.setSizeHint(w.sizeHint()); self.lst_layer.setItemWidget(it, w)
            if i == self.idx_ativa: it.setSelected(True); self.lst_layer.setCurrentItem(it)

    def toggle_vis(self, idx): 
        self.camadas[idx].visivel = not self.camadas[idx].visivel
        self.camadas[idx].item.setVisible(self.camadas[idx].visivel)

    # --- CORREÇÃO: DETECTA SE O NOME TEM "BORRACHA" ---
    def mudar_pincel(self, nome): 
        self.motor.pincel_atual = nome
        if "Borracha" in nome:
            self.ferramenta = "borracha"
        else:
            self.ferramenta = "pincel"
            
        conf = self.motor.pegar_config()
        mix = conf.get("mistura_padrao", 0)
        self.fator_mistura = mix / 100.0
        self.sl_mix.setValue(mix)

    def atualizar_lista_pinceis(self):
        self.lst_brush.clear()
        for nome in self.motor.estilos:
            it = QListWidgetItem(nome); icon = QIcon(self.motor.estilos[nome]["textura"] or self.motor.gerar_icone_generico(nome))
            it.setIcon(icon); self.lst_brush.addItem(it)

    def importar_brush(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar", "", "Img/Krita (*.png *.jpg *.bundle)")
        if not path: return
        if path.endswith(".bundle"):
            with zipfile.ZipFile(path, 'r') as z:
                for f in z.namelist():
                    if f.endswith(('.png','.jpg')) and "preview" not in f:
                        pix = QPixmap(); pix.loadFromData(z.read(f))
                        if not pix.isNull(): self.motor.criar_novo_pincel_customizado(os.path.basename(f), pix)
        else:
            pix = QPixmap(path)
            if not pix.isNull(): self.motor.criar_novo_pincel_customizado("Custom", pix)
        self.atualizar_lista_pinceis()

    def salvar(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar", "", "PNG (*.png)")
        if path:
            img = QPixmap(2000, 2000); img.fill(Qt.GlobalColor.transparent); p = QPainter(img)
            for c in self.camadas: 
                if c.visivel: 
                    opt = QtWidgets.QStyleOptionGraphicsItem(); c.item.paint(p, opt, None)
            p.end(); img.save(path)

    def abrir(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir", "", "Img (*.png *.jpg)")
        if path: 
            pix = QPixmap(path).scaled(2000, 2000, Qt.AspectRatioMode.KeepAspectRatio)
            self.camadas[self.idx_ativa].pixmap = pix; self.camadas[self.idx_ativa].item.setPixmap(pix)

    def salvar_undo(self):
        if len(self.historico) > 10: self.historico.pop(0)
        self.historico.append((self.idx_ativa, self.camadas[self.idx_ativa].pixmap.copy()))

    def desfazer(self):
        if self.historico:
            i, pix = self.historico.pop()
            if i < len(self.camadas): self.camadas[i].pixmap = pix; self.camadas[i].item.setPixmap(pix)

    def keyPressEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier and e.key() == Qt.Key.Key_Z: 
            self.desfazer()
        elif e.key() == Qt.Key.Key_R: 
            self.view.resetTransform(); self.view.scale(1.0, 1.0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MeuDesenhoPro(); win.show(); app.exec()