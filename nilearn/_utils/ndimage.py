"""
N-dimensional image manipulation
"""
# Author: Gael Varoquaux, Alexandre Abraham, Philippe Gervais
# License: simplified BSD

import numpy as np
from scipy import ndimage

from .._utils import  check_niimg_3d
from .._utils.compat import _basestring, get_affine
from .._utils.niimg_conversions import _safe_get_data
from ..image import new_img_like

###############################################################################
# Operating on connected components
###############################################################################

def largest_connected_component(volume):
    """Return the largest connected component of a 3D array.

    Parameters
    -----------
    volume: numpy.array
        3D boolean array indicating a volume.

    Returns
    --------
    volume: numpy.array
        3D boolean array with only one connected component.
    """
    if hasattr(volume, "get_data") \
       or isinstance(volume, _basestring):
        raise ValueError('Please enter a valid numpy array. For images use\
                         largest_connected_component_img')

    # We use asarray to be able to work with masked arrays.
    volume = np.asarray(volume)
    labels, label_nb = ndimage.label(volume)
    if not label_nb:
        raise ValueError('No non-zero values: no connected components')
    if label_nb == 1:
        return volume.astype(np.bool)
    label_count = np.bincount(labels.ravel().astype(np.int))
    # discard the 0 label
    label_count[0] = 0
    return labels == label_count.argmax()


def largest_connected_component_img(imgs):
    """ Return the largest connected component of an image or list of images.

    Parameters
    ----------
    imgs: Niimg-like object or iterable of Niimg-like objects
        See http://nilearn.github.io/manipulating_images/input_output.html
        Image(s) to extract the largest connected component from.

    Returns
    -------
        img or list of img containing the largest connected component
    """
    if hasattr(imgs, "__iter__") \
       and not isinstance(imgs, _basestring):
        single_img = False
    else:
        single_img = True
        imgs = [imgs]

    ret = []
    for img in imgs:
        img = check_niimg_3d(img)
        affine = get_affine(img)
        largest_component = largest_connected_component(_safe_get_data(img))
        ret.append(new_img_like(img, largest_component, affine,
                                copy_header=True))

    if single_img:
        return ret[0]
    else:
        return ret


def get_border_data(data, border_size):
    return np.concatenate([
        data[:border_size, :, :].ravel(),
        data[-border_size:, :, :].ravel(),
        data[:, :border_size, :].ravel(),
        data[:, -border_size:, :].ravel(),
        data[:, :, :border_size].ravel(),
        data[:, :, -border_size:].ravel(),
    ])


def _peak_local_max(image, min_distance=10, threshold_abs=0, threshold_rel=0.1,
                    num_peaks=np.inf):
    """Find peaks in an image, and return them as coordinates or a boolean array.

    Peaks are the local maxima in a region of `2 * min_distance + 1`
    (i.e. peaks are separated by at least `min_distance`).

    NOTE: If peaks are flat (i.e. multiple adjacent pixels have identical
    intensities), the coordinates of all such pixels are returned.

    Parameters
    ----------
    image : ndarray of floats
        Input image.
    min_distance : int
        Minimum number of pixels separating peaks in a region of `2 *
        min_distance + 1` (i.e. peaks are separated by at least
        `min_distance`). To find the maximum number of peaks, use `min_distance=1`.
    threshold_abs : float
        Minimum intensity of peaks.
    threshold_rel : float
        Minimum intensity of peaks calculated as `max(image) * threshold_rel`.
    num_peaks : int
        Maximum number of peaks. When the number of peaks exceeds `num_peaks`,
        return `num_peaks` peaks based on highest peak intensity.

    Returns
    -------
    output : ndarray or ndarray of bools
        Boolean array shaped like `image`, with peaks represented by True values.

    Notes
    -----
    The peak local maximum function returns the coordinates of local peaks
    (maxima) in a image. A maximum filter is used for finding local maxima.
    This operation dilates the original image. After comparison between
    dilated and original image, peak_local_max function returns the
    coordinates of peaks where dilated image = original.

    This code is mostly adapted from scikit image 0.11.3 release.
    Location of file in scikit image: peak_local_max function in skimage.feature.peak
    """
    out = np.zeros_like(image, dtype=np.bool)

    if np.all(image == image.flat[0]):
        return out

    image = image.copy()

    size = 2 * min_distance + 1
    image_max = ndimage.maximum_filter(image, size=size, mode='constant')

    mask = (image == image_max)
    image *= mask

    # find top peak candidates above a threshold
    peak_threshold = max(np.max(image.ravel()) * threshold_rel, threshold_abs)

    # get coordinates of peaks
    coordinates = np.argwhere(image > peak_threshold)

    if coordinates.shape[0] > num_peaks:
        intensities = image.flat[np.ravel_multi_index(coordinates.transpose(), image.shape)]
        idx_maxsort = np.argsort(intensities)[::-1]
        coordinates = coordinates[idx_maxsort][:num_peaks]

    nd_indices = tuple(coordinates.T)
    out[nd_indices] = True
    return out
