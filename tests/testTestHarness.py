"""
Created on Nov 11, 2020

@author: joseph-hellerstein
"""

from SBstoat._testHarness import TestHarness
from SBstoat._logger import Logger

import os
import unittest


IGNORE_TEST = True
IS_PLOT = True
DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(DIR, "BIOMD0000000339.xml")
VARIABLE_NAMES = ["Va_Xa", "IIa_Tmod", "VIIa_TF"]
PARAMETER_NAMES = ["r27_c", "r28_c", "r29_c"]
VARIABLE_NAMES = ["Pk", "VK"]
PARAMETER_NAMES = ["d_Pk", "d_VK"]
BIOMD_URL_PAT = "http://www.ebi.ac.uk/biomodels/model/download/BIOMD0000000%s?filename=BIOMD0000000%s_url.xml"
URL_603 = BIOMD_URL_PAT % ("603", "603")

class TestFunctions(unittest.TestCase):

    def setUp(self):
        if IGNORE_TEST:
            return
        self.harness = TestHarness(INPUT_PATH, PARAMETER_NAMES, VARIABLE_NAMES)

    def testConstructor(self):
        if IGNORE_TEST:
            return
        self.assertEqual(len(self.harness.parameterValueDct), len(PARAMETER_NAMES))

    def testConstructorInvalid(self):
        if IGNORE_TEST:
            return
        with self.assertRaises(ValueError):
            self.harness = TestHarness("dummy", VARIABLE_NAMES, PARAMETER_NAMES)

    def testEvaluate(self):
        # TESTING
        logger = Logger(isReport=False)
        harness = TestHarness(URL_603, logger=logger)
        harness.evaluate(stdResiduals=0)
        import pdb; pdb.set_trace()
       


if __name__ == '__main__':
    unittest.main()