"""
Manages logging.
Messages are structured as follows:
    activity: some kind of significant processing
    result: outcome of the major processing
    status: status of an activity: start, finish
    exception: an exception occurred
    error: a processing error occurred

Time logging is provided as well.
    blockGuid = logger.startBlock("My block")
    ... lots of code ...
    logger.endBlock(blockGuid)
    ... more code ...
    logger.report(csvFile) # writes the results to a csv file
"""

from SBstoat import _helpers

import collections
import pandas as pd
import numpy as np
import sys
import time

LEVEL_ACTIVITY = 1
LEVEL_RESULT = 2
LEVEL_STATUS = 3
LEVEL_EXCEPTION = 4
LEVEL_ERROR = 5
LEVEL_MAX = LEVEL_ERROR
# Dataframe columns
COUNT = "count"
MEAN = "mean"
TOTAL = "total"
# Attributes used in equals comparisons
STATISTIC_ATTR_MERGE = ["count", "total"]
STATISTIC_ATTR_EQUALS = list(STATISTIC_ATTR_MERGE)
STATISTIC_ATTR_EQUALS.append("mean")
LOGGER_ATTR = ["isReport", "toFile", "startTime", "logLevel", "unpairedBlocks",
      "blockDct", "performanceDF", "statisticDct"]


class BlockSpecification(object):
    # Describes an entry for timing a block of code
    guid = 0
    
    def __init__(self, block):
        self.guid = BlockSpecification.guid
        BlockSpecification.guid += 1
        self.startTime = time.time()
        self.block = block
        self.duration = None  # Time duration of the block

    def setDuration(self):
        self.duration = time.time() - self.startTime

    def __repr__(self):
        repr = "guid: %d, block: %s, startTime: %f"  \
              % (self.guid, self.block, self.startTime)
        if self.duration is not None:
            repr += ", duration: %f" % self.duration
        return repr


class Statistic(object):
    # Statistics for a block
    def __init__(self, block=None):
        self.block = block
        self.count = 0
        self.total = 0.0
        self.mean = None

    def __repr__(self):
        repr = "Statistic[block: %s, count: %d, total: %f"  \
              % (self.block, self.count, self.total)
        if self.mean is not None:
            repr += "mean: %f"  % self.mean
        repr += "]"
        return repr
    
    def copy(self):
        return _helpers.copyObject(self)

    def update(self, value):
        self.count += 1
        self.total += value

    def equals(self, other):
        true = True
        for attr in STATISTIC_ATTR_EQUALS:
            result = self.__getattribute__(attr) == other.__getattribute__(attr)
            if not isinstance(result, bool):
                result = all(result)
            true = true and result
        return true

    def merge(self, other):
        newStatistic = self.copy()
        for attr in STATISTIC_ATTR_MERGE:
            value = self.__getattribute__(attr) + other.__getattribute__(attr)
            newStatistic.__setattr__(attr, value)
        return newStatistic

    def summarize(self):
        if self.count == 0:
            self.mean = 0.0
        else:
            self.mean = self.total/self.count


class Logger(object):


    def __init__(self, isReport=True, toFile=None, logLevel=LEVEL_STATUS):
        self.isReport = isReport
        self.toFile = toFile
        self.startTime = time.time()
        self.logLevel = logLevel
        self.unpairedBlocks = 0  # Count of blocks begun without an end
        self.blockDct = {}  # key: guid, value: BlockSpecification. Must be lock protected.
        self._performanceDF = None  # Summarizes performance report
        self.statisticDct = {}

    def copy(self):
        return _helpers.copyObject(self)

    def equals(self, other):
        true = True
        for attr in LOGGER_ATTR:
            result = self.__getattribute__(attr) == other.__getattribute__(attr)
            if not isinstance(result, bool):
                result = all(result)
            true = true and result
        return true

    @property
    def performanceDF(self):
        """
        Summarizes the performance data collected.
        
        Returns
        -------
        pd.Series
            index: block name
            Columns: COUNT, MEAN
        """
        if self._performanceDF is None:
            # Accumulate the durations
            dataDct = {}
            self.unpairedBlocks = len(self.blockDct)
            #
            indices = list(self.statisticDct.keys())
            [s.summarize() for s in self.statisticDct.values()]
            means = [self.statisticDct[b].mean for b in indices]
            counts = [self.statisticDct[b].count for b in indices]
            totals = [self.statisticDct[b].total for b in indices]
            self._performanceDF = pd.DataFrame({
                  COUNT: counts,
                  MEAN: means,
                  TOTAL: totals,
                  })
            self._performanceDF.index = indices
            self._performanceDF = self.performanceDF.sort_index()
        return self._performanceDF

    def getFileDescriptor(self):
        if self.toFile is not None:
            return open(self.toFile, "a")
        else:
            return None

    @staticmethod
    def join(*args):
        """
        Joins together a list of block names.
 
        Parameters
        ----------
        *args: list-str
        
        Returns
        -------
        str
        """
        return "/".join(args)

    def _write(self, msg, numNL):
        relTime = time.time() - self.startTime
        newLineStr = ('').join(["\n" for _ in range(numNL)])
        newMsg = "\n%s%f: %s" % (newLineStr, relTime, msg)
        if self.toFile is None:
            print(newMsg)
        else:
            with open(self.toFile, "a") as fd:
                fd.write(newMsg)

    def activity(self, msg, preString=""):
       # Major processing activity
       if self.isReport and (self.logLevel >= LEVEL_ACTIVITY):
           self._write("***%s***" %msg, 2)
    
    def result(self, msg, preString=""):
       # Result of an activity
       if self.isReport and (self.logLevel >= LEVEL_RESULT):
           self._write("\n **%s" %msg, 1)
    
    def status(self, msg, preString=""):
       # Progress message
       if self.isReport and (self.logLevel >= LEVEL_STATUS):
           self._write("    (%s)" %msg, 0)
    
    def exception(self, msg, preString=""):
       # Progress message
       if self.isReport and (self.logLevel >= LEVEL_EXCEPTION):
           self._write("    (%s)" %msg, 0)
    
    def error(self, msg, excp):
       # Progress message
       if self.isReport and (self.logLevel >= LEVEL_ERROR):
           fullMsg = "%s: %s" % (msg, str(excp))
           self._write("    (%s)" % fullMsg, 0)

    ###### BLOCK TIMINGS ######
    def startBlock(self, block:str)->float:
        """
        Records the beginning of a block.

        Parameters
        ----------
        block: name of the block
        
        Returns
        -------
        int: identifier for the BlockSpecification
        """
        spec = BlockSpecification(block)
        self.blockDct[spec.guid] = spec
        return spec.guid

    def _merge(self, other):
        """
        Merges the results of another logger.
        """
        newLogger = self.copy()
        for block, statistic in self.statisticDct.items():
            otherStatistic = other.statisticDct[block]
            newLogger.statisticDct[block] = statistic.merge(otherStatistic)
        return newLogger

    @staticmethod
    def merge(others):
        curLogger = others[0]
        for other in others[1:]:
            newLogger = curLogger._merge(other)
            curLogger = newLogger
        return newLogger
        

    def endBlock(self, guid:int):
        """
        Records the end of a block. Items are removed as
        statistics are accumulated.

        Parameters
        ----------
        guid: identifies the block instance
        """
        if not guid in self.blockDct.keys():
            self.exception("missing guid: %d" % guid)
        else:
            spec = self.blockDct[guid]
            spec.setDuration()
            if not spec.block in self.statisticDct.keys():
                self.statisticDct[spec.block] = Statistic(block=spec.block)
            self.statisticDct[spec.block].update(spec.duration)
            del self.blockDct[spec.guid]
