#!/usr/bin/env python3
"""Downloads and meshes HUC and hydrography data.

Default data for HUCs comes from The National Map's Watershed Boundary Dataset (WBD).
Default data for hydrography comes from The National Map's National Hydrography Dataset (NHD).
See: "https://nhd.usgs.gov/"

Default DEMs come from the National Elevation Dataset (NED).
See: "https://lta.cr.usgs.gov/NED"
"""

import matplotlib
#matplotlib.use("PDF")

import os,sys
import numpy as np
from matplotlib import pyplot as plt
import shapely

import workflow.hilev
import workflow.ui
import workflow.files

if __name__ == '__main__':
    # set up parser
    parser = workflow.ui.get_basic_argparse(__doc__)
    workflow.ui.outmesh_options(parser)
    workflow.ui.simplify_options(parser)
    workflow.ui.refine_options(parser)
    workflow.ui.center_options(parser)
    workflow.ui.huc_source_options(parser)
    workflow.ui.dem_source_options(parser)
    workflow.ui.huc_args(parser)

    # parse args, log
    args = parser.parse_args()
    workflow.ui.setup_logging(args.verbosity, args.logfile)
    sources = workflow.files.get_sources(args)
    
    # collect data
    hucs, centroid = workflow.hilev.get_hucs(args.HUC, sources['HUC'], args.center)
    rivers = workflow.hilev.get_rivers(args.HUC, sources['HUC'])
    dem_profile, dem = workflow.hilev.get_dem(args.HUC, sources)

    # make 2D mesh
    if args.center:
        rivers = [shapely.affinity.translate(r, -centroid.coords[0][0], -centroid.coords[0][1]) for r in rivers]
    rivers = workflow.hilev.simplify_and_prune(hucs, rivers, args)

    # plot the result
    if args.verbosity > 0:
        plt.figure(figsize=(5,3))
        workflow.plot.hucs(hucs, 'k')
        workflow.plot.rivers(rivers, color='r')
        plt.gca().set_aspect('equal', 'datalim')
        plt.xlabel('')
        plt.ylabel('')
        #plt.savefig('my_mesh')
        plt.show()

    mesh_points2, mesh_tris = workflow.hilev.triangulate(hucs, rivers, args)

    # plot the result
    if args.verbosity > 0:
        plt.figure(figsize=(5,3))
        workflow.plot.triangulation(mesh_points2, mesh_tris, linewidth=0.5)
        workflow.plot.hucs(hucs, 'k')
        workflow.plot.rivers(rivers, color='r')
        plt.gca().set_aspect('equal', 'datalim')
        plt.xlabel('')
        plt.ylabel('')
        #plt.savefig('my_mesh')
        plt.show()

    # elevate to 3D
    if args.center:
        mesh_points2_uncentered = mesh_points2 + np.expand_dims(np.array(centroid.coords[0]),0)
    else:
        mesh_points2_uncentered = mesh_points2

    mesh_points3_uncentered = workflow.hilev.elevate(mesh_points2_uncentered, dem, dem_profile)

    if args.center:
        mesh_points3 = np.empty(mesh_points3_uncentered.shape,'d')
        mesh_points3[:,0:2] = mesh_points2
        mesh_points3[:,2] = mesh_points3_uncentered[:,2]
    else:
        mesh_points3 = mesh_ponts3_uncentered

    # plot the result
    if args.verbosity > 0:
        plt.figure(figsize=(5,3))
        workflow.plot.triangulation(mesh_points3, mesh_tris, linewidth=0.5)
        plt.colorbar()
        workflow.plot.hucs(hucs, 'k')
        workflow.plot.rivers(rivers, color='r')
        plt.gca().set_aspect('equal', 'datalim')
        plt.xlabel('')
        plt.ylabel('')
        #plt.savefig('my_mesh')
        plt.show()

    # save mesh
    metadata_lines = ['Mesh of HUC: %s including all HUC 12 boundaries and hydrography.'%args.HUC,
                      '',
                      '  coordinate system = epsg:%04i'%(workflow.conf.rcParams['epsg']),
                      ]

    if args.center:
        metadata_lines.append('  centered to: %g, %g'%centroid.coords[0])
    metadata_lines.extend(['',
                           'Mesh generated by workflow mesh_hucs.py script.',
                           '',
                           workflow.utils.get_git_revision_hash(),
                           '',
                           'with calling sequence:',
                           '  '+' '.join(sys.argv)])

    if args.outfile is None:
        outdir = "data/meshes"
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        outfile = os.path.join(outdir, 'huc_%s.vtk'%args.HUC)
    else:
        outfile = args.outfile            
    workflow.hilev.save(outfile, mesh_points3, mesh_tris, '\n'.join(metadata_lines))
    sys.exit(0)
