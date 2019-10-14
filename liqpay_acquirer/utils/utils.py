import base64
import hashlib


def to_unicode(s):
    """
    :param s:
    :return: unicode value (decoded utf-8)
    """
    if isinstance(s, unicode):
        return s
    if isinstance(s, basestring):
        return s.decode('utf-8', 'strict')
    if hasattr(s, '__unicode__'):
        return s.__unicode__()
    return unicode(bytes(s), 'utf-8', 'strict')


def smart_str(x):
    return to_unicode(x).encode('utf-8')


def make_signature(*args):
    """

    :param args: strings to join
    :return: sha1 hash of result of concatenating of *args strings
    """
    joined_fields = ''.join(smart_str(x) for x in args)
    return base64.b64encode(hashlib.sha1(joined_fields).digest())
