'''
Created on Mar 26, 2021

@author: mballance
'''
import os


def find_yaml_files(path):
    ret = []
    if not os.path.isdir(path):
        raise Exception("Directory " + path + " doesn't exist")
    for f in os.listdir(path):
        print("File: " + f)
        if os.path.splitext(f)[1] == ".yaml":
            ret.append(os.path.join(path, f))
            print("Found file " + f)
    return ret
