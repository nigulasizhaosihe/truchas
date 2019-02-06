#!/usr/bin/env python3

#===============================================================================
#
#  Copyright (c) Los Alamos National Security, LLC.  This file is part of the
#  Truchas code (LA-CC-15-097) and is subject to the revised BSD license terms
#  in the LICENSE file found in the top-level directory of this distribution.
#
#===============================================================================

import sys
import os
import posixpath
import copy
from xml.etree import ElementTree as ET

import h5py

def series_xdmf(series, grid_pointer):
    """Returns XDMF-formated XML describing data in a DANU H5 file series."""
    grid = copy.deepcopy(grid_pointer)
    grid.append(ET.Element("Time", {"Value": str(series.attrs["time"])}))

    for field in series.values():
        # get field name and type
        if field.ndim == 1:
            attr_type = "Scalar"
            field_name = field.attrs["FIELDNAME"].decode()
            dims = str(field.shape[0])
        elif field.ndim == 2:
            field_name = posixpath.basename(field.name)
            attr_type = "Vector" if field_name in ("Z_VC", "Displacement") \
                else "Matrix"
            dims = "{:d} {:d}".format(*field.shape)
        else:
            raise ValueError("Fields with >2 dimensions are not supported")

        try:
            field_center = field.attrs["FIELDTYPE"].capitalize().decode()
        except:
            continue

        xdmf_data = ET.Element("DataItem", {"Format": "HDF",
                                            "Dimensions": dims,
                                            "DataType": "Float",
                                            "Precision": "8",
                                            "Name": field_name})
        xdmf_data.text = series.file.filename + ":" + field.name

        if attr_type == "Matrix":
            # Paraview does not read matrices properly.
            # Rewrite as a bunch of scalars.
            slab_dims = "{:d} 1".format(field.shape[0])
            for n in range(field.shape[1]):
                slab_name = field.attrs["FIELDNAME{:d}".format(n+1)].decode()
                xdmf_field = ET.Element("Attribute", {"Name": slab_name,
                                                      "AttributeType": "Scalar",
                                                      "Center": field_center})
                xdmf_slab = ET.SubElement(xdmf_field, "DataItem",
                                          {"ItemType": "HyperSlab",
                                           "Type": "HyperSlab",
                                           "Dimensions": slab_dims})
                xdmf_slab_data = ET.SubElement(xdmf_slab, "DataItem",
                                               {"Dimensions": "3 2",
                                                "Format": "XML"})
                xdmf_slab_data.text = \
                    "0 {:d}   1 1   {:d} 1".format(n, field.shape[0])

                xdmf_slab.append(xdmf_data)
                grid.append(xdmf_field)

        else:
            xdmf_field = ET.Element("Attribute", {"Name": field_name,
                                                  "AttributeType": attr_type,
                                                  "Center": field_center})
            xdmf_field.append(xdmf_data)
            grid.append(xdmf_field)

    return grid


def dtype_extract(d):
    datatype = {"int8": ("Int", "1"),
                "int16": ("Int", "2"),
                "int32": ("Int", "4"),
                "int64": ("Int", "8"),
                "float32": ("Float", "4"),
                "float64": ("Float", "8")}
    return datatype[d.name]


def grid_xdmf(data):
    # geometry
    node_loc = "/Simulations/MAIN/Mesh/Nodal Coordinates"
    data_type, precision = dtype_extract(data[node_loc].dtype)
    shape = data[node_loc].shape
    geometry = ET.Element("Geometry", {"GeometryType": "XYZ"})
    node_coordinates = ET.SubElement(geometry, "DataItem",
                                     {"DataType": data_type,
                                      "Precision": precision,
                                      "Dimensions": "{:d} {:d}".format(*shape),
                                      "Format": "HDF",
                                      "Name": "Coordinates"})
    node_coordinates.text = data.filename + ":" + node_loc

    # topology
    element_loc = "/Simulations/MAIN/Mesh/Element Connectivity"
    data_type, precision = dtype_extract(data[element_loc].dtype)
    shape = data[element_loc].shape
    topology = ET.Element("Topology",
                          {"BaseOffset": str(data[element_loc].attrs["Offset"]),
                           "NumberOfElements": str(data[element_loc].shape[0]),
                           "TopologyType": "Hexahedron"})
    connectivity = ET.SubElement(topology, "DataItem",
                                 {"DataType": data_type,
                                  "Precision": precision,
                                  "Dimensions": str(data[element_loc].size),
                                  "Format": "HDF",
                                  "Name": "Connectivity"})
    connectivity.text = data.filename + ":" + element_loc

    # grid pointer
    gp = ET.Element("Grid", {"GridType": "Uniform"})
    gp_geometry = ET.SubElement(gp, "Geometry",
                                {"Reference": "/Xdmf/Domain/Geometry"})
    gp_topology = ET.SubElement(gp, "Topology",
                                {"Reference": "/Xdmf/Domain/Topology"})

    return geometry, topology, gp


def hdf5_to_xdmf(infile, outfile, verbose=False):
    """Produces an XDMF3 file pointing to data in an HDF5 container."""
    h5in = h5py.File(infile, "r")

    xdmf = ET.Element("Xdmf", {"Version": "2.0",
                               "xmlns:xi": "http://www.w3.org/2001/XInclude"})
    xdmf_domain = ET.SubElement(xdmf, "Domain")

    # store grid data and pointer
    geometry, topology, xdmf_grid_pointer = grid_xdmf(h5in)
    xdmf_domain.append(geometry)
    xdmf_domain.append(topology)

    # store time series data
    xdmf_grid_parent = ET.SubElement(xdmf_domain, "Grid",
                                  {"GridType": "Collection",
                                   "CollectionType": "Temporal"})

    for series in h5in["/Simulations/MAIN/Series Data"].values():
        xdmf_grid_parent.append(series_xdmf(series, xdmf_grid_pointer))

    # write to file
    xmltree = ET.ElementTree(xdmf)
    with open(outfile, 'wb') as f:
        f.write(b'<?xml version="1.0" ?>')
        f.write(b'<!DOCTYPE Xdmf SYSTEM "Xdmf.dtd" []>')
        xmltree.write(f)


if __name__=="__main__":
    if len(sys.argv) != 2:
        raise Exception('Usage: xdmf-writer.py hdf5_file.h5')
    infile = sys.argv[1]
    outfile = os.path.splitext(infile)[0] + ".xmf"
    hdf5_to_xdmf(infile, outfile)
