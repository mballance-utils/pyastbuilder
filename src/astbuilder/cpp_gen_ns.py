'''
Created on May 28, 2022

@author: mballance
'''
import os


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
        
    @staticmethod
    def incdir(outdir, namespace, create=True):
        if namespace is None or namespace == "":
            ret = os.path.join(outdir, "include")
        else:
            elems = namespace.split("::")
            print("elems: %s" % str(elems))
            ret = os.path.join(outdir, "include", "/".join(elems))
            
        if create and not os.path.isdir(ret):
            os.makedirs(ret)
        
        return ret
        
            