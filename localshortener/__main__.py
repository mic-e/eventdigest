import flask
from eventdigest.util import redirects

site = flask.Flask("shortener")


@site.route('/<link>')
def redirecter(link):
    try:
        return flask.redirect(redirects[link])
    except KeyError:
        return "unknown redirect"


if __name__ == '__main__':
    site.run(port=8080)
