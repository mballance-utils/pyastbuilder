'''
Created on Sep 12, 2020

@author: ballance
'''

from _io import StringIO

class OutStream(object):
    
    def __init__(self):
        self.ind = ""
        self.out = StringIO()
        
    def print(self, s=""):
        self.out.write(self.ind + s)

    def println(self, s=""):
        self.out.write(self.ind + s + "\n")
        
    def write(self, s):
        self.out.write(s)
        
    def content(self):
        return self.out.getvalue()
    
    def inc_indent(self, amt=1):
        for _ in range(amt):
            self.ind += "    ";
        
    def dec_indent(self, amt=1):
        if len(self.ind) > amt*4:
            self.ind = self.ind[amt*4:]
        else:
            self.ind = ""

    