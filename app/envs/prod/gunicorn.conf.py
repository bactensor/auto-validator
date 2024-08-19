import multiprocessing

workers = 2 * multiprocessing.cpu_count() + 1
bind = "0.0.0.0:8000"
wsgi_app = "auto_validator.wsgi:application"
access_logfile = "-"
