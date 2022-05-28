'''
Created on May 28, 2022

@author: mballance
'''

class CppGenNS(object):
    
    @staticmethod
    def enter(namespace, out):
        if namespace is not None and namespace != "":
            ns_elems = namespace.split("::")
            for e in ns_elems:
                out.println("namespace %s {" % e)
            out.println()
            
    @staticmethod
    def leave(namespace, out):
        if namespace is not None and namespace != "":
            out.println()
            
            ns_elems = namespace.split("::")
            for e in ns_elems:
                out.println("} // namespace %s" % e)
            out.println()
            
    @staticmethod
    def incpath(namespace, file):
        if namespace is None or namespace == "":
            return file
        else:
            elems = namespace.split("::")
            return "/".join(elems) + "/" + file
        
            