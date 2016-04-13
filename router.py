###########################################################################
#
# Copyright 2015-2016 Robert B. Lowrie (http://github.com/lowrie)
#
# This file is part of pyRouterJig.
#
# pyRouterJig is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pyRouterJig is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# pyRouterJig; see the file LICENSE. If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################

'''
Contains the router, board, template and their geometry properties.
'''
from __future__ import division
from __future__ import print_function
from future.utils import lrange

import math
import utils

class Router_Exception(Exception):
    '''
    Exception handler for all routerJig
    '''
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg
    def __str__(self):
        return self.msg

class Incra_Template(object):
    '''
    Contains properties of an incra template

    Attributes:

    height: Dimension in y-coordinate
    margin: Dimension in x-coordinate placed on each end of template
    length: total length of template
    '''
    def __init__(self, units, boards, margin=None, length=None):
        # incra uses 1/2" high templates
        self.height = units.inches_to_increments(0.5)
        if margin is None:
            self.margin = units.inches_to_increments(1.0)
        else:
            self.margin = margin
        if length is None:
            self.length = boards[0].width + 2 * self.margin
        else:
            self.length = length

class Router_Bit(object):
    '''
    Stores properties of dovetail and straight router bits.

    Input attributes (after creation, use setter functions to set these)

    angle: measured from y-axis, in degrees, following dovetail bit
           standard. Zero for straight bit.

    width: max cutting width.  This is the bottom of a dovetail bit.
           For now, this must be an even number.

    depth: cutting depth. Equals board thickness for through dovetails
            and box joints.

    Computed attributes:

    offset: x-dimension between max-width point and point at board's
            surface.  Zero for angle=0.

    neck: width of bit at board surface.

    halfwidth: half of width
    '''
    def __init__(self, units, width, depth, angle=0):
        self.units = units
        self.width = width
        self.depth = depth
        self.angle = angle
        self.reinit()
    def set_width_from_string(self, s):
        '''
        Sets the width from the string s, following requirements from units.string_to_increments().
        '''
        if self.units.metric:
            val = '6'
        else:
            val = '1/2'
        msg = 'Unable to set Bit Width to: {}<p>'\
              'Set to a positive value, such as: {}'.format(s, val)
        try:
            width = self.units.string_to_increments(s)
        except:
            raise Router_Exception(msg)
        if width <= 0:
            raise Router_Exception(msg)
        halfwidth = width // 2
        if 2 * halfwidth != width:
            msg += '<p>Bit Width must be an even number of increments.<p>'\
                   'The increment size is: {}<p>'\
                   ''.format(self.units.increments_to_string(1, True))
            raise Router_Exception(msg)
        self.width = width
        self.halfwidth = halfwidth
        self.reinit()
    def set_depth_from_string(self, s):
        '''
        Sets the depth from the string s, following requirements from units.string_to_increments().
        '''
        if self.units.metric:
            val = '5'
        else:
            val = '3/4'
        msg = 'Unable to set Bit Depth to: {}<p>'\
              'Set to a positive value, such as: {}'.format(s, val)
        try:
            depth = self.units.string_to_increments(s)
        except:
            raise Router_Exception(msg)
        if depth <= 0:
            raise Router_Exception(msg)
        self.depth = depth
        self.reinit()
    def set_angle_from_string(self, s):
        '''
        Sets the angle from the string s, where s represents a floating point number or fractional number.
        '''
        msg = 'Unable to set Bit Angle to: {}<p>'\
              'Set to zero or a positive value, such as 7.5 or "7 1/2"'.format(s)
        try:
            angle = self.units.string_to_float(s)
        except:
            raise Router_Exception(msg)
        if angle < 0:
            raise Router_Exception(msg)
        self.angle = angle
        self.reinit()
    def reinit(self):
        '''
        Reinitializes internal attributes that are dependent on width
        and angle.
        '''
        self.halfwidth = self.width // 2
        self.offset = 0 # ensure exactly 0 for angle == 0
        if self.angle > 0:
            self.offset = self.depth * math.tan(self.angle * math.pi / 180)
        self.neck = self.width - 2 * self.offset
    def dovetail_correction(self):
        '''
        Correction for rounding the offset
        '''
        if utils.my_round(self.neck) + 2 * utils.my_round(self.offset) < self.width:
            return 1
        else:
            return 0

class My_Rectangle(object):
    '''
    Stores a rectangle geometry
    '''
    def __init__(self, xOrg, yOrg, width, height):
        '''
        (xOrg, yOrg): Bottom-left coordinate (origin)
        width: Extent in s
        height: Extent in y
        '''
        self.set_origin(xOrg, yOrg)
        self.width = width
        self.height = height
    def xMid(self):
        '''Returns the x-coordinate of the midpoint.'''
        return self.xOrg + self.width // 2
    def yMid(self):
        '''Returns the y-coordinate of the midpoint.'''
        return self.yOrg + self.height // 2
    def xL(self):
        '''Returns the left (min) x-coordindate'''
        return self.xOrg
    def xR(self):
        '''Returns the right (max) x-coordindate'''
        return self.xOrg + self.width
    def yB(self):
        '''Returns the bottom (min) y-coordindate'''
        return self.yOrg
    def yT(self):
        '''Returns the top (max) y-coordindate'''
        return self.yOrg + self.height
    def set_origin(self, xOrg, yOrg):
        '''Sets the origin to xs, ys'''
        self.xOrg = xOrg
        self.yOrg = yOrg

class Board(My_Rectangle):
    '''
    Board of wood description.

    Attributes:
    units: Units object
    width: Dimension of routed edge (along x-axis)
    height: Dimension perpendicular to routed edge (along y-axis)
    thickness: Dimension into paper or screen (not used yet)
    wood: Wood image used for fill
    active: If true, this board is active

    Dimensions are in increment units.
    '''
    def __init__(self, bit, width, thickness=32):
        My_Rectangle.__init__(self, 0, 0, width, 32)
        self.units = bit.units
        self.thickness = thickness
        self.wood = None
        self.active = True
        self.dheight = 0
        self.set_height(bit)
        self.bottom_cuts = None
        self.top_cuts = None
    def set_wood(self, wood):
        '''Sets attribute wood'''
        self.wood = wood
    def set_active(self, active=True):
        '''Sets attribute active'''
        self.active = active
    def set_width_from_string(self, s):
        '''
        Sets the width from the string s, following requirements from units.string_to_increments().
        '''
        if self.units.metric:
            val = '52'
        else:
            val = '7 1/2'
        msg = 'Unable to set Board Width to: {}<p>'\
              'Set to a postive value, such as: {}'.format(s, val)
        try:
            width = self.units.string_to_increments(s)
        except:
            raise Router_Exception(msg)
        if width <= 0:
            raise Router_Exception(msg)
        self.width = width
    def set_height(self, bit, dheight=None):
        '''
        Sets the height from the router bit depth of cut
        '''
        if dheight is None:
            if self.dheight > 0:
                h = self.dheight
            else:
                h = utils.my_round(0.5 * bit.depth)
        else:
            self.dheight = dheight
            h = dheight
        self.height = bit.depth + h
    def set_height_from_string(self, bit, s):
        '''
        Sets the height from the string s, following requirements from units.string_to_increments().
        This sets the attribute dheight, which is the increment above the bit depth.
        '''
        # TODO: This is called "thickness" because we set this only for
        # double* boards, for which we call this the thickness.
        if self.units.metric:
            val = '4'
        else:
            val = '1/8'
        msg = 'Unable to set board Thickness to: {}<p>'\
              'Set to a postive value, such as: {}'.format(s, val)
        try:
            t = self.units.string_to_increments(s)
        except:
            raise Router_Exception(msg)
        if t <= 0:
            raise Router_Exception(msg)
        self.set_height(bit, t)
    def set_bottom_cuts(self, cuts, bit):
        '''Sets the bottom cuts for the board'''
        for c in cuts:
            c.make_router_passes(bit, self)
        self.bottom_cuts = cuts
    def set_top_cuts(self, cuts, bit):
        '''Sets the top cuts for the board'''
        for c in cuts:
            c.make_router_passes(bit, self)
        self.top_cuts = cuts
    def _do_cuts(self, bit, cuts, y_nocut, y_cut):
        '''Creates the perimeter coordinates for the given cuts'''
        x = []
        y = []
        if cuts[0].xmin > 0:
            x = [self.xL()]
            y = [y_nocut]
        # loop through the cuts and add them to the perimeter
        for c in cuts:
            if c.xmin > 0:
                # on the surface, start of cut
                x.append(c.xmin + x[0] + bit.offset)
                y.append(y_nocut)
            # at the cut depth, start of cut
            x.append(c.xmin + self.xL())
            y.append(y_cut)
            # at the cut depth, end of cut
            x.append(c.xmax + self.xL())
            y.append(y_cut)
            if c.xmax < self.width:
                # at the surface, end of cut
                x.append(c.xmax + self.xL() - bit.offset)
                y.append(y_nocut)
        # add the last point on the top and bottom, at the right edge,
        # accounting for whether the last cut includes this edge or not.
        if cuts[-1].xmax < self.width:
            x.append(self.xL() + self.width)
            y.append(y_nocut)
        return (x, y)
    def do_all_cuts(self, bit):
        '''
        Returns (xtop, ytop, xbottom, ybottom), which are the coordinates of the top and 
        bottom cuts, ordered left to right.  If the edge has no cuts, just the endpoints
        of the board are returned.
        '''
        # Do the top edge
        y_nocut = self.yT() # y-location of uncut edge
        if self.top_cuts is None:
            xtop = [self.xL(), self.xR()]
            ytop = [y_nocut, y_nocut]
        else:
            y_cut = y_nocut - bit.depth   # y-location of routed edge
            (xtop, ytop) = self._do_cuts(bit, self.top_cuts, y_nocut, y_cut)
        # Do the bottom edge
        y_nocut = self.yB() # y-location of uncut edge
        if self.bottom_cuts is None:
            xb = [self.xL(), self.xR()]
            yb = [y_nocut, y_nocut]
        else:
            y_cut = y_nocut + bit.depth   # y-location of routed edge
            (xb, yb) = self._do_cuts(bit, self.bottom_cuts, y_nocut, y_cut)
        return (xtop, ytop, xb, yb)
    def perimeter(self, bit):
        '''
        Compute the perimeter coordinates of the board.

        bit: A Router_Bit object.

        Returns (x, y) coordinates of perimeter, ordred clockwise around
        perimeter.
        '''
        (x, y, xb, yb) = self.do_all_cuts(bit)
        # merge the top and bottom
        xb.reverse()
        yb.reverse()
        x.extend(xb)
        y.extend(yb)
        # close the polygon by adding the first point
        x.append(x[0])
        y.append(y[0])
        return (x, y)
    def triangulate(self, bit):
        '''
        Compute the triangulation of the board.

        bit: A Router_Bit object.

        Returns (x, y, t), where

        x, y = lists of vertex coordinates, ordered clockwise around perimeter
        t = list of triangle indices in x, y

        Note that perimeter() returns a smaller list of (x, y), but more
        coordinates are needed to create a good triangulation.
        '''
        t = []
        y_top = self.yT()
        y_bot = self.yB()
        if self.top_cuts is None: # has only bottom cuts
            y_cut = y_bot + bit.depth # y-location of routed edge
            cuts = self.bottom_cuts
            (xc, yc) = self._do_cuts(bit, cuts, y_bot, y_cut)
            nintervals = 2 * len(cuts) - 1
            incut = True
            if cuts[0].xmin > 0:
                nintervals += 1
                incut = False
                xc.insert(0, xc[0])
                yc.insert(0, y_cut)
            if cuts[-1].xmax < self.width:
                nintervals += 1
                xc.append(self.width)
                yc.append(y_cut)
            ntop = nintervals + 1
            ntotal = ntop + len(xc)
            v = [[self.xL(), y_top]] * ntotal
            v[0] = [xc[0], yc[0]]
            v[1] = [xc[1], yc[1]]
            ic = 0
            ibot = 2
            itop = ntotal - 2
            for i in lrange(nintervals):
                v[ibot] = [xc[ibot], yc[ibot]]
                if ibot < len(xc) - 1:
                    v[ibot + 1] = [xc[ibot + 1], yc[ibot + 1]]
                if incut:
                    v[itop] = [cuts[ic].xmax + self.xL(), y_top]
                    ic += 1
                    t.append([ibot - 1, ibot, itop])
                    t.append([ibot - 1, itop, itop + 1])
                else:
                    if ic < len(cuts):
                        v[itop] = [cuts[ic].xmin + self.xL(), y_top]
                    else:
                        v[itop] = [self.xR(), y_top]
                    t.append([ibot - 1, ibot, ibot + 1])
                    t.append([ibot - 1, ibot + 1, ibot - 2])
                    t.append([ibot - 2, ibot + 1, itop])
                    t.append([ibot - 2, itop, itop + 1])
                incut = (not incut)
                ibot += 2
                itop -= 1
        elif self.bottom_cuts is None: # has only top cuts
            y_cut = y_top - bit.depth # y-location of routed edge
            cuts = self.top_cuts
            (xc, yc) = self._do_cuts(bit, cuts, y_top, y_cut)
            nintervals = 2 * len(cuts) - 1
            incut = True
            if cuts[0].xmin > 0:
                nintervals += 1
                incut = False
                xc.insert(0, xc[0])
                yc.insert(0, y_cut)
            if cuts[-1].xmax < self.width:
                nintervals += 1
                xc.append(self.width)
                yc.append(y_cut)
            nbot = nintervals + 1
            ntotal = nbot + len(xc)
            v = [[self.xL(), y_bot]] * ntotal
            v[0] = [xc[0], yc[0]]
            v[1] = [xc[1], yc[1]]
            ic = 0
            ibot = ntotal - 2
            itop = 2
            for i in lrange(nintervals):
                v[itop] = [xc[itop], yc[itop]]
                if itop < len(xc) - 1:
                    v[itop + 1] = [xc[itop + 1], yc[itop + 1]]
                if incut:
                    v[ibot] = [cuts[ic].xmax + self.xL(), y_bot]
                    ic += 1
                    t.append([itop - 1, itop, ibot + 1])
                    t.append([itop, ibot, ibot + 1])
                else:
                    if ic < len(cuts):
                        v[ibot] = [cuts[ic].xmin + self.xL(), y_bot]
                    else:
                        v[ibot] = [self.xR(), y_bot]
                    t.append([itop - 2, itop + 1, itop])
                    t.append([itop - 2, itop, itop - 1])
                    t.append([itop + 1, itop - 2, ibot + 1])
                    t.append([itop + 1, ibot + 1, ibot])
                incut = (not incut)
                itop += 2
                ibot -= 1
        return (v, t)

class Cut(object):
    '''
    Cut description.

    Attributes:

    xmin: min x-location of cut.
    xmax: max x-location of cut.
    passes: Array of router passes to make the cut, indicating the center of the bit
    midPass: The particle pass in passes that is centered (within an increment)
             on the cut
    '''
    def __init__(self, xmin, xmax):
        self.xmin = xmin
        self.xmax = xmax
        self.passes = []
    def validate(self, bit, board):
        '''
        Checks whether the attributes of the cut are valid.
        '''
        if self.xmin >= self.xmax:
            raise Router_Exception('cut xmin = %d, xmax = %d: '\
                                   'Must have xmax > xmin!' % (self.xmin, self.xmax))
        if self.xmin < 0:
            raise Router_Exception('cut xmin = %d, xmax = %d: '\
                                   'Must have xmin >=0!' % (self.xmin, self.xmax))
        if self.xmax > board.width:
            raise Router_Exception('cut xmin = %d, xmax = %d:'
                                   ' Must have xmax < board width (%d)!'\
                                   % (self.xmin, self.xmax, board.width))
        if self.xmax - self.xmin < bit.width and self.xmin > 0 and self.xmax < board.width:
            raise Router_Exception('cut xmin = %d, xmax = %d: '\
                                   'Bit width (%d) too large for this cut!'\
                                   % (self.xmin, self.xmax, bit.width))
    def make_router_passes(self, bit, board):
        '''Computes passes for the given bit.'''
        # The logic below assumes bit.width is even
        if bit.width % 2 != 0:
            Router_Exception('Router-bit width must be even!')
        self.validate(bit, board)
        # set current extents of the uncut region
        xL = self.xmin
        xR = self.xmax
        # alternate between the left and right sides of the overall cut to make the passes
        remainder = xR - xL
        self.passes = []
        while remainder > 0:
            # start with a pass on the right side of cut
            p = xR - bit.halfwidth
            if p - bit.halfwidth >= self.xmin or self.xmin == 0:
                self.passes.append(p)
                xR -= bit.width
            # if anything to cut remains, do a pass on the far left side
            remainder = xR - xL
            if remainder > 0:
                p = xL + bit.halfwidth
                if p + bit.halfwidth <= self.xmax or self.xmax == board.width:
                    self.passes.append(p)
                    xL += bit.width
                    remainder = xR - xL
                    # at this stage, we've done the same number of left and right passes, so if
                    # there's only one more pass needed, center it.
                    if remainder > 0 and remainder <= bit.width:
                        p = (xL + xR) // 2
                        self.passes.append(p)
                        remainder = 0
        # Sort the passes
        self.passes = sorted(self.passes)
        # Error checking:
        for p in self.passes:
            if (self.xmin > 0 and p - bit.halfwidth < self.xmin) or \
               (self.xmax < board.width and p + bit.halfwidth > self.xmax):
                raise Router_Exception('cut xmin = %d, xmax = %d, pass = %d: '\
                                       'Bit width (%d) too large for this cut!'\
                                       % (self.xmin, self.xmax, p, bit.width))

def adjoining_cuts(cuts, bit, board):
    '''
    Given the cuts on an edge, computes the cuts on the adjoining edge.

    cuts: An array of Cut objects
    bit: A Router_Bit object
    board: A Board object

    Returns an array of Cut objects
    '''
    nc = len(cuts)
    adjCuts = []
    # if the left-most input cut does not include the left edge, add an
    # adjoining cut that includes the left edge
    if cuts[0].xmin > 0:
        left = 0
        right = utils.my_round(cuts[0].xmin + bit.offset) - board.dheight
        if right - left >= board.dheight:
            adjCuts.append(Cut(left, right))
    # loop through the input cuts and form an adjoining cut, formed
    # by looking where the previous cut ended and the current cut starts
    for i in lrange(1, nc):
        left = utils.my_round(cuts[i-1].xmax - bit.offset + board.dheight)
        right = max(left + bit.width, utils.my_round(cuts[i].xmin + bit.offset) - board.dheight)
        adjCuts.append(Cut(left, right))
    # if the right-most input cut does not include the right edge, add an
    # adjoining cut that includes this edge
    if cuts[-1].xmax < board.width:
        left = utils.my_round(cuts[-1].xmax - bit.offset) + board.dheight
        right = board.width
        if right - left >= board.dheight:
            adjCuts.append(Cut(left, right))
    return adjCuts

def caul_cuts(cuts, bit, board, trim):
    '''
    Given the cuts on an edge, computes the cuts need to make a caul clamp.

    cuts: An array of Cut objects
    bit: A Router_Bit object
    board: A Board object
    trim: Amount to add to each side of cut (or "trim" from each side of finger)

    Returns an array of Cut objects
    '''
    new_cuts = []
    for c in cuts:
        xmin = max(0, c.xmin - trim)
        xmax = min(board.width, c.xmax + trim)
        cut = Cut(xmin, xmax)
        cut.make_router_passes(bit, board)
        new_cuts.append(cut)
    return new_cuts

def cut_boards(boards, bit, spacing):
    '''
    Determines the cuts for each board for the given bit and spacing
    '''
    # determine all the cuts from the A-cuts (index 0) on the top board.
    last = spacing.cuts
    boards[0].set_bottom_cuts(last, bit)

    if boards[3].active:
        # double-double case
        top = adjoining_cuts(last, bit, boards[0])
        boards[3].set_top_cuts(top, bit)
        last = adjoining_cuts(top, bit, boards[3])
        boards[3].set_bottom_cuts(last, bit)
    if boards[2].active:
        # double and double-double
        top = adjoining_cuts(last, bit, boards[0])
        boards[2].set_top_cuts(top, bit)
        last = adjoining_cuts(top, bit, boards[2])
        boards[2].set_bottom_cuts(last, bit)

    # make the top cuts on the bottom board
    top = adjoining_cuts(last, bit, boards[1])
    boards[1].set_top_cuts(top, bit)

class Joint_Geometry(object):
    '''
    Computes and stores all of the geometry attributes of the joint.
    '''
    def __init__(self, template, boards, bit, spacing, margins, config):
        self.template = template
        self.boards = boards
        self.bit = bit
        self.spacing = spacing
        self.margins = margins

        cut_boards(boards, bit, spacing)
        self.compute_fit()

        board_sep = margins.sep
        if config.show_fit:
            board_sep = -bit.depth

        # Create the corners of the template
        self.rect_T = My_Rectangle(margins.left, margins.bottom,
                                   template.length, template.height)

        # The sub-rectangle in the template of the board's width
        # (no template margins)
        self.board_T = My_Rectangle(self.rect_T.xL() + template.margin, self.rect_T.yB(), \
                                    boards[0].width, template.height)
        x = self.board_T.xL()
        y = self.rect_T.yT() + margins.sep

        # Set bottom board origin
        self.boards[1].set_origin(x, y)
        y = self.boards[1].yT() + board_sep

        # Set double and double-double origins
        if self.boards[2].active:
            self.boards[2].set_origin(x, y)
            y = self.boards[2].yT() + board_sep
            if self.boards[3].active:
                self.boards[3].set_origin(x, y)
                y = self.boards[3].yT() + board_sep

        # Set top board origin
        self.boards[0].set_origin(x, y)
        y = self.boards[0].yT() + margins.sep

        # Template stuff for double-double cases
        if self.boards[3].active:
            self.rect_TDD = My_Rectangle(margins.left, y,
                                         template.length, template.height)
            self.board_TDD = My_Rectangle(self.rect_TDD.xL() + template.margin, y, \
                                          boards[0].width, template.height)
            y = self.board_TDD.yT() + margins.sep
        else:
            self.rect_TDD = None
            self.board_TDD = None

        # Caul template
        if config.show_caul:
            caul_trim = max(1, bit.units.abstract_to_increments(config.caul_trim))
            self.rect_caul = My_Rectangle(margins.left, y,
                                          template.length, template.height)
            self.board_caul = My_Rectangle(self.rect_caul.xL() + template.margin, y, \
                                          boards[0].width, template.height)
            self.caul_top = caul_cuts(self.boards[0].bottom_cuts, bit, boards[0], caul_trim)
            self.caul_bottom = caul_cuts(self.boards[1].top_cuts, bit, boards[1], caul_trim)
        else:
            self.rect_caul = None
            self.board_caul = None
            self.caul_top = None
            self.caul_bottom = None

    def compute_fit(self):
        '''
        Sets the maximum gap and overlap over all joints.
        '''
        # Determine the board indices for each joint.
        if self.boards[2].active:
            joints = [[1, 2]]
            if self.boards[3].active:
                joints.append([2, 3])
                joints.append([3, 0])
            else:
                joints.append([2, 0])
        else:
            joints = [[1, 0]]

        # Load up the coordinates for the boards
        coords = []
        for i in range(4):
            if self.boards[i].active:
                coords.append(self.boards[i].do_all_cuts(self.bit))

        # Determine the max gap and overlap
        self.max_gap = 0
        self.max_overlap = 0
        for j in joints:
            # Here, bottom and top are with respect to the joint, not the
            # boards, so they're flipped. Roughly, should have ybot < ytop.
            xbot = coords[j[0]][0]
            ybot = coords[j[0]][1]
            xtop = coords[j[1]][2]
            ytop = coords[j[1]][3]
            n = len(xtop)
            yshift = self.boards[j[1]].yB() - self.boards[j[0]].yT() +\
                     self.bit.depth
            for i in range(n):
                ybot[i] += yshift
            for i in range(n - 1):
                d = gap_overlap((xbot[i], xbot[i+1]),
                                (ybot[i], ybot[i+1]),
                                (xtop[i], xtop[i+1]),
                                (ytop[i], ytop[i+1]))
                if d > 0:
                    self.max_gap = max(self.max_gap, d)
                else:
                    self.max_overlap = max(self.max_overlap, -d)

def gap_overlap(xbot, ybot, xtop, ytop):
    '''
    Returns the distance between the midpoint of (xbot, ybot) to the 
    line (xtop, ytop).  If positive, then a gap; otherwise, an overlap.
    '''
    # find unit normal from bottom line
    dxbot = xbot[1] - xbot[0]
    dybot = ybot[1] - ybot[0]
    norm = 1.0 / math.sqrt(dxbot * dxbot + dybot * dybot)
    nx = -dybot * norm
    ny = dxbot * norm
    # vector connecting midpoints
    dx = 0.5 * (xtop[1] + xtop[0] - xbot[1] - xbot[0])
    dy = 0.5 * (ytop[1] + ytop[0] - ybot[1] - ybot[0])
    # the dot product is our result
    return dx * nx + dy * ny

def create_title(boards, bit, spacing):
    '''
    Returns a title that describes the joint
    '''
    units = bit.units
    title = spacing.description
    title += '\nBoard width: '
    title += units.increments_to_string(boards[0].width, True)
    if boards[2].active:
        title += '   Double Thickness: '
        title += units.increments_to_string(boards[2].dheight, True)
        if boards[3].active:
            title += ', '
            title += units.increments_to_string(boards[2].dheight, True)
    title += '    Bit: '
    if bit.angle > 0:
        title += '%.1f deg. dovetail' % bit.angle
    else:
        title += 'straight'
    title += ', width: '
    title += units.increments_to_string(bit.width, True)
    title += ', depth: '
    title += units.increments_to_string(bit.depth, True)
    return title
