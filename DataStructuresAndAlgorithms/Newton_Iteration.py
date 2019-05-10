#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Simon Liu"

"""
Newton iteration:
0. for a given positive real number x and the allowable error e, let the variable y take any positive real number, such as  y = x;
1. If y*y is close enough to x, ie |y×y-x|<e, the calculation ends and y is output as the result;
2. Otherwise, take z=(y + x/y)/2;
3. Let z be the new value of y and return to step 1.
"""
import math


def newton_iteration(x, e):
    org = x
    y = x
    while abs(y*y - org) > e:
        y = (y + x/y)/2
    return y


if __name__ == '__main__':
    x = float(raw_input('Please input a positive real number: '))
    e = float(raw_input('Please input the allowable error-e: '))
    print newton_iteration(x, e)
    print math.sqrt(x)



