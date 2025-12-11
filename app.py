import sys
import random
import math
import zipfile
import io
import os
import time
import json
from datetime import datetime

from PyQt6.QtWidgets import (QApplication, QMainWindow, QColorDialog, 
                             QToolBar, QFileDialog, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QMessageBox, QDockWidget, QListWidget, 
                             QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QSlider, QInputDialog,
                             QStackedWidget, QDialog, QFormLayout, QSpinBox, QGridLayout) 
from PyQt6.QtGui import (QPixmap, QPainter, QPen, QColor, QAction, QTabletEvent, 
                         QPointingDevice, QBrush, QIcon, QImage, QPainterPath,
                         QLinearGradient, QRadialGradient, QPolygonF, 
                         QShortcut, QKeySequence, QTransform) 
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QPointF
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as db 

# --- CONFIGURAÇÃO DO MOTOR C++ ---
try:
    import motor_cpp
    print("============================================")
    print("   🚀 SUCESSO: MOTOR LIBMYPAINT CARREGADO!  ")
    print("============================================")
    MOTOR_C_ATIVO = True
except ImportError as e:
    print("============================================")
    print(f"   🐢 AVISO: MOTOR C++ FALHOU: {e}         ")
    print("============================================")
    MOTOR_C_ATIVO = False

# ============================================================================
# 1. CLASSES UTILITÁRIAS E DE DADOS
# ============================================================================

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
                "dinamica_tamanho": False, "dinamica_alpha": True, "texturizado": True, "textura": self.gerar_textura_forte(),
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
        p.setBrush(QColor(0, 0, 0, 20))
        p.drawEllipse(2, 2, 60, 60)
        for _ in range(400):
            x = random.randint(0, 64); y = random.randint(0, 64)
            dx = x - 32; dy = y - 32
            if dx*dx + dy*dy < 30*30:
                p.setPen(QColor(0, 0, 0, random.randint(50, 150)))
                p.drawPoint(x, y)
        p.end()
        return img

    def gerar_textura_forte(self): 
        img = QPixmap(64, 64)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 150))
        p.drawEllipse(2, 2, 60, 60)
        for _ in range(600):
            x = random.randint(0, 64); y = random.randint(0, 64)
            dx = x - 32; dy = y - 32
            if dx*dx + dy*dy < 30*30:
                p.setPen(QColor(0, 0, 0, 255)) 
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

# ============================================================================
# 2. COMPONENTES VISUAIS (CANVAS, CORES, DIALOGOS)
# ============================================================================

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

# --- NOVO: DIÁLOGO DE CRIAÇÃO DE ARQUIVO ---
class DialogoNovoArquivo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova Arte")
        self.setFixedSize(300, 200)
        self.setStyleSheet("background-color: #404040; color: white;")
        
        layout = QFormLayout(self)
        
        self.inp_largura = QSpinBox()
        self.inp_largura.setRange(64, 8000); self.inp_largura.setValue(2000)
        self.inp_largura.setSuffix(" px")
        
        self.inp_altura = QSpinBox()
        self.inp_altura.setRange(64, 8000); self.inp_altura.setValue(2000)
        self.inp_altura.setSuffix(" px")
        
        self.inp_nome = QtWidgets.QLineEdit("Sem Titulo")
        
        layout.addRow("Nome do Projeto:", self.inp_nome)
        layout.addRow("Largura:", self.inp_largura)
        layout.addRow("Altura:", self.inp_altura)
        
        btn_criar = QPushButton("CRIAR TELA")
        btn_criar.setStyleSheet("background-color: #007ACC; font-weight: bold; padding: 10px; border-radius: 5px;")
        btn_criar.clicked.connect(self.accept)
        layout.addWidget(btn_criar)

    def get_dados(self):
        return self.inp_nome.text(), self.inp_largura.value(), self.inp_altura.value()

# ============================================================================
# 3. TELAS DO SISTEMA (GALERIA E EDITOR)
# ============================================================================

# --- TELA 1: A GALERIA PROCREATE-STYLE ---
class TelaGaleria(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.caminho_galeria = os.path.join(os.path.expanduser("~"), "Desktop", "Galeria_Artes")
        
        if not os.path.exists(self.caminho_galeria):
            os.makedirs(self.caminho_galeria)

        layout = QVBoxLayout(self)
        
        # Cabeçalho
        topo = QHBoxLayout()
        lbl = QLabel("Minha Galeria"); lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #DDD;")
        topo.addWidget(lbl)
        topo.addStretch()
        
        # Botão NOVO (+)
        btn_novo = QPushButton(" + Nova Arte ")
        btn_novo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_novo.setStyleSheet("""
            QPushButton { background-color: #007ACC; color: white; font-size: 16px; font-weight: bold; border-radius: 8px; padding: 8px 15px; }
            QPushButton:hover { background-color: #0099FF; }
        """)
        btn_novo.clicked.connect(self.criar_novo)
        topo.addWidget(btn_novo)
        layout.addLayout(topo)

        # Grid de Artes
        self.lista_artes = QListWidget()
        self.lista_artes.setViewMode(QListWidget.ViewMode.IconMode)
        self.lista_artes.setIconSize(QSize(180, 180))
        self.lista_artes.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lista_artes.setSpacing(20)
        self.lista_artes.setStyleSheet("QListWidget { background-color: #303030; border: none; } QListWidget::item { color: white; } QListWidget::item:hover { background-color: #505050; border-radius: 10px; }")
        self.lista_artes.itemDoubleClicked.connect(self.abrir_arte)
        layout.addWidget(self.lista_artes)
        
        self.carregar_galeria()

    def carregar_galeria(self):
        self.lista_artes.clear()
        arquivos = [f for f in os.listdir(self.caminho_galeria) if f.endswith('.png')]
        arquivos.sort(key=lambda x: os.path.getmtime(os.path.join(self.caminho_galeria, x)), reverse=True)
        
        for arq in arquivos:
            caminho_completo = os.path.join(self.caminho_galeria, arq)
            icon = QIcon(caminho_completo)
            item = QListWidgetItem(arq.replace(".png", ""))
            item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, caminho_completo)
            self.lista_artes.addItem(item)

    def criar_novo(self):
        diag = DialogoNovoArquivo(self)
        if diag.exec():
            nome, w, h = diag.get_dados()
            # Manda criar o arquivo no Editor e muda a tela
            self.main.abrir_editor(w, h, nome)

    def abrir_arte(self, item):
        caminho = item.data(Qt.ItemDataRole.UserRole)
        self.main.abrir_editor_com_arquivo(caminho)

# --- TELA 2: O EDITOR DE DESENHO (Antigo MainWindow) ---
class TelaEditor(QMainWindow):
    def __init__(self, main_window):
        super().__init__()
        self.main_app = main_window # Referência ao Gerente
        self.caminho_atual = None
        
        # --- Configuração do Motor C++ ---
        if MOTOR_C_ATIVO:
            self.motor_fisico = motor_cpp.MotorMyPaint()
            self.tempo_anterior = time.time()
        else:
            self.motor_fisico = None
            
        self.setStyleSheet("QMainWindow { background-color: #404040; } QDockWidget { color: white; font-weight: bold; background-color: #353535; } QListWidget { background-color: #353535; } QLabel { color: white; }")
        
        # Dados Iniciais
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

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor("#202020"))
        
        self.view = CanvasView(self.scene, self)
        self.setCentralWidget(self.view)

        self.setup_docks(); self.setup_toolbar(); self.setup_menus()
        
        # Atalho Tab
        self.sh_tab = QShortcut(QKeySequence("Tab"), self)
        self.sh_tab.activated.connect(self.toggle_zen_mode)

    # --- INICIALIZAÇÃO DA TELA (CHAMADO PELA GALERIA) ---
    def novo_projeto(self, w, h, nome="Sem Titulo"):
        self.scene.clear(); self.camadas = []; self.historico = []
        self.scene.setSceneRect(0, 0, w, h)
        
        # Define caminho de salvamento automático
        safe_name = "".join([c for c in nome if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        self.caminho_atual = os.path.join(self.main_app.galeria.caminho_galeria, f"{safe_name}.png")
        if os.path.exists(self.caminho_atual): # Evita sobrescrever
            self.caminho_atual = os.path.join(self.main_app.galeria.caminho_galeria, f"{safe_name}_{int(time.time())}.png")

        bg = DadosCamada("Papel", w, h, 0); bg.pixmap.fill(QColor("#F5F5F0"))
        bg.item.setPixmap(bg.pixmap); self.scene.addItem(bg.item); self.camadas.append(bg)
        self.nova_camada(); self.idx_ativa = 1; self.atualizar_lista_camadas()
        
        # Centraliza a vista
        self.view.resetTransform()
        self.view.centerOn(w/2, h/2)
        self.view.scale(0.8, 0.8) # Zoom out inicial para ver tudo

    def carregar_projeto(self, caminho):
        self.caminho_atual = caminho
        pix = QPixmap(caminho)
        w, h = pix.width(), pix.height()
        
        self.scene.clear(); self.camadas = []; self.historico = []
        self.scene.setSceneRect(0, 0, w, h)
        
        bg = DadosCamada("Fundo (Imagem)", w, h, 0); bg.pixmap = pix
        bg.item.setPixmap(bg.pixmap); self.scene.addItem(bg.item); self.camadas.append(bg)
        
        self.nova_camada(); self.idx_ativa = 1; self.atualizar_lista_camadas()
        self.view.resetTransform(); self.view.centerOn(w/2, h/2); self.view.scale(0.8, 0.8)

    # --- LÓGICA DE DESENHO E FERRAMENTAS ---
    # (Mantida idêntica à versão anterior, apenas indentada)
    def processar_desenho(self, pos, pressao, eraser):
        if self.idx_ativa >= len(self.camadas): return
        cam = self.camadas[self.idx_ativa]
        if not cam.visivel or cam.trancada: return

        conf = self.motor.pegar_config()
        tam = self.tam_base
        eh_borracha = (self.ferramenta == "borracha") or eraser
        
        if eh_borracha:
            modo = QPainter.CompositionMode.CompositionMode_DestinationOut if conf.get("texturizado") else QPainter.CompositionMode.CompositionMode_Clear
        else:
            modo = self.blend_atual
        
        p1, p2 = self.ultimo_ponto, pos
        dist = math.hypot(p2.x()-p1.x(), p2.y()-p1.y())
        if dist == 0: return

        p = QPainter(cam.pixmap)
        p.setCompositionMode(modo)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # MISTURA
        cor_uso = self.cor_pincel
        if self.fator_mistura > 0 and self.cache_leitura and not eh_borracha:
            x_read = max(0, min(self.cache_leitura.width()-1, int(p1.x())))
            y_read = max(0, min(self.cache_leitura.height()-1, int(p1.y())))
            cor_fundo = self.cache_leitura.pixelColor(x_read, y_read)
            r = int(self.cor_pincel.red() * (1 - self.fator_mistura) + cor_fundo.red() * self.fator_mistura)
            g = int(self.cor_pincel.green() * (1 - self.fator_mistura) + cor_fundo.green() * self.fator_mistura)
            b = int(self.cor_pincel.blue() * (1 - self.fator_mistura) + cor_fundo.blue() * self.fator_mistura)
            cor_uso = QColor(r, g, b, self.cor_pincel.alpha())

        eh_mypaint = conf.get("eh_mypaint_oficial", False)
        
        if (not conf.get("texturizado") and not eh_mypaint) or (eh_borracha and not conf.get("texturizado")) or not MOTOR_C_ATIVO:
            tam_final = max(1, tam * pressao) if conf["dinamica_tamanho"] else tam
            alpha_final = pressao if conf["dinamica_alpha"] else 1.0
            p.setOpacity(alpha_final * self.opac_global)
            pen = QPen(Qt.GlobalColor.transparent if eh_borracha else cor_uso, tam_final, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen); p.drawLine(p1, p2)
        
        elif MOTOR_C_ATIVO and (conf.get("texturizado") or eh_mypaint):
            agora = time.time()
            dt = agora - self.tempo_anterior
            self.tempo_anterior = agora
            
            if eh_mypaint and "dados_mypaint" in conf:
                settings = conf["dados_mypaint"].get("settings", {})
                for nome_setting, valor in settings.items():
                    v_final = valor.get("base_value", 0.0)
                    self.motor_fisico.set_parametro_por_nome(nome_setting, float(v_final))
            else:
                self.motor_fisico.set_config(0, float(tam) * 0.1) 
                self.motor_fisico.set_config(1, float(self.opac_global))

            dabs = self.motor_fisico.atualizar_traco(pos.x(), pos.y(), pressao, dt)
            tex = self.motor.pegar_textura_atual()
            for x, y, raio, opac in dabs:
                diametro = raio * 2
                if diametro < 0.5: continue
                p.setOpacity(opac)
                tex_scaled = tex.scaled(int(diametro), int(diametro), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                p.drawPixmap(int(x - diametro/2), int(y - diametro/2), tex_scaled)
        
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
        self.ultimo_ponto = pos; self.resto_dist = 0
        if MOTOR_C_ATIVO and self.motor_fisico:
            self.tempo_anterior = time.time(); self.motor_fisico.reset()
        if self.idx_ativa < len(self.camadas):
            self.cache_leitura = self.camadas[self.idx_ativa].pixmap.toImage()

    def tratar_fim_traco(self):
        self.ultimo_ponto = None; self.cache_leitura = None 

    # --- UI SETUP ---
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
        # Botão de Voltar para a Galeria
        btn_home = QAction("🏠 Galeria", self)
        btn_home.triggered.connect(self.voltar_para_galeria)
        tb.addAction(btn_home)
        tb.addSeparator()
        
        tb.addWidget(QLabel("📏")); sl_tam = QSlider(Qt.Orientation.Horizontal); sl_tam.setRange(1, 300); sl_tam.setValue(30)
        sl_tam.valueChanged.connect(lambda v: setattr(self, 'tam_base', v)); tb.addWidget(sl_tam)
        tb.addWidget(QLabel("💧")); sl_op = QSlider(Qt.Orientation.Horizontal); sl_op.setRange(0, 100); sl_op.setValue(100)
        sl_op.valueChanged.connect(lambda v: setattr(self, 'opac_global', v/100)); tb.addWidget(sl_op)
        tb.addWidget(QLabel("🌀")); self.sl_mix = QSlider(Qt.Orientation.Horizontal); self.sl_mix.setRange(0, 100); self.sl_mix.setValue(0)
        self.sl_mix.valueChanged.connect(lambda v: setattr(self, 'fator_mistura', v/100)); tb.addWidget(self.sl_mix)
        cb_blend = QComboBox(); cb_blend.addItems(self.modos_blend.keys())
        cb_blend.currentTextChanged.connect(lambda t: setattr(self, 'blend_atual', self.modos_blend[t]))
        tb.addWidget(cb_blend)
        tb.addAction("💾", self.salvar_rapido); tb.addAction("📂", self.abrir); tb.addAction("🧼", lambda: setattr(self, 'ferramenta', 'borracha'))

    def setup_menus(self):
        m = self.menuBar().addMenu("Exibir")
        m.addAction(self.dk_cor.toggleViewAction()); m.addAction(self.dk_brush.toggleViewAction())
        m.addAction(self.dk_layer.toggleViewAction()); m.addAction("Tela Cheia (Tab)", self.toggle_zen_mode)

    # --- FUNÇÕES DE CONTROLE ---
    def voltar_para_galeria(self):
        self.salvar_rapido(silencioso=True)
        self.main_app.ir_para_galeria()

    def salvar_rapido(self, silencioso=False):
        if self.caminho_atual:
            img = QPixmap(self.scene.width(), self.scene.height())
            img.fill(Qt.GlobalColor.transparent); p = QPainter(img)
            # Fundo Branco Padrão se não tiver
            p.fillRect(img.rect(), Qt.GlobalColor.white)
            for c in self.camadas: 
                if c.visivel: 
                    opt = QtWidgets.QStyleOptionGraphicsItem(); c.item.paint(p, opt, None)
            p.end(); img.save(self.caminho_atual)
            if not silencioso: QMessageBox.information(self, "Salvo", "Arte salva na Galeria!")

    def toggle_zen_mode(self):
        self.modo_zen = not self.modo_zen
        if self.modo_zen:
            self.showFullScreen(); self.menuBar().hide(); self.dk_cor.hide(); self.dk_brush.hide(); self.dk_layer.hide()
        else:
            self.showNormal(); self.menuBar().show(); self.dk_cor.show(); self.dk_brush.show(); self.dk_layer.show()

    def nova_camada(self):
        idx = len(self.camadas); c = DadosCamada(f"Camada {idx}", int(self.scene.width()), int(self.scene.height()), idx)
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

    def mudar_pincel(self, nome): 
        self.motor.pincel_atual = nome
        if "Borracha" in nome: self.ferramenta = "borracha"
        else: self.ferramenta = "pincel"
        conf = self.motor.pegar_config()
        self.fator_mistura = conf.get("mistura_padrao", 0) / 100.0
        self.sl_mix.setValue(conf.get("mistura_padrao", 0))

    def atualizar_lista_pinceis(self):
        self.lst_brush.clear()
        for nome in self.motor.estilos:
            it = QListWidgetItem(nome); icon = QIcon(self.motor.estilos[nome]["textura"] or self.motor.gerar_icone_generico(nome))
            it.setIcon(icon); self.lst_brush.addItem(it)

    def importar_brush(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Pincel", "", "MyPaint Brush (*.myb);;Imagens (*.png *.jpg *.bundle)")
        if not path: return
        nome_arquivo = os.path.basename(path)
        if path.endswith(".myb"):
            try:
                with open(path, 'r') as f: dados_json = json.load(f)
                self.motor.criar_novo_pincel_customizado(nome_arquivo, None)
                config = self.motor.estilos[self.motor.pincel_atual]
                config["dados_mypaint"] = dados_json; config["eh_mypaint_oficial"] = True
                QMessageBox.information(self, "Sucesso", f"Pincel '{nome_arquivo}' importado!")
                self.atualizar_lista_pinceis()
            except Exception as e: QMessageBox.warning(self, "Erro", f"Erro ao ler .myb: {e}")
        elif path.endswith(".bundle"):
            with zipfile.ZipFile(path, 'r') as z:
                for f in z.namelist():
                    if f.endswith(('.png','.jpg')) and "preview" not in f:
                        pix = QPixmap(); pix.loadFromData(z.read(f))
                        if not pix.isNull(): self.motor.criar_novo_pincel_customizado(os.path.basename(f), pix)
            self.atualizar_lista_pinceis()
        else:
            pix = QPixmap(path)
            if not pix.isNull(): 
                self.motor.criar_novo_pincel_customizado("Custom Image", pix)
                self.atualizar_lista_pinceis()

    def salvar(self):
        # Salvar Como (Exportar)
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Imagem", "", "PNG (*.png)")
        if path:
            img = QPixmap(self.scene.width(), self.scene.height())
            img.fill(Qt.GlobalColor.transparent); p = QPainter(img); p.fillRect(img.rect(), Qt.GlobalColor.white)
            for c in self.camadas: 
                if c.visivel: opt = QtWidgets.QStyleOptionGraphicsItem(); c.item.paint(p, opt, None)
            p.end(); img.save(path)

    def abrir(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Imagem", "", "Img (*.png *.jpg)")
        if path: self.carregar_projeto(path)

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
            self.view.resetTransform(); self.view.scale(0.8, 0.8)

# ============================================================================
# 4. JANELA GERENTE (CONTROLA TUDO)
# ============================================================================
class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SamK Art Studio Pro")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("background-color: #252525;")

        # StackedWidget: Permite trocar de telas (Galeria <-> Editor)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Cria as duas telas
        self.galeria = TelaGaleria(self)
        self.editor = TelaEditor(self)

        self.stack.addWidget(self.galeria) # Index 0
        self.stack.addWidget(self.editor)  # Index 1

        self.ir_para_galeria()

    def ir_para_galeria(self):
        self.galeria.carregar_galeria() # Recarrega as imagens salvas
        self.stack.setCurrentIndex(0)

    def abrir_editor(self, w, h, nome):
        self.editor.novo_projeto(w, h, nome)
        self.stack.setCurrentIndex(1)

    def abrir_editor_com_arquivo(self, caminho):
        self.editor.carregar_projeto(caminho)
        self.stack.setCurrentIndex(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = JanelaPrincipal()
    win.show()
    app.exec()