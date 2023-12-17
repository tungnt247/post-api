run:
	gunicorn wsgi:app -w 4 -b 0.0.0.0

image:
	docker build -t api . && docker run -dp 8000:8000 api
