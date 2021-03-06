import requests


class Hammock(object):
    """Chainable, magical class helps you make requests to RESTful services"""

    HTTP_METHODS = ['get', 'options', 'head', 'post', 'put', 'patch', 'delete']

    def __init__(self, name=None, parent=None, append_slash=False, **kwargs):
        """Constructor

        Arguments:
            name -- name of node
            parent -- parent node for chaining
            **kwargs -- `requests` session be initiated with if any available
        """
        self._name = name
        self._parent = parent
        self._append_slash = append_slash
        self._session = kwargs and requests.session(**kwargs) or None

    def __getattr__(self, name):
        """Here comes some magic. Any absent attribute typed within class
        falls here and return a new child `Hammock` instance in the chain.
        """
        chain = self.__class__(name=name, parent=self, append_slash=self._append_slash)
        for attribute, value in self.__dict__.items():
            if attribute not in ('_name', '_parent', '_append_slash'):
               setattr(chain, attribute, value)

        return chain

    def __iter__(self):
        """Iterator implementation which iterates over `Hammock` chain."""
        current = self
        while current:
            if current._name:
                yield current
            current = current._parent

    def _chain(self, *args):
        """This method converts args into chained Hammock instances

        Arguments:
            *args -- array of string representable objects
        """
        chain = self
        for arg in args:
            chain = self.__class__(name=str(arg), parent=chain, append_slash=self._append_slash)
        for attribute, value in self.__dict__.items():
            if attribute not in ('_name', '_parent', '_append_slash'):
                setattr(chain, attribute, value)

        return chain

    def _probe_session(self):
        """This method searches for a `requests` session sticked to any
        ascending parent `Hammock` instance
        """
        for hammock in self:
            if hammock._session:
                return hammock._session
        return None

    def _close_session(self, probe=False):
        """Closes session if exists

        Arguments:
            probe -- search through ascendants if any session available
                to close
        """
        session = probe and self._probe_session() or self._session
        if session:
            session.close()

    def __call__(self, *args):
        """Here comes second magic. If any `Hammock` instance called it
        returns a new child `Hammock` instance in the chain
        """
        return self._chain(*args)

    def _url(self, *args):
        """Converts current `Hammock` chain into a url string

        Arguments:
            *args -- extra url path components to tail
        """
        path_comps = [mock._name for mock in self._chain(*args)]

        if self._append_slash:
            url = "/".join(reversed(path_comps))
            return url + '/'
        else:
            return "/".join(reversed(path_comps))

    def __repr__(self):
        """ String representaion of current `Hammock` chain"""
        return self._url()

    def _request(self, method, *args, **kwargs):
        """
        Makes the HTTP request using requests module
        """
        session = self._probe_session() or requests
        return session.request(method, self._url(*args), **kwargs)


def bind_method(method):
    """Bind `requests` module HTTP verbs to `Hammock` class as
    static methods."""
    def aux(hammock, *args, **kwargs):
        # allows to do GET(filter=12) instead of having to do
        # GET({'params': {'filter': 12}})
        # This is a list of special keyword arguments in requests
        REQUESTS_SPECIAL_KEYS = set([
            'params', 'headers', 'cookies', 'auth', 'timeout',
            'allow_redirects', 'proxies', 'return_response', 'session',
            'config', 'verify', 'prefetch', 'cert'
        ])
        if method == 'get' and kwargs and 'params' not in kwargs:
            special_key_found = non_special_key_found = False
            params_to_send = {}

            for key in kwargs:
                if key not in REQUESTS_SPECIAL_KEYS:
                    non_special_key_found = True
                    params_to_send.setdefault('params', {}).update(
                        {key: kwargs[key]}
                    )
                else:
                    special_key_found = True

            if special_key_found and non_special_key_found:
                raise Exception("You cannot pass a requests kwarg and an \
                    unknown kwarg together")

            if non_special_key_found:
                kwargs = params_to_send

        return hammock._request(method, *args, **kwargs)
    return aux


for method in Hammock.HTTP_METHODS:
    setattr(Hammock, method.upper(), bind_method(method))
