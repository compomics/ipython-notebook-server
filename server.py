import tornado.ioloop
import tornado.web
import MySQLdb
import logging
import os
import socket
from urlparse import urlparse
import shutil
import subprocess
import time


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        """ Display login page """
        self.render('index.html', username='')

    def post(self):
        """ Process login form, set up or recall user and session """
        conn = None
        port = None
        session_exists = False
        username = self.get_argument('username', '').strip()
        port_query = 'SELECT MIN(s1.port + 1) AS next FROM sessions s1 LEFT JOIN sessions s2 ON s1.port + 1 = s2.port WHERE s2.port IS NULL'

        """ Fill in database login details here, see db.sql for schema """
        db_host = None
        db_user = None
        db_password = None

        if len(username) > 0 and username.isalnum():
            try:
                conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, db='ipy')

                with conn:
                    db = conn.cursor()

                    db.execute('SELECT id FROM users WHERE username=%s', username)
                    row = db.fetchone()
                    
                    if row is None:
                        logging.info('creating new user: ' + username)
                        db.execute('INSERT INTO users (username) VALUES (%s)', username)
                        db.execute('SELECT id FROM users WHERE username=%s', username)
                        self.create_user(username)
                        row = db.fetchone()
                        user_id = row[0]
                    else:
                        user_id = row[0]

                    db.execute('SELECT * FROM sessions WHERE user_id = %s', user_id)
                    row = db.fetchone()

                    if row is not None:
                        if self.process_exists(row[3]):
                            port = row[2]
                            db.execute('UPDATE sessions SET updated = %s WHERE user_id = %s', (int(time.time()), user_id))
                            session_exists = True
                        else:
                            db.execute('DELETE FROM sessions WHERE user_id = %s', user_id)

                            db.execute(port_query)
                            row = db.fetchone()
                            
                            port = row[0]
                    else:
                        db.execute(port_query)
                        row = db.fetchone()

                        if row[0] is None:
                            port = 8000
                        else:
                            port = row[0]

                    profile_path = self.write_config(username, port)

                    if session_exists:
                        logging.info('Reconnecting to iPython process: ' + str(session_exists))
                    else:
                        logging.info('Starting iPython server for: ' + username)

                        iprocess = subprocess.Popen(['/usr/local/bin/ipython', 'notebook', '--ProfileDir.location=' + profile_path])
                        db.execute('INSERT INTO sessions (user_id, port, pid, updated) VALUES (%s, %s, %s, %s)', (user_id, port, iprocess.pid, int(time.time())))
            except MySQLdb.Error as err:
                logging.error(err)
            finally:
                if conn:
                    conn.close()

            if port:
                self.redirect(':' + str(port))
            else:
                self.write('Error: session could not be created for user.')
        else:
            self.render('index.html', username=username)

    def create_user(self, username):
        """ Create file structure for user """
        user_path = 'users/' + username
        ip_path = user_path + '/.ipython'
        notebook_path = user_path + '/notebooks'
        profile_path = ip_path + '/profile_nbserver/'

        if not os.path.exists(profile_path):
            logging.info('creating directories for ' + username)
            
            os.makedirs(profile_path)

            shutil.copytree('default_notebooks', notebook_path)

    def write_config(self, username, port):
        """ Write a configuration file """
        user_path = 'users/' + username
        ip_path = user_path + '/.ipython'
        profile_path = ip_path + '/profile_nbserver/'
        
        # get local IP address
        hostname = urlparse('%s://%s' % (self.request.protocol, self.request.host)).hostname
        ip_address = socket.gethostbyname(hostname)

        # write configuration file
        conf_file = open(profile_path + 'ipython_notebook_config.py', 'w')

        conf_file.write('c = get_config()')
        conf_file.write('\nc.NotebookApp.ip = "' + ip_address + '"')
        conf_file.write('\nc.NotebookApp.port = ' + str(port))
        conf_file.write('\nc.NotebookApp.port_retries = 0')
        conf_file.write('\nc.NotebookApp.enable_mathjax = True')
        conf_file.write('\nc.NotebookApp.open_browser = False')
        conf_file.write('\nc.NotebookApp.ipython_dir = u"' + ip_path + '"')
        conf_file.write('\nc.IPKernelApp.pylab = "inline"')
        conf_file.write('\nc.NotebookManager.notebook_dir = u"' + user_path + '/notebooks"')
        conf_file.close()

        return profile_path

    def process_exists(self, pid):
        """ Check if a process is running """
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

app = tornado.web.Application([
    (r'/', MainHandler),
])

if __name__ == '__main__':
    logging.basicConfig(filename='ipy.log', level=logging.INFO)
    logging.info('Starting ipy server')
    
    app.listen(80)
    tornado.ioloop.IOLoop.instance().start()
