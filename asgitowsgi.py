#taken from https://gist.githubusercontent.com/mtorromeo/f7608efc5dad47299f9e270a069c9159/raw/d3da1cf0924cf68d76d413d95fda5d45c76a5890/asgitowsgi.py
import asyncio
import sys

from http import HTTPStatus


RESPONSE_STATUS_TEXT = {
    code: str(code) for code in range(100, 600)
}
RESPONSE_STATUS_TEXT.update({
    status.value: "%d %s" % (status.value, status.phrase)
    for status in HTTPStatus
})


class ASGItoWSGIAdapter(object):
    """
    Expose an WSGI interface, given an ASGI application.
    """
    def __init__(self, asgi, raise_exceptions=False):
        self.asgi = asgi
        self.raise_exceptions = raise_exceptions
        self.loop = asyncio.get_event_loop()

    def __call__(self, environ, start_response):
        return_bytes = []
        message = self.environ_to_message(environ)

        async def send(msg):
            if msg['type'] == 'http.response.start':
                status = RESPONSE_STATUS_TEXT[msg['status']]
                headers = [
                    [key.decode('latin-1'), value.decode('latin-1')]
                    for key, value in msg['headers']
                ]
                exc_info = sys.exc_info()
                start_response(status, headers, exc_info)
            elif msg['type'] == 'http.response.body':
                return_bytes.append(msg.get('body', b''))

        async def receive():
            return {
                'type': 'http.request',
                'body': environ['wsgi.input'].read()
            }

        try:
            self.loop.run_until_complete(self.asgi(message, receive, send))
        except Exception:
            if self.raise_exceptions:
                raise

        return return_bytes

    def environ_to_message(self, environ):
        """
        WSGI environ -> ASGI message
        """
        message = {
            'type': 'http',
            'method': environ['REQUEST_METHOD'].upper(),
            'root_path': environ.get('SCRIPT_NAME', ''),
            'path': environ.get('PATH_INFO', ''),
            'query_string': environ.get('QUERY_STRING', '').encode('latin-1'),
            'http_version': environ.get('SERVER_PROTOCOL', 'http/1.0').split('/', 1)[-1],
            'scheme': environ.get('wsgi.url_scheme', 'http'),
            'raise_exceptions': self.raise_exceptions  # Not actually part of the ASGI spec
        }

        if 'REMOTE_ADDR' in environ and 'REMOTE_PORT' in environ:
            message['client'] = [environ['REMOTE_ADDR'], int(environ['REMOTE_PORT'])]
        if 'SERVER_NAME' in environ and 'SERVER_PORT' in environ:
            message['server'] = [environ['SERVER_NAME'], int(environ['SERVER_PORT'])]

        headers = []
        if environ.get('CONTENT_TYPE'):
            headers.append([b'content-type', environ['CONTENT_TYPE'].encode('latin-1')])
        if environ.get('CONTENT_LENGTH'):
            headers.append([b'content-length', environ['CONTENT_LENGTH'].encode('latin-1')])
        for key, val in environ.items():
            if key.startswith('HTTP_'):
                key_bytes = key[5:].replace('_', '-').lower().encode('latin-1')
                val_bytes = val.encode()
                headers.append([key_bytes, val_bytes])

        message['headers'] = headers

        return message
