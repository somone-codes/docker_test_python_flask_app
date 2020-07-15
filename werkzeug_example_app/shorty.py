import os
import urllib.parse

import redis
from jinja2 import Environment, FileSystemLoader
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.routing import Map, Rule
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response


class Shorty(object):

    def __init__(self, configure):
        self.redis = redis.Redis(host=configure['host'], port=configure['port'], db=configure['db'])
        template_path = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
        self.url_map = Map([
            Rule("/", endpoint="new_url"),
            Rule("/<short_id>", endpoint="follow_short_link"),
            Rule("/<short_id>+", endpoint="short_link_details"),
        ])

    def on_follow_short_link(self, request, short_id):
        link_target = self.redis.get('url-target:' + short_id)
        if link_target is None:
            raise NotFound()
        self.redis.incr('click-count:' + short_id)
        return redirect(link_target)

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

    def on_short_link_details(self, request, short_id):
        link_target = self.redis.get('url-target:' + short_id)
        if link_target is None:
            raise NotFound()
        click_count = int(self.redis.get('click-count:' + short_id) or 0)
        link_target = link_target.decode('utf-8')
        return self.render_template('short_link_details.html',
                                    link_target=link_target,
                                    short_id=short_id,
                                    click_count=click_count
                                    )

    def base36_encode(self, number):
        assert number >= 0, 'positive integer required'
        if number == 0:
            return '0'
        base36 = []
        while number != 0:
            number, i = divmod(number, 36)
            base36.append('0123456789abcdefghijklmnopqrstuvwxyz'[i])
        return ''.join(reversed(base36))

    def insert_url(self, url):
        short_id = self.redis.get('reverse-url:' + url)
        if short_id is not None:
            return short_id
        url_num = self.redis.incr('last-url-id')
        short_id = self.base36_encode(url_num)
        self.redis.set('url-target:' + short_id, url)
        self.redis.set('reverse-url:' + url, short_id)
        return short_id

    def is_valid_url(self, url):
        parts = urllib.parse.urlparse(url)
        return parts.scheme in ('http', 'https')

    def on_new_url(self, request):
        error = None
        url = ''
        if request.method == 'POST':
            url = request.form['url']
            if not self.is_valid_url(url):
                error = 'Please enter a valid URL'
            else:
                short_id = self.insert_url(url)
                return redirect('/%s+' % short_id)
        return self.render_template('new_url.html', error=error, url=url)

    def dispatch_response(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_response(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app(host='localhost', port=6379, db=2, with_static=True):
    configure = {'host': host, 'port': port, 'db': db}
    app = Shorty(configure)
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static': os.path.join(os.path.dirname(__file__), 'static')
        })
    return app


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    from . import app

    run_simple(hostname='127.0.0.1', port=8000, application=app, use_debugger=False, static_files=False,
               use_reloader=False)