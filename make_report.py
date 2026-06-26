# -*- coding: utf-8 -*-
"""Generate a combined Word report for Homework #1 and #2 (Korean)."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn

BASE = "/projects/sandbox"
DS = os.path.join(BASE, "dataset")

doc = Document()

# ---- global style: Korean-friendly font, compact ----
style = doc.styles["Normal"]
style.font.name = "Malgun Gothic"
style.font.size = Pt(10)
style._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
style.paragraph_format.space_after = Pt(4)
style.paragraph_format.line_spacing = 1.08

# margins
for sec in doc.sections:
    sec.top_margin = Cm(1.8)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)


def set_kfont(run, size=None, bold=None, color=None):
    run.font.name = "Malgun Gothic"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color:
        run.font.color.rgb = color


def heading(text, size=13, space_before=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    set_kfont(r, size=size, bold=True, color=RGBColor(0x1F, 0x37, 0x64))
    return p


def subheading(text, size=11):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    set_kfont(r, size=size, bold=True)
    return p


def body(text, size=10):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_kfont(r, size=size)
    return p


def bullet(text, size=10):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    set_kfont(r, size=size)
    return p


def two_images(img1, cap1, img2, cap2, w=7.1):
    """Place two images side by side using a table."""
    t = doc.add_table(rows=2, cols=2)
    t.autofit = True
    for col, (img, cap) in enumerate([(img1, cap1), (img2, cap2)]):
        cell = t.cell(0, col)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(img, width=Cm(w))
        cap_cell = t.cell(1, col)
        cp = cap_cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(cap)
        set_kfont(r, size=8.5, bold=False, color=RGBColor(0x55, 0x55, 0x55))
    return t


def one_image(img, cap, w=11.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(img, width=Cm(w))
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cp.add_run(cap)
    set_kfont(r, size=8.5, color=RGBColor(0x55, 0x55, 0x55))


def make_table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = hdr[i].paragraphs[0].add_run(h)
        set_kfont(r, size=9, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cells[i].paragraphs[0].add_run(str(val))
            set_kfont(r, size=9)
    return t


# =====================================================================
# COVER PAGE (excluded from 4-page limit)
# =====================================================================
for _ in range(4):
    doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("전산재료공학 과제 보고서"); set_kfont(r, size=24, bold=True, color=RGBColor(0x1F, 0x37, 0x64))
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Homework #1 & #2"); set_kfont(r, size=16, bold=True)
for _ in range(2):
    doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("#1. 원형 홀을 포함한 평판의 2차원 선형탄성 유한요소해석\n"
              "#2. 압입시험 데이터 기반 탄성계수(E) 예측 인공신경망")
set_kfont(r, size=12)
for _ in range(8):
    doc.add_paragraph()
for label in ["과    목 : ____________________",
              "학    번 : ____________________",
              "이    름 : ____________________",
              "제 출 일 : 2026. __. __."]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(label); set_kfont(r, size=12)

doc.add_page_break()

# =====================================================================
# HOMEWORK #1
# =====================================================================
heading("Homework #1. 원형 홀을 포함한 평판의 2차원 선형탄성 유한요소해석 (Plane Stress)", size=13, space_before=0)
body("폭 W=2.0 m, 높이 H=1.0 m, 두께 t=0.01 m인 평판(중심 (0,0))에 중심 (0.1, 0), 반지름 r의 "
     "원형 홀을 둔 모델을 평면응력(Plane Stress) 조건에서 해석하였다. 재료는 E=210 GPa, ν=0.30이며, "
     "하단은 완전 고정(u=v=0), 상단은 위쪽으로 Δ=1×10⁻⁴ m의 변위를 강제하였다(변위 구속 조건).")

subheading("1) 예제 코드 8단계의 역할")
bullet("① 입력 파라미터: 형상(W,H,t), 재료물성(E,ν), 홀 위치·크기, 메쉬 간격(h, n_circle), 경계조건(Δ) 등 해석 조건 정의.")
bullet("② 재료물성·요소 정의: 평면응력 구성행렬 D 계산과 CST(상수변형률 삼각형) 요소의 B행렬·면적 계산 함수 정의.")
bullet("③ 모델·메쉬 생성: 격자점 생성 → 홀 내부 점 제거 → 경계·홀 경계점 추가 → Delaunay 삼각분할 → 홀 내부 요소 제거.")
bullet("④ 경계조건 설정: 하단/상단/좌우 경계 절점을 탐색하여 고정 및 변위 부여 대상 절점을 식별.")
bullet("⑤ 강성행렬 구성 및 해 계산: 요소 강성행렬 Kᵉ를 전체 행렬 K로 조립하고, Dirichlet 경계조건을 소거법으로 적용해 K_ff·U_f = −K_fc·U_c 를 풀어 변위 U를 구함.")
bullet("⑥ 후처리(응력·변형률): 각 요소에서 ε=B·u, σ=D·ε 및 von Mises 응력을 계산.")
bullet("⑦ 시각화 함수: 변형 형상과 응력·변형률 컨투어를 그리는 헬퍼 함수.")
bullet("⑧ 실행(Run): 위 단계를 순서대로 호출하여 해석을 수행하고 결과를 출력·시각화.")

subheading("2) 기본 해석 결과 (변위장·응력분포)")
body("상단을 위로 당기는 세로 인장 하중에 대해, 변위장은 상단에서 최대 수직변위를 보이고 하단 고정부에서 0이 되는 "
     "전형적 분포를 나타냈다. 응력은 홀 가장자리에서 집중되며, 특히 하중 방향과 수직인 홀의 좌·우 측면"
     "(x=cx±r, y=0)에서 σyy가 최대가 되고 홀의 상·하부는 저응력 영역으로 나타났다. 이는 원공 주위 응력집중 "
     "이론과 일치한다.")
two_images(os.path.join(BASE, "vonmises_r_min.png"), "그림 1. von Mises 응력 분포 (r=0.05)",
           os.path.join(BASE, "vonmises_r_max.png"), "그림 2. von Mises 응력 분포 (r=0.30)")

subheading("3) 파라미터 실험: 구멍 크기(r) 변경")
body("선택 변수로 구멍 크기 r을 0.05~0.30으로 변화시켜 응력집중계수(SCF=σyy,max/σ_nominal)를 분석하였다. "
     "정확도 향상을 위해 홀 경계 주변 메쉬를 점진적으로 조밀화하였다. 결과는 다음과 같다.")
make_table(["r (m)", "2r/W", "σyy,max [MPa]", "SCF (gross)", "SCF (net)"],
           [["0.05", "0.05", "62.0", "2.91", "2.76"],
            ["0.10", "0.10", "58.6", "2.84", "2.56"],
            ["0.15", "0.15", "54.0", "2.75", "2.34"],
            ["0.20", "0.20", "49.6", "2.68", "2.14"],
            ["0.25", "0.25", "45.7", "2.64", "1.98"],
            ["0.30", "0.30", "42.9", "2.66", "1.86"]])
one_image(os.path.join(BASE, "SCF_vs_holesize.png"), "그림 3. 구멍 크기(2r/W)에 따른 응력집중계수 변화", w=10.0)
subheading("결과 분석")
bullet("가장 작은 구멍(r=0.05)에서 SCF(gross) ≈ 2.91 로, 무한 평판·소형 원공의 고전 Kirsch 이론값 3에 거의 수렴 → 유한요소 모델의 타당성 검증.")
bullet("구멍이 커질수록 첨두 응력 σyy,max는 감소(62→43 MPa). 변위 구속 조건이라 구멍이 커지면 평판이 유연해져 전달 하중이 줄기 때문이다.")
bullet("net-section 기준 SCF는 단조 감소(2.76→1.86): 구멍이 커질수록 단면 응력 분포가 상대적으로 균등해지는 효과. 또한 본 시편은 높이 H가 짧고 구멍이 경계에 근접하여 무한 평판 가정에서 벗어나는 유한 효과가 관찰된다.")

# =====================================================================
# HOMEWORK #2
# =====================================================================
heading("Homework #2. 압입시험 데이터 기반 탄성계수(E) 예측 인공신경망", size=13, space_before=0)
body("수업에서 항복강도(YS)를 예측하던 동일 데이터셋(4,500개)을 사용하되, 목표변수(target)를 탄성계수 E로 "
     "변경하여 인공신경망(ANN)을 학습하였다. 입력변수(12개)는 Pmax, Stiffness2(제하 강성), Slope1~5, "
     "30~150 µm 변위에서의 하중값이다.")

subheading("1) 모델 구성 및 학습 과정")
bullet("모델: 다층 퍼셉트론(MLP) — Dense(128)-Dense(128)-Dropout(0.2)-Dense(64)-Dense(32)-Dense(1), 활성함수 ReLU, L2 정규화.")
bullet("손실함수 MAPE, 최적화기 Adam(lr=1e-3), 입력 Min-Max 정규화, 데이터 분할 70/15/15(train/val/test), EarlyStopping 적용.")
bullet("학습 곡선(그림 4): Training MAPE는 epoch 증가에 따라 빠르게 감소하여 ~1%로 수렴, Validation MAPE도 낮은 수준에서 안정화되어 양호하게 학습됨.")
two_images(os.path.join(DS, "E_mape_curve.png"), "그림 4. Epoch에 따른 MAPE 변화 곡선",
           os.path.join(DS, "E_reference_vs_prediction.png"), "그림 5. 실제값 vs 예측값 (Test)")

subheading("2) 예측 성능 평가 (Test data)")
make_table(["지표", "MAPE", "MAE", "RMSE"],
           [["값", "1.16 %", "1.72 GPa", "2.37 GPa"]])
body("그림 5의 실제값–예측값 산점도가 이상선(y=x)에 거의 완벽히 일치하며, MAPE 약 1.2%로 매우 높은 예측 정확도를 "
     "보였다. (참고: 동일 모델로 YS를 예측했을 때의 ~15%보다 훨씬 우수하며, 이는 탄성계수가 압입 데이터로 예측하기 "
     "용이한 물성임을 시사한다.)")

subheading("3) 입력 변수 중요도 분석 (Permutation Importance & SHAP)")
body("어떤 입력 변수가 E 예측에 가장 큰 영향을 미치는지 Permutation Importance(변수를 무작위로 섞었을 때 오차 "
     "증가량)와 SHAP(예측 기여도) 두 가지 방법으로 분석하였다.")
two_images(os.path.join(DS, "E_permutation_importance.png"), "그림 6. Permutation Importance",
           os.path.join(DS, "E_shap_importance.png"), "그림 7. SHAP 변수 중요도")
subheading("결과 해석")
bullet("두 방법 모두 Stiffness2(제하 강성)가 압도적 1위로, 나머지 변수를 모두 합친 것보다 영향력이 훨씬 크다. (Permutation: 해당 변수 셔플 시 MAPE +50%p, SHAP: 평균 영향 ≈46 GPa로 2위 대비 ~15배)")
bullet("이는 압입역학적으로 타당하다. Oliver–Pharr 이론에서 탄성계수 Er은 제하 강성 S와 직접 비례한다(Er = (√π/2)·S/√A). 즉, 신경망이 데이터만으로 탄성계수–제하강성의 물리적 관계를 스스로 학습했음을 의미한다.")
bullet("보조적으로 Slope4·Slope5(제하 구간 기울기) 등이 미미하게 기여하는 것도 제하 거동과 관련되어 합리적이다.")

subheading("4) 결론")
body("압입 데이터 기반 ANN은 탄성계수 E를 MAPE ≈1.2%의 높은 정확도로 예측하였으며, 변수 중요도 분석 결과 제하 "
     "강성이 결정적 변수로 나타났다. 이는 압입이론의 물리적 관계와 일치하여, 모델이 물리적으로 타당한 학습을 "
     "수행했음을 확인하였다.")

out = os.path.join(BASE, "과제보고서_HW1_HW2.docx")
doc.save(out)
print("Saved:", out)
