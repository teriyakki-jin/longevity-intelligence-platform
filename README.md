# 🧬 Longevity Intelligence Platform

Personal AI health platform that predicts **biological age**, models **mortality risk**, simulates a **digital health twin**, and provides an **AI-powered health coach** — all trained on NHANES public datasets (CDC, 2009–2020, n≈40,000).

---

## Models

| Model | Algorithm | Performance |
|-------|-----------|-------------|
| Biological Age Clock | LightGBM + Optuna HPO | MAE < 5yr, r > 0.95 |
| Mortality Risk | Cox Proportional Hazards | C-index 0.8373 |
| Cause-Specific Mortality | XGBoost (5 causes) | AUC > 0.80 |
| Digital Twin | Monte Carlo + Causal DAG | 500 simulations |

---

## Quick Start

### 1. Clone
```bash
git clone https://github.com/teriyakki-jin/longevity-intelligence-platform.git
cd longevity-intelligence-platform
```

### 2. Install Python deps
```bash
pip install -e . --no-deps
pip install fastapi uvicorn lightgbm xgboost lifelines shap structlog pydantic-settings anthropic
```

### 3. Download trained models
Run **Cell 8** in `notebooks/colab_train.ipynb` on Google Colab → downloads `longevity-models.zip`.

Unzip into project root:
```bash
unzip longevity-models.zip  # creates models/bioage/ models/mortality/
```

### 4. Start backend
```bash
python run_api.py --port 8888
# API docs: http://localhost:8888/docs
```

### 5. Start dashboard
```bash
cd dashboard
echo "NEXT_PUBLIC_API_URL=http://localhost:8888/api/v1" > .env.local
npm install && npm run dev
# Dashboard: http://localhost:3000
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/bioage/predict` | Predict biological age from blood markers |
| `POST /api/v1/mortality/predict` | 5yr/10yr survival + cause breakdown |
| `POST /api/v1/twin/simulate` | Monte Carlo lifestyle intervention simulation |
| `GET  /api/v1/health` | Health check |

---

## Training (Google Colab)

Open `notebooks/colab_train.ipynb` in Colab:

1. **Cell 1** — Install deps + runtime restart
2. **Cell 3** — Clone repo
3. **Cells 4–27** — Download NHANES, train all models
4. **Cell 29** — Save to Google Drive
5. **Cell 31** — Download models as zip

---

## Stack

**ML**: LightGBM · XGBoost · lifelines (Cox PH) · SHAP · Optuna  
**Backend**: FastAPI · uvicorn · pydantic v2  
**Frontend**: Next.js 14 · TypeScript · Tailwind CSS · D3.js  
**Data**: NHANES 2009–2020 (CDC public domain)
