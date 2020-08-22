import rasterio
import rasterio.merge
import rasterio.warp
import rasterio.plot
from rasterio import windows
from itertools import product
from osgeo import gdal
from tqdm import tqdm

from pathlib import Path
from handler import Files


def reproject(in_file, dest_file, in_crs, dest_crs='EPSG:4326'):

    """
    Re-project images
    :param in_file: path to file to be reprojected
    :param dest_file: path to write re-projected image
    :param in_crs: crs of input file -- only valid if image does not contain crs in metadata
    :param dest_crs: destination crs
    :return: path to re-projected image
    """

    input_raster = gdal.Open(str(in_file))

    if input_raster.GetSpatialRef() is not None:
        in_crs = input_raster.GetSpatialRef()

    if in_crs is None:
        raise ValueError('No CRS set')

    # TODO: Change the resolution based on the lowest resolution in the inputs
    gdal.Warp(str(dest_file), input_raster, dstSRS=dest_crs, srcSRS=in_crs, xRes=6e-06, yRes=6e-06)

    return dest_file.resolve()


def create_mosaic(in_files, out_file):

    """
    Creates mosaic from in_files.
    :param in_files: list of paths to input files
    :param out_file: path to output mosaic
    :return: path to output file
    """

    file_objs = []

    for file in in_files:
        src = rasterio.open(file)
        file_objs.append(src)

    mosaic, out_trans = rasterio.merge.merge(file_objs)

    out_meta = src.meta.copy()

    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans
                     }
                    )

    with rasterio.open(out_file, "w", **out_meta) as dest:
        dest.write(mosaic)

    return out_file.resolve()


def get_intersect(*args):

    """
    Computes intersect of input rasters.
    :param args: list of files to compute
    :return: tuple of intersect in (left, bottom, right, top)
    """

    # TODO: This has been tested for NW hemisphere. Real intersection would be ideal.

    left = []
    bottom = []
    right = []
    top = []

    for arg in args:
        raster = rasterio.open(arg)
        left.append(raster.bounds[0])
        bottom.append(raster.bounds[1])
        right.append(raster.bounds[2])
        top.append(raster.bounds[3])

    intersect = (max(left), max(bottom), min(right), min(top))

    return intersect


def create_chips(in_raster, out_dir, intersect):

    """
    Creates chips from mosaic that fall inside the intersect
    :param in_raster: mosaic to create chips from
    :param out_dir: path to write chips
    :param intersect: bounds of chips to create
    :return: list of path to chips
    """

    output_filename = 'tile_{}-{}.tif'

    def get_intersect_win(rio_obj):

        """
        Calculate rasterio window from intersect
        :param rio_obj: rasterio dataset
        :return: window of intersect
        """

        xy_ul = rasterio.transform.rowcol(rio_obj.transform, intersect[0], intersect[3])
        xy_lr = rasterio.transform.rowcol(rio_obj.transform, intersect[2], intersect[1])

        int_window = rasterio.windows.Window(xy_ul[1], xy_ul[0],
                                             abs(xy_ul[1] - xy_lr[1]),
                                             abs(xy_ul[0] - xy_lr[0]))

        return int_window

    def get_tiles(ds, width=1024, height=1024):

        """
        Create chip tiles generator
        :param ds: rasterio dataset
        :param width: tile width
        :param height: tile height
        :return: generator of rasterio windows and transforms for each tile to be created
        """

        intersect_window = get_intersect_win(ds)
        offsets = product(range(intersect_window.col_off, intersect_window.width + intersect_window.col_off, width),
                          range(intersect_window.row_off, intersect_window.height + intersect_window.row_off, height))
        for col_off, row_off in offsets:
            window = windows.Window(col_off=col_off, row_off=row_off, width=width, height=height).intersection(intersect_window)
            transform = windows.transform(window, ds.transform)
            yield window, transform

    chips = []

    with rasterio.open(in_raster) as inds:
        tile_width, tile_height = 1024, 1024

        meta = inds.meta.copy()

        for window, transform in tqdm(get_tiles(inds)):
            meta['transform'] = transform
            meta['width'], meta['height'] = window.width, window.height
            output_filename = f'tile_{int(window.col_off)}-{int(window.row_off)}.tif'
            outpath = out_dir.joinpath(output_filename)

            with rasterio.open(outpath, 'w', **meta) as outds:
                outds.write(inds.read(window=window))

            chips.append(outpath.resolve())

    return chips