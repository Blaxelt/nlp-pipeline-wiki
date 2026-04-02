.PHONY: start frontend backend

start:
	make -j2 backend frontend

backend:
	cd backend && uvicorn app.main:app --reload --log-level info

frontend:
	cd frontend && npm run dev