#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
@author: DerekK88
"""

from __future__ import absolute_import, division, print_function, unicode_literals
import numpy as np
import gdspy
import uuid
import picwriter.toolkit as tk

class GratingCoupler(gdspy.Cell):
    def __init__(self, wgt, port=(0,0), direction='EAST', focus_distance=None,
                    width=20, length=50, taper_length=20, period=1.0, dutycycle=0.5,
                    wavelength=1.55, sin_theta=np.sin(np.pi * 8 / 180),
                    evaluations=99):
        """
        First initiate super properties (gdspy.Cell)
        wgt = WaveguideTemplate reference
        port = tuple (x1, y1) position that determines output port
        direction = direction of the port on the grating coupler
        focus_distance = if None, use straight grating, else focus by this amount
        width = width of the grating region
        length = length of the grating region
        taper_length = length of taper
        period = grating period
        dutycycle = dutycycle, defined by (period-gap)/period

        The parameters below only apply to the focusing grating couplers
        wavelength = free space wavelength
        sin_theta = sine of the incidence angle
        focus_distance = distance
        evaluations = number of parametric evaluations of path.parametric
        """
        gdspy.Cell.__init__(self, "GratingCoupler--"+str(uuid.uuid4()))

        self.portlist = {}

        self.port = port
        self.direction = direction
        self.wgt = wgt
        self.resist = wgt.resist

        self.focus_distance = focus_distance
        self.width = width
        self.length = length
        self.taper_length = taper_length
        self.period = period
        if dutycycle>1.0 or dutycycle<0.0:
            raise ValueError("Warning! Dutycycle *must* specify a valid number "
                             "between 0 and 1.")
        self.dc = dutycycle
        self.wavelength = wavelength
        self.sin_theta = sin_theta
        self.evaluations = evaluations
        self.spec = {'layer': wgt.layer, 'datatype': wgt.datatype}

        self.build_cell()
        self.build_ports()

    def build_cell(self):
        """
        Sequentially build all the geometric shapes using gdspy path functions
        then add it to the Cell
        """
        num_teeth = int(self.length//self.period)
        if self.focus_distance==None:
            """ Create a straight grating GratingCoupler
            """
            if self.resist == '-':
                path = gdspy.Path(self.wgt.wg_width, self.port)
                path.segment(self.taper_length, direction='+y',
                             final_width=self.width, **self.spec)
                teeth = gdspy.L1Path((self.port[0]-0.5*self.width, self.taper_length+self.port[1]+0.5*(num_teeth-1+self.dc)*self.period),
                                    '+x', self.period*self.dc, [self.width], [], num_teeth, self.period, **self.spec)
            elif self.resist == '+':
                path = gdspy.Path(self.wgt.clad_width, self.port, number_of_paths=2,
                                  distance=self.wgt.wg_width + self.wgt.clad_width)
                path.segment(self.taper_length, direction='+y',
                             final_distance=self.width+self.wgt.clad_width, **self.spec)
                path.segment(self.length, direction='+y', **self.spec)
                teeth = gdspy.L1Path((self.port[0]-0.5*self.width, self.taper_length+self.port[1]+0.5*(num_teeth-1+(1.0-self.dc))*self.period),
                                    '+x', self.period*(1.0-self.dc), [self.width], [], num_teeth, self.period, **self.spec)
        else:
            """ Create a lensed grating coupler
            """
            path = gdspy.Path(self.wgt.wg_width, self.port)
            assert self.focus_distance > 0
            neff = self.wavelength / float(self.period) + self.sin_theta
            qmin = int(self.focus_distance / float(self.period) + 0.5)
            teeth = gdspy.Path(self.period * self.dc, self.port)
            max_points = 199
            c3 = neff**2 - self.sin_theta**2
            w = 0.5 * self.width
            for q in range(qmin, qmin + num_teeth):
                c1 = q * self.wavelength * self.sin_theta
                c2 = (q * self.wavelength)**2
                teeth.parametric(lambda t: (self.width * t - w, (c1 + neff
                                * np.sqrt(c2 - c3 * (self.width * t - w)**2)) / c3),
                                number_of_evaluations=self.evaluations,
                                max_points=max_points,
                                **self.spec)
                teeth.x = self.port[0]
                teeth.y = self.port[1]
            teeth.polygons[0] = np.vstack(
                (teeth.polygons[0][:self.evaluations, :],
                 ([(self.port[0] + 0.5 * self.wgt.wg_width, self.port[1]),
                   (self.port[0] - 0.5 * self.wgt.wg_width, self.port[1])])))
            teeth.fracture()

        if self.direction=="WEST":
            teeth.rotate(np.pi/2.0, self.port)
            path.rotate(np.pi/2.0, self.port)
        if self.direction=="SOUTH":
            teeth.rotate(np.pi, self.port)
            path.rotate(np.pi, self.port)
        if self.direction=="EAST":
            teeth.rotate(-np.pi/2.0, self.port)
            path.rotate(-np.pi/2.0, self.port)
        self.add(teeth)
        self.add(path)

    def build_ports(self):
        """ Portlist format:
            example:  {'port':(x_position, y_position), 'direction': 'NORTH'}
        """
        self.portlist["output"] = {'port':self.port, 'direction':tk.flip_direction(self.direction)}

if __name__ == "__main__":
    from picwriter.components.waveguide import Waveguide, WaveguideTemplate
    top = gdspy.Cell("top")
    wgt = WaveguideTemplate(bend_radius=50, resist='-', fab='ETCH')

    wg1=Waveguide([(0,0), (250,0), (250,500), (500,500)], wgt)
    top.add(wg1)

    gc1 = GratingCoupler(wgt, width=20, length=50, taper_length=20, period=1.0, dutycycle=0.7, **wg1.portlist["input"])
    top.add(gc1)

    gc2 = GratingCoupler(wgt, focus_distance=20.0, width=20, length=50, taper_length=20, period=1.0, dutycycle=0.5, **wg1.portlist["output"])
    top.add(gc2)

    gdspy.LayoutViewer()