#!/usr/bin/env python3

#===============================================================================
#
#  Copyright (c) Los Alamos National Security, LLC.  This file is part of the
#  Truchas code (LA-CC-15-097) and is subject to the revised BSD license terms
#  in the LICENSE file found in the top-level directory of this distribution.
#
#===============================================================================

import argparse
import os

import scipy as sp

import fortran_write
import truchas

def write_restart(outfile, truchas_data, series_id, scale_factor):
    fw = fortran_write.FortranWrite(outfile)
    fields = truchas_data.field_names(series_id)

    # HEADER SEGMENT
    # file format magic number
    fw.write_str("{:8s}".format("TRF-3"))

    # feature list
    features = feature_list(truchas_data, fields)
    fw.write_i4x0(len(features))
    for f in features:
        fw.write_str("{:32s}".format(f))

    # simulation specification (free use -- not using any now)
    fw.write_i4x0(0)

    # global data
    fw.write_r8x0(truchas_data.time(series_id))
    fw.write_r8x0(truchas_data.time_step(series_id))
    fw.write_i4x0(truchas_data.cycle(series_id))
    fw.write_i4x0(truchas_data.ncell)
    fw.write_i4x0(truchas_data.nnode)

    # MESH SEGMENT
    for cn in cell_node_map(truchas_data).transpose():
        fw.write_i4x1(cn)

    if "BLOCKID" in truchas_data._root["Simulations/MAIN/Non-series Data/"]:
        bid = truchas_data._root["Simulations/MAIN/Non-series Data/BLOCKID"][:]
        bid = bid[truchas_data._cellmap]
        fw.write_i4x0(1)
        fw.write_i4x1(bid)
    else:
        fw.write_i4x0(0)

    for x in truchas_data.node_coordinates().transpose():
        fw.write_r8x1(x)

    # CORE DATA SEGMENT
    fw.write_r8x1(truchas_data.field(series_id, "Z_RHO"))
    fw.write_r8x1(truchas_data.field(series_id, "Z_TEMP"))
    fw.write_r8x1(truchas_data.field(series_id, "Z_ENTHALPY"))

    if "fluid_flow" in features:
        fw.write_r8x1(truchas_data.field(series_id, "Z_P"))

        for v in truchas_data.field(series_id, "Z_VC").transpose():
            fw.write_r8x1(v)

        for v in truchas_data.field(series_id, "Face_Vel").transpose():
            fw.write_r8x1(v)
    else:
        dummy = sp.zeros(truchas_data.ncell)
        for i in range(10):
            fw.write_r8x1(dummy)

    if "VOF" in fields:
        vof = truchas_data.field(series_id, "VOF").transpose()
        fw.write_i4x0(vof.shape[0])
        for vf in vof:
            fw.write_r8x1(vf)
    else:
        # single phase problem
        fw.write_i4x0(1)
        fw.write_r8x1(sp.ones(truchas_data.ncell))

    # SOLID MECHANICS SEGMENT
    if "solid_mechanics" in features:
        for n in range(12):
            for field in ("TOTAL_STRAIN_", "ELASTIC_STRESS_", "PLASTIC_STRAIN_"):
                name = field + "{:02d}".format(n+1)
                for t in truchas_data.field(series_id, name).transpose():
                    fw.write_r8x1(t)

            name = "PLASTIC_STRAIN_RATE_{:02d}".format(n+1)
            fw.write_r8x1(truchas_data.field(series_id, name))

        for t in truchas_data.field(series_id, "epsilon").transpose():
            fw.write_r8x1(t)

        for t in truchas_data.field(series_id, "sigma").transpose():
            fw.write_r8x1(t)

        for t in truchas_data.field(series_id, "e_plastic").transpose():
            fw.write_r8x1(t)

        fw.write_r8x1(truchas_data.field(series_id, "epsdot"))

        for t in truchas_data.field_node(series_id, "RHS").transpose():
            fw.write_r8x1(t)

        for t in truchas_data.field(series_id, "epstherm").transpose():
            fw.write_r8x1(t)

        for t in truchas_data.field(series_id, "epspc").transpose():
            fw.write_r8x1(t)

        for t in truchas_data.field_node(series_id, "Displacement").transpose():
            fw.write_r8x1(t)

    # SPECIES SEGMENT
    if "species" in features:
        nspecies = truchas_data._root["Simulations/MAIN"].attrs["NUM_SPECIES"]
        assert nspecies > 0
        fw.write_i4x0(nspecies)

        for n in range(nspecies):
            fw.write_r8x1(truchas_data.field(series_id, "phi" + str(n+1)))

    # MICROSTRUCTURE SEGMENT
    if "microstructure" in features:
        ustruc_map = truchas_data._series(series_id)["CP-USTRUC-MAP"][:]
        fw.write_i4x0(ustruc_map.size)
        fw.write_i4x1(ustruc_map)

        # get the number of components
        ncomp = 0
        while "CP-USTRUC-COMP-" + str(ncomp+1) in fields: ncomp += 1
        fw.write_i4x0(ncomp)

        for n in range(ncomp):
            name = "CP-USTRUC-COMP-" + str(n+1)
            ustruc_comp = truchas_data._series(series_id)[name][:]
            cid = truchas_data._series(series_id)[name].attrs["COMP-ID"]

            fw.write_i4x0(cid)
            fw.write_i4x0(ustruc_comp.shape[1])
            fw.write_i8x2(ustruc_comp)

    # JOULE HEAT SEGMENT
    if "joule_heat" in features:
        t = truchas_data.time(series_id)

        # scan through the EMnnn simulations, in order, looking for
        # the last one whose TIME attribute value is <= the time
        # attribute for the requested series sequence number.
        em_fields = list(truchas_data._root["Simulations"].keys())
        n = 0; t_em_next = 0; name_next = ""
        while t_em_next <= t:
            t_em = t_em_next
            name = name_next

            n += 1
            name_next = "EM{:03d}".format(n)
            if name_next not in em_fields: break
            t_em_next = truchas_data._root["Simulations/" + name_next] \
                                    .attrs["TIME"]
        em_sim = truchas_data._root["Simulations/" + name + "/Non-series Data"]
        print("Using EM simulation {:s} (t = {:f})".format(name, t_em))

        fw.write_r8x0(em_sim["FREQ"][0])
        fw.write_r8x0(em_sim["UHFS"][0])

        coils = em_sim["COILS"][:]
        fw.write_i4x0(coils.shape[0])
        for c in coils:
            fw.write_r8x0(c[0])
            fw.write_r8x1(c[1:4])
            fw.write_r8x0(c[4])
            fw.write_r8x0(c[5])
            fw.write_i4x0(int(round(c[6])))

        array = em_sim["MU"][:]
        fw.write_i4x0(array.size)
        fw.write_r8x1(array)

        array = em_sim["SIGMA"][:]
        fw.write_i4x0(array.size)
        fw.write_r8x1(array)

        array = em_sim["JOULE"][:][truchas_data._cellmap]
        fw.write_i4x0(truchas_data.ncell)
        fw.write_r8x1(array)


def feature_list(truchas_data, fields):
    """Returns a list of features present based on fields in the output."""
    features = []
    if "Z_VC" in fields: features.append("fluid_flow")
    if "epsilon" in fields: features.append("solid_mechanics")
    if "phi1" in fields: features.append("species")
    if "Joule_P" in fields: features.append("joule_heat")
    if "CP-USTRUC-MAP" in fields: features.append("microstructure")
    return features


def cell_node_map(truchas_data):
    # Load the cnode map, convert to 0-based indexing,
    # reorder for cell and node ordering, then convert
    # back to 1-based indexing.
    cnode = truchas_data._root["Meshes/DEFAULT/Element Connectivity"][:] - 1
    nm = truchas_data._root["Simulations/MAIN/Non-series Data/NODEMAP"][:] - 1
    cnode = nm[cnode[truchas_data._cellmap,:]] + 1
    return cnode


def print_cycles(truchas_data):
    """Prints a list of available cycles"""
    nseries = truchas_data.num_series()
    if nseries > 0:
        cycle_time = [(truchas_data.cycle(s+1), truchas_data.time(s+1))
                      for s in range(nseries)]
        print(" cycle   time")
        print('-'*29)
        for ct in cycle_time:
            print(ct)
    else:
        print("no cycle output exists")


def parse_argv():
    parser = argparse.ArgumentParser(
        description=("Creates a Truchas restart file using data "
                     "from an h5 output file."))
    parser.add_argument("-l", action="store_true",
                        help=("Print a list of the available cycles from which "
                              "the restart file can be created. No restart file "
                              "is written."))
    parser.add_argument("-n", type=int, default=-1,
                        help=("Data from cycle N is used to generate the "
                              "restart file; if not specified the last cycle "
                              "is used."))
    parser.add_argument("-o", type=str, metavar="FILE",
                        help=("Write restart data to FILE. If not specified, "
                              "FILE is taken to be the H5FILE name with the "
                              ".h5 suffix replaced by .restart.N, where N is "
                              "the cycle number."))
    parser.add_argument("-m", type=argparse.FileType('r'), metavar="FILE",
                        help=("Create a mapped restart file using the specified "
                              "ExodusII mesh FILE as the target mesh."))
    parser.add_argument("-s", type=float, default=1, metavar="FLOAT",
                        help=("Scale the mapped restart mesh by the "
                              "factor FLOAT."))
    parser.add_argument("h5file", help="Input H5 file.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_argv()
    truchas_data = truchas.TruchasData(args.h5file)

    if args.l:
        print_cycles(truchas_data)
    else:
        # get the cycle id and series id
        nseries = truchas_data.num_series()
        if args.n == -1:
            cycle = truchas_data.cycle(nseries)
            series_id = nseries
        else:
            cycles = [truchas_data.cycle(s+1) for s in range(nseries)]
            cycle = args.n
            series_id = cycles.index(cycle) + 1

        outfile = os.path.abspath(args.o) if args.o \
            else os.path.splitext(args.h5file)[0] + ".restart." + str(cycle)

        # If the parent output directory doesn't exist, create it
        outdir = os.path.dirname(outfile)
        if not os.path.exists(outdir):
            os.mkdir(outdir)

        print("Using cycle {:d} and writing to {:s}".format(cycle, outfile))
        write_restart(outfile, truchas_data, series_id, args.s)
