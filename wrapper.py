from asgi import app
from asgitowsgi import ASGItoWSGIAdapter

application = ASGItoWSGIAdapter(app)
