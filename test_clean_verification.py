#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test file to verify siren-clean works correctly"""

import builtins

# This is a test setup - siren is assigned to builtins
builtins.siren = siren

def test_function():
    """This function should NOT be removed"""
    x = 10
    return x

def another_test():
    """Another function"""
    y = 20
    print("Test complete")
    return y

# This variable assignment should NOT be removed
siren_backup = siren

# But this call SHOULD be removed

print("Script complete")
