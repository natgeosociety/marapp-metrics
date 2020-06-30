import os

import ee

GOOGLE_SERVICE_ACCOUNT = os.environ.get("GOOGLE_SERVICE_ACCOUNT")


def initialize_google_ee():
    """Initialize the EE library."""

    if GOOGLE_SERVICE_ACCOUNT:
        credentials = ee.ServiceAccountCredentials(
            None, key_data=GOOGLE_SERVICE_ACCOUNT
        )
        ee.Initialize(credentials)
    else:
        ee.Initialize()


def map_function(image, scale, reducers, keep_geom, best_effort, max_pixels, band=True):
    def reducer_wrapper(feat):
        geom = feat.geometry()
        for key, reducer in reducers.items():
            result = image.reduceRegion(
                reducer=reducer,
                geometry=geom,
                scale=scale,
                maxPixels=max_pixels,
                bestEffort=best_effort,
                crs="EPSG:4326",
            )
            if not keep_geom:
                feat = feat.setGeometry(None)
            if band:
                result = result.get(key)
            feat = feat.set({key: result})
        return feat

    return reducer_wrapper


def simple_mask_function(im, mask_im, **kwargs):
    """
    Applies a simple mask onto im with a single QA value from mask_im.
    """
    mask = None

    for k, v in kwargs.items():
        if str(k) == "gt":
            mask = mask_im.gt(v)
        elif str(k) == "gte":
            mask = mask_im.gte(v)
        elif str(k) == "lt":
            mask = mask_im.lt(v)
        elif str(k) == "lte":
            mask = mask_im.lte(v)
        elif str(k) == "eq":
            mask = mask_im.eq(v)
        elif str(k) == "eq_or":
            v = list(v)
            mask = mask_im.eq(v[0]).Or(mask_im.eq(v[1]))
        elif str(k) == "range":
            v = list(v)
            mask = mask_im.gte(v[0]).And(mask_im.lt(v[1]))

    if mask is not None:
        return im.updateMask(mask)


def filter_fires(im):
    """
    Earth engine QA filter for fires
    """
    burn_dates = im.select("BurnDate")
    valid_dates = burn_dates.gt(0).And(burn_dates.lt(367))
    valid_qa = im.select("QA").lte(4)
    # keep QA values 1-4 (5 is detection over agricultural areas)
    mask = valid_dates.And(valid_qa)

    return im.updateMask(mask)
