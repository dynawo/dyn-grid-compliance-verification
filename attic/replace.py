#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os

if __name__ == "__main__":
    for i in os.listdir():
        if i == "__init__.py" or i == "replace.py":
            continue
        for j in os.listdir(i):
            if j == "__init__.py":
                continue
            for k in os.listdir(i + "/" + j):
                if k == "__init__.py":
                    continue
                else:
                    with open(i + "/" + j + "/" + k, "r") as file:
                        filedata = file.read()

                    filedata = filedata.replace("&", "$")

                    with open(i + "/" + j + "/" + k, "w") as file:
                        file.write(filedata)

                    os.rename(i + "/" + j + "/" + k, (i + "/" + j + "/" + k).replace("&", "$"))
