"""
Applies the USGS L7 Phase-2 Gap filling protocol, using a single kernel size.
Based on the GEE code found on the GEE forums. See this GEE code editor for original code:
https://code.earthengine.google.com/263d5d0fec9a198307c7661739801382
Original gap fill algorithm was proposed in 'SLC gap-filled products phase one methodology' by Scarammuza et al. (2004)
"""

import ee

MIN_SCALE = 1/3
MAX_SCALE = 3
MIN_NEIGHBORS = 144


def gap_fill(src, fill, kernel_size, upscale=False):
    """
    Gap filling
    :param src: scene to be filled
    :param fill: scene to use for the fillin
    :param kernel_size: size of the kernel in meters
    :param upscale: indicates whether to upscale the computation to coarser resolution for faster computation time
    :return: filled image
    """
    kernel = ee.Kernel.square(kernel_size * 30, "meters", False)

    # Find the pixels common to both scenes.
    common = src.mask().And(fill.mask())
    fc = fill.updateMask(common)
    sc = src.updateMask(common)

    # Find the primary scaling factors with a regression.
    # Interleave the bands for the regression.  This assumes the bands have the same names.
    regress = fc.addBands(sc)
    regress = regress.select(regress.bandNames().sort())

    ratio = 5

    if upscale:
        fit = regress \
            .reduceResolution(ee.Reducer.median(), False, 500) \
            .reproject(regress.select(0).projection().scale(ratio, ratio)) \
            .reduceNeighborhood(ee.Reducer.linearFit().forEach(src.bandNames()), kernel, None, False) \
            .unmask() \
            .reproject(regress.select(0).projection().scale(ratio, ratio))
    else:
        fit = regress \
            .reduceNeighborhood(ee.Reducer.linearFit().forEach(src.bandNames()), kernel, None, False)

    offset = fit.select(".*_offset")
    scale = fit.select(".*_scale")

    # Find the secondary scaling factors using just means and stddev
    reducer = ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True)

    if upscale:
        src_stats = src\
            .reduceResolution(ee.Reducer.median(), False, 500)\
            .reproject(regress.select(0).projection().scale(ratio, ratio))\
            .reduceNeighborhood(reducer, kernel, None, False)\
            .reproject(regress.select(0).projection().scale(ratio, ratio))

        fill_stats = fill\
            .reduceResolution(ee.Reducer.median(), False, 500)\
            .reproject(regress.select(0).projection().scale(ratio, ratio))\
            .reduceNeighborhood(reducer, kernel, None, False)\
            .reproject(regress.select(0).projection().scale(ratio, ratio))
    else:
        src_stats = src\
            .reduceNeighborhood(reducer, kernel, None, False)

        fill_stats = fill\
            .reduceNeighborhood(reducer, kernel, None, False)


    scale2 = src_stats.select(".*stdDev").divide(fill_stats.select(".*stdDev"))
    offset2 = src_stats.select(".*mean").subtract(fill_stats.select(".*mean").multiply(scale2))

    invalid = scale.lt(MIN_SCALE).Or(scale.gt(MAX_SCALE))
    scale = scale.where(invalid, scale2)
    offset = offset.where(invalid, offset2)

    # When all else fails, just use the difference of means as an offset.
    invalid2 = scale.lt(MIN_SCALE).Or(scale.gt(MAX_SCALE))
    scale = scale.where(invalid2, 1)
    offset = offset.where(invalid2, src_stats.select(".*mean").subtract(fill_stats.select(".*mean")))

    # Apply the scaling and mask off pixels that didn't have enough neighbors.
    count = common.reduceNeighborhood(ee.Reducer.count(), kernel, None, True, "boxcar")

    scaled = fill.multiply(scale).add(offset)\
        .updateMask(count.gte(MIN_NEIGHBORS))

    return src.unmask(scaled, True)