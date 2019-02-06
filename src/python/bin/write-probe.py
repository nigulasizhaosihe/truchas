#!/usr/bin/env python3

#===============================================================================
#
#  Copyright (c) Los Alamos National Security, LLC.  This file is part of the
#  Truchas code (LA-CC-15-097) and is subject to the revised BSD license terms
#  in the LICENSE file found in the top-level directory of this distribution.
#
#===============================================================================

import argparse

import truchas

def print_probe_data(truchas_data, probe):
    pv = truchas_data.probe_view(probe)

    xyz = "[{:.6E}, {:.6E}, {:.6E}]"

    print("# probe name: " + pv.attrs["NAME"].decode())
    print("# probe description: " + pv.attrs["DESCRIPTION"].decode())
    print("# probe location: ", xyz.format(pv.attrs["X"],
                                           pv.attrs["Y"],
                                           pv.attrs["Z"]))

    print("# nearest cell index: ", pv.attrs["CELL_INDEX"])
    print("# nearest cell location: ", xyz.format(pv.attrs["CELL_X"],
                                                  pv.attrs["CELL_Y"],
                                                  pv.attrs["CELL_Z"]))

    print("# nearest node index: ", pv.attrs["NODE_INDEX"])
    print("# nearest node location: ", xyz.format(pv.attrs["NODE_X"],
                                                  pv.attrs["NODE_Y"],
                                                  pv.attrs["NODE_Z"]))

    print("# time, value(s)")
    probe_data = pv[:]
    for x in probe_data:
        print("{:.6E}\t{:.6E}".format(x[1], x[2]))


def print_probes(truchas_data, probes):
    print("Index   Probe name")
    print("-"*30)
    for i, probe in zip(range(len(probes)), probes):
        variable = probe[5:]
        name = truchas_data.probe_view(probe).attrs["NAME"].decode()
        print("{:3d}\t{:s}: {:s}".format(i+1, name, variable))


def parse_argv():
    parser = argparse.ArgumentParser(
        description="Writes probe data from a Truchas h5 output file to stdout.")
    parser.add_argument("-l", action="store_true",
                        help="Print a list of the available probes.")
    parser.add_argument("-n", type=int,
                        help="Data for probe index N is written to stdout.")
    parser.add_argument("h5file", help="Input H5 file.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_argv()
    truchas_data = truchas.TruchasData(args.h5file)
    probes = truchas_data.probes()

    if args.l:
        print_probes(truchas_data, probes)
    else:
        assert args.n > 0 and args.n <= len(probes)
        print_probe_data(truchas_data, probes[args.n-1])
