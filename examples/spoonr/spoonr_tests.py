# -*- coding: utf-8 -*-
"""
    Flaskr Tests
    ~~~~~~~~~~~~

    Tests the Flaskr application.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import spoonr
import unittest
import tempfile


class SpoonrTestCase(unittest.TestCase):

    def setUp(self):
        """Before each test, set up a blank database"""
        self.db = tempfile.NamedTemporaryFile()
        self.app = spoonr.app.test_client()
        spoonr.DATABASE = self.db.name
        spoonr.init_db()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    # testing functions

    def test_empty_db(self):
        """Start with a blank database."""
        rv = self.app.get('/')
        assert 'No entries here so far' in rv.data

    def test_login_logout(self):
        """Make sure login and logout works"""
        rv = self.login(spoonr.USERNAME, spoonr.PASSWORD)
        assert 'You were logged in' in rv.data
        rv = self.logout()
        assert 'You were logged out' in rv.data
        rv = self.login(spoonr.USERNAME + 'x', spoonr.PASSWORD)
        assert 'Invalid username' in rv.data
        rv = self.login(spoonr.USERNAME, spoonr.PASSWORD + 'x')
        assert 'Invalid password' in rv.data

    def test_messages(self):
        """Test that messages work"""
        self.login(spoonr.USERNAME, spoonr.PASSWORD)
        rv = self.app.post('/add', data=dict(
            title='<Hello>',
            text='<strong>HTML</strong> allowed here'
        ), follow_redirects=True)
        assert 'No entries here so far' not in rv.data
        self.login(spoonr.USERNAME, spoonr.PASSWORD)
        assert '&lt;Hello&gt' in rv.data
        assert '<strong>HTML</strong> allowed here' in rv.data


if __name__ == '__main__':
    unittest.main()
