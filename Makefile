.PHONY: install web api docker
install:
	python -m pip install -r requirements.txt
web:
	cd frontend && npm install && npm run dev
api:
	uvicorn app.main:app --reload