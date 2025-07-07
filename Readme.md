# ❶ clone / copy the folder, then:
cd flask_file_app

# ❷ create & activate a virtual‑environment
python -m venv venv
source venv/bin/activate       
# Windows: 
venv\Scripts\activate

# ❸ install deps
pip install -r requirements.txt

# ❹ start the app
python app.py
# → Serving on http://127.0.0.1:5000

# run test cases
python -m pytest tests/test_api.py

# check code coverage
python -m pytest --cov=app tests/