'''
Created on Sep 12, 2020

@author: ballance
'''

from _io import StringIO

class OutStream(object):
    
    def __init__(self):
        self.ind = ""
        self.out = StringIO()
        
    def println(self, s=""):
        self.out.write(self.ind + s + "\n")
        
    def write(self, s):
        self.out.write(s)
        
    def content(self):
        return self.out.getvalue()
    
    def inc_indent(self):
        self.ind += "    ";
        
    def dec_indent(self):
        if len(self.ind) > 4:
            self.ind = self.ind[4:]
        else:
            self.ind = ""

    