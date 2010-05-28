#!/usr/bin/python

import os, shutil
from subprocess import Popen, PIPE

import string
from distutils import dir_util
import pwd

ID_LOWER_LIMIT = 10000

class WrongUIDException(Exception):
    pass


class UserActions(object):
    def __init__(self, uid, gid=None, umask=027, dry=False):
        self.uid = uid
        self.gid = gid if gid else uid
        self.umask = umask
        self.set_ids()
        self.set_umask()

        self.uname = pwd.getpwuid(self.uid)[0]

        self.dry = dry

    def set_ids(self):
        if self.uid >= ID_LOWER_LIMIT and self.gid >= ID_LOWER_LIMIT:
            os.setgid(self.uid)
            os.setuid(self.uid)
        else:
            raise WrongUIDException("UID or GID %s:%s < %s." % (self.uid, self.gid, ID_LOWER_LIMIT))

    def set_umask(self):
        os.umask(self.umask)

    def pre(self):
        return True

    def post(self):
        #print 'self.post not overriden'
        return False

    def critical(func):
        def new_func(self, *args, **kwargs):
            if self.dry:
                print 'Called %s as %s with:' % (func.func_name,self.uname)
                print '  args:', args
                print 'kwargs:', kwargs
            else:   
                if os.getgid() == self.gid and os.getuid() == self.uid:
                    if self.pre():
                        temp = func(self, *args, **kwargs)
                        self.post()
                        return temp
                else:
                    raise WrongUIDException("Current UID:GID %s:%s does not match required UID:GID %s:%s." % (os.getuid(), os.getgid(), self.uid, self.gid))
        return new_func

    @critical
    def mv(self, src, dst):
        os.rename(src, dst)

    @critical
    def mkdir(self, dir):
        os.makedirs(dir)

    @critical
    def cd(self, dir):
        os.chdir(dir)

    @critical
    def chmod(self, fname, chmod):
        os.chmod(fname, chmod)

    @critical
    def cp(self, src, dst):
        shutil.copyfile(src, dst)

    @critical
    def cp_tree(self, src, dst, symlinks=False):
        #temp, shutil.copy2 = shutil.copy2, shutil.copyfile
        #shutil.copytree(src, dst)
        #shutil.copy2 = temp
        dir_util.copy_tree(src, dst, preserve_mode=False, preserve_times=False, preserve_symlinks=symlinks)

    @critical
    def rm(self, fname):
        os.remove(fname)

    @critical
    def rm_tree(self, dname):
        shutil.rmtree(dname)

    @critical
    def run(self, cmd, shell_bin='/bin/bash'):
        #return subprocess.Popen([exe]+args, executable=shell_bin, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return os.system('umask %s && %s' % ('027', cmd))

    @critical
    def run2(self, cmd, input=''):
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        return proc.communicate(input)

    @critical
    def fill(self, fname, delimiter='%', **kwargs):
        f = file(fname, 'r')
        tstr = f.read()
        f.close()
        Template = type('Template', (string.Template,), {'delimiter':delimiter})
        tmpl = Template(tstr)
        f = file(fname, 'w')
        f.write(tmpl.substitute(**kwargs))
        f.close()

