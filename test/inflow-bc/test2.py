#!/usr/bin/env python

import sys
import os

import numpy

import Truchas
import TruchasTest

class mytest(TruchasTest.GoldenTestCase):

  test_name = 'inflow-bc-2'
  num_procs = 4 # with a parallel executable

  # Override the default setUp, omitting the opening of the golden output
  def setUp(self):
    if self._is_initialized is False:
      self.setUpClass() # This runs Truchas
    self.test_output = Truchas.TruchasOutput(self.get_output_file())

  def test_fields(self):
    success = True

    # Final time
    success &= self.vof_test(2, 1e-15)
    success &= self.pressure_test(2, 1e-15)
    success &= self.velocity_test(2, 1e-15)
    success &= self.temperature_test(2, 1e-15)

    self.assertTrue(success)

  def vof_test(self, id, tol):

    # The centroids function does not serialize, so we don't want to here either.
    time = self.test_output.get_simulation().find_series(id).time
    test = self.test_output.get_simulation().find_series(id).get_data('VOF',serialize=False)

    # Analytic vof solution at cell centroids
    cc = self.test_output.get_mesh().centroids()
    p = 0.25*time - 0.375
    vof = numpy.empty_like(test[:,0])
    for j in range(vof.size):
      x = cc[j,0]
      if x+0.125 < p:
        vof[j] = 1
      elif x-0.125 > p:
        vof[j] = 0
      else:
        vof[j] = 4*(p-(x-0.125))

    error = numpy.amax(abs(test[:,0]-vof))
    return self.report('vof', time, error, tol)

  def pressure_test(self, id, tol):
    time = self.test_output.get_simulation().find_series(id).time
    test = self.test_output.get_simulation().find_series(id).get_data('Z_P')
    error = numpy.amax(abs(test))
    return self.report('pressure', time, error, tol)

  def velocity_test(self, id, tol):
    time = self.test_output.get_simulation().find_series(id).time
    test = self.test_output.get_simulation().find_series(id).get_data('Z_VC')
    vof = self.test_output.get_simulation().find_series(id).get_data('VOF')[:,0]

    # the x-velocity is 0.25 in cells containing fluid
    uerror = max(abs(u - 0.25) if vf > 0.0 else abs(u) for u,vf in zip(test[:,0],vof))
    verror = max(abs(test[:,1]))
    werror = max(abs(test[:,2]))

    success = self.report('x-velocity', time, uerror, tol)
    success &= self.report('y-velocity', time, verror, tol)
    success &= self.report('z-velocity', time, werror, tol)
    return success

  def temperature_test(self, id, tol):
    time = self.test_output.get_simulation().find_series(id).time
    test = self.test_output.get_simulation().find_series(id).get_data('Z_TEMP')
    vof = self.test_output.get_simulation().find_series(id).get_data('VOF')[:,0]

    # the temperature is 2 in cells containing fluid
    error = max(abs(u - 2.0) if vf > 0.0 else abs(u) for u,vf in zip(test,vof))

    success = self.report('temperature', time, error, tol)
    return success

  def report(self, var, time, error, tol):
    success = error <= tol
    status = 'PASS' if success else 'FAIL'
    print '%s: %s at t=%8.2e: max error=%8.2e (tol=%8.2e)'%(status,var,time,error,tol)
    return success

if __name__ == '__main__':
  import unittest
  unittest.main()