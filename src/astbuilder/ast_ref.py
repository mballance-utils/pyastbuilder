'''
Created on Sep 13, 2020

@author: ballance
'''

class AstRef(object):
    
    def __init__(self, target):
        self.target = target
        self.circular = False
        