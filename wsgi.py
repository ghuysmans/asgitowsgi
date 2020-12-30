def application(environ, start_response):
    print(environ)
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello from WSGI']
