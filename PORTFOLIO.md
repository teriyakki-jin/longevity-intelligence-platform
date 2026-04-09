# Longevity Intelligence Platform

> **혈액 바이오마커 데이터로 생물학적 나이와 사망 위험을 예측하고, Digital Twin 시뮬레이션으로 라이프스타일 개선 효과를 10년 단위로 시각화하는 개인 건강 인텔리전스 플랫폼**

---

## 프로젝트 개요

CDC NHANES 2009–2020 공개 데이터셋(약 4만 명)을 기반으로, 혈액 검사 수치만으로 생물학적 나이·사망 위험·원인별 사망 확률을 동시에 추론하는 ML 파이프라인을 구축했습니다. 단순 예측에서 그치지 않고 Monte Carlo 시뮬레이션과 Causal DAG를 결합한 Digital Twin 엔진으로 "금연하면 생물학적 나이가 몇 년 낮아지는가"를 정량적으로 답합니다. FastAPI + Next.js 풀스택으로 전 기능을 인터랙티브 대시보드에 통합했습니다.

---

## 핵심 기능

- 🧬 **Biological Age Clock** — LightGBM + Optuna HPO(80 trials)로 혈액 바이오마커에서 생물학적 나이를 회귀 추론. SHAP Waterfall Chart로 기여 바이오마커 즉시 시각화
- ☠️ **Mortality Risk Modeling** — Cox Proportional Hazards로 5년·10년 생존 곡선 산출(C-index 0.8373). XGBoost 멀티클래스로 심혈관·암·호흡기·당뇨·사고사 원인별 AUC > 0.80
- 🔮 **Digital Twin Simulation** — Causal DAG 기반 인과 개입 효과를 Monte Carlo 500회 반복으로 95% 신뢰구간까지 계산. 슬라이더 조작 → 10년 생물학적 나이 궤적 실시간 렌더링
- 🤖 **AI Health Coach** — Claude API + SSE Streaming으로 예측 결과를 맥락으로 활용하는 개인화 헬스 코칭

---

## 모델 성능

| 모델 | 알고리즘 | 지표 | 값 |
|------|----------|------|-----|
| Biological Age Clock | LightGBM + Optuna HPO | MAE | < 5년 |
| Biological Age Clock | LightGBM + Optuna HPO | Pearson r | > 0.95 |
| All-cause Mortality | Cox Proportional Hazards | C-index | **0.8373** |
| Cause-Specific (5종) | XGBoost | AUC | > 0.80 |

> Optuna Bayesian HPO 80 trials 기준. 학습 데이터: NHANES 2009–2020 6개 서베이 사이클 + CDC Mortality Linkage File (n ≈ 40,000)

---

## 기술 스택

| 레이어 | 사용 기술 |
|--------|----------|
| ML | LightGBM · XGBoost · lifelines · SHAP · Optuna |
| Backend | FastAPI · uvicorn · pydantic v2 · Python 3.10 |
| Frontend | Next.js 14 App Router · TypeScript · Tailwind CSS · D3.js |
| Training | Google Colab · Google Drive |
| Streaming | SSE (Server-Sent Events) · Claude API |

---

## 시스템 아키텍처

```
[Google Colab]
  NHANES .xpt + Mortality .dat 파싱
  → Feature Engineering (eGFR, FIB-4, Metabolic Syndrome Score 등)
  → LightGBM HPO (Optuna 80 trials)  → blood_clock.joblib
  → Cox PH (lifelines)               → cox.joblib
  → XGBoost 5-class                  → cause_specific.joblib
           │
           ▼ (Google Drive → 로컬 다운로드)
[FastAPI :8888]
  POST /api/v1/bioage/predict       생물학적 나이 + SHAP
  POST /api/v1/mortality/predict    생존 곡선 + 원인별 위험
  POST /api/v1/twin/simulate        Monte Carlo 500회
  GET  /api/v1/health
           │
           ▼ (REST + SSE)
[Next.js 14 Dashboard :3000]
  /          → Bio Age 입력 폼 + SHAP Waterfall Chart (D3.js)
  /twin      → 라이프스타일 슬라이더 + 10yr Trajectory (D3.js)
  /mortality → 원인별 위험 Bar Chart + Survival Curve (D3.js)
  /coach     → SSE 스트리밍 AI 헬스 코치
```

---

## 기술적 도전 & 해결

### 1. CDC 공식 문서의 바이트 위치 오류 — 직접 역공학

NHANES 사망률 연계 파일(Fixed-Width .dat)의 follow-up 기간 컬럼 바이트 위치가 공식 문서에 **21–30**으로 명시되어 있으나 실제 파싱 시 전체 NaN 반환. 파일을 바이트 단위로 슬라이싱하며 반복 검증한 결과 **실제 위치는 42–47**임을 경험적으로 확인. 공식 문서를 신뢰하지 않고 데이터를 직접 검증하는 것의 중요성.

### 2. pandas nullable Int64 vs float64 — merge 0건 버그

`read_sas()` → SEQN이 `float64`, `read_fwf()` → SEQN이 `Int64(nullable)`. 두 타입 간 merge 시 키 매칭 실패로 결과 0행. pandas 내부 타입 비교 동작을 파악하고 양쪽을 `int`로 통일하여 해결.

### 3. Digital Twin Causal DAG — 개입 효과 정규화

라이프스타일 슬라이더의 raw delta(예: 운동 +190분)를 바이오마커에 직접 전파하면 BMI가 8.3으로 떨어지는 등 비현실적 값 발생 → 모델 외삽 오류. 각 개입 변수의 **학습 데이터 SD로 delta를 정규화**하여 causal effect를 통계적으로 합리적인 범위 내로 제약. Monte Carlo 신뢰구간은 percentile bootstrap으로 산출.

---

## 데이터

**NHANES (National Health and Nutrition Examination Survey)**

- **출처**: CDC (미국 질병통제예방센터) 공개 데이터 · Public Domain
- **기간**: 2009–2020 (6개 2년 주기 서베이 사이클)
- **규모**: 약 40,000명, 사망률 연계 파일 포함
- **주요 피처**: 혈중 포도당, HbA1c, 총콜레스테롤, HDL/LDL, 중성지방, 크레아티닌, 알부민, CRP, ALT/AST, WBC, 혈색소, BMI, 허리둘레, 흡연·음주 이력

6개 사이클을 SEQN 기준으로 수직 병합 후 CDC Mortality Linkage File(2019 공개 버전)과 조인하여 생존 분석용 데이터셋 구성.

---

## Links

**GitHub**: [github.com/teriyakki-jin/longevity-intelligence-platform](https://github.com/teriyakki-jin/longevity-intelligence-platform)

---

*LightGBM · XGBoost · lifelines · SHAP · Optuna · FastAPI · Next.js 14 · D3.js · Claude API*
