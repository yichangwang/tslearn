"""
The :mod:`tslearn.utils` module includes various utilities.
"""

import numpy
import os
from sklearn.base import BaseEstimator, TransformerMixin
from scipy.io import arff

__author__ = 'Romain Tavenard romain.tavenard[at]univ-rennes2.fr'


def _arraylike_copy(arr):
    """Duplicate content of arr into a numpy array.

     Examples
     --------
     >>> X_npy = numpy.array([1, 2, 3])
     >>> numpy.alltrue(_arraylike_copy(X_npy) == X_npy)
     True
     >>> _arraylike_copy(X_npy) is X_npy
     False
     >>> numpy.alltrue(_arraylike_copy([1, 2, 3]) == X_npy)
     True
     """
    if type(arr) != numpy.ndarray:
        return numpy.array(arr)
    else:
        return arr.copy()


def bit_length(n):
    """Returns the number of bits necessary to represent an integer in binary, excluding the sign and leading zeros.

    This function is provided for Python 2.6 compatibility.

    Examples
    --------
    >>> bit_length(0)
    0
    >>> bit_length(2)
    2
    >>> bit_length(1)
    1
    """
    k = 0
    try:
        if n > 0:
            k = n.bit_length()
    except AttributeError:  # In Python2.6, bit_length does not exist
        k = 1 + int(numpy.log2(abs(n)))
    return k


def to_time_series(ts, remove_nans=False):
    """Transforms a time series so that it fits the format used in ``tslearn`` models.

    Parameters
    ----------
    ts : array-like
        The time series to be transformed.
    remove_nans : bool (default: False)
        Whether trailing NaNs at the end of the time series should be removed or not

    Returns
    -------
    numpy.ndarray of shape (sz, d)
        The transformed time series.
    
    Example
    -------
    >>> to_time_series([1, 2]) # doctest: +NORMALIZE_WHITESPACE
    array([[ 1.],
           [ 2.]])
    >>> to_time_series([1, 2, numpy.nan]) # doctest: +NORMALIZE_WHITESPACE
    array([[ 1.],
           [ 2.],
           [ nan]])
    >>> to_time_series([1, 2, numpy.nan], remove_nans=True) # doctest: +NORMALIZE_WHITESPACE
    array([[ 1.],
           [ 2.]])
    
    See Also
    --------
    to_time_series_dataset : Transforms a dataset of time series
    """
    ts_out = _arraylike_copy(ts)
    if ts_out.ndim == 1:
        ts_out = ts_out.reshape((-1, 1))
    if ts_out.dtype != numpy.float:
        ts_out = ts_out.astype(numpy.float)
    if remove_nans:
        ts_out = ts_out[:ts_size(ts_out)]
    return ts_out


def to_time_series_dataset(dataset, dtype=numpy.float):
    """Transforms a time series dataset so that it fits the format used in ``tslearn`` models.

    Parameters
    ----------
    dataset : array-like
        The dataset of time series to be transformed.
    dtype : data type (default: numpy.float)
        Data type for the returned dataset.

    Returns
    -------
    numpy.ndarray of shape (n_ts, sz, d)
        The transformed dataset of time series.
    
    Example
    -------
    >>> to_time_series_dataset([[1, 2]]) # doctest: +NORMALIZE_WHITESPACE
    array([[[ 1.],
            [ 2.]]])
    >>> to_time_series_dataset([[1, 2], [1, 4, 3]]) # doctest: +NORMALIZE_WHITESPACE
    array([[[  1.],
            [  2.],
            [ nan]],
    <BLANKLINE>
           [[  1.],
            [  4.],
            [  3.]]])
    
    See Also
    --------
    to_time_series : Transforms a single time series
    """
    if numpy.array(dataset[0]).ndim == 0:
        dataset = [dataset]
    n_ts = len(dataset)
    max_sz = max([ts_size(to_time_series(ts)) for ts in dataset])
    d = to_time_series(dataset[0]).shape[1]
    dataset_out = numpy.zeros((n_ts, max_sz, d), dtype=dtype) + numpy.nan
    for i in range(n_ts):
        ts = to_time_series(dataset[i], remove_nans=True)
        dataset_out[i, :ts.shape[0]] = ts
    return dataset_out


def to_sklearn_dataset(dataset, dtype=numpy.float, return_dim=False):
    """Transforms a time series dataset so that it fits the format used in
    ``sklearn`` estimators.

    Parameters
    ----------
    dataset : array-like
        The dataset of time series to be transformed.
    dtype : data type (default: numpy.float)
        Data type for the returned dataset.

    Returns
    -------
    numpy.ndarray of shape (n_ts, sz * d)
        The transformed dataset of time series.

    Example
    -------
    >>> to_sklearn_dataset([[1, 2]], return_dim=True) # doctest: +NORMALIZE_WHITESPACE
    (array([[ 1., 2.]]), 1)
    >>> to_sklearn_dataset([[1, 2], [1, 4, 3]]) # doctest: +NORMALIZE_WHITESPACE
    array([[ 1.,  2., nan],
           [ 1.,  4., 3.]])

    See Also
    --------
    to_time_series_dataset : Transforms a time series dataset to ``tslearn``
    format.
    """
    tslearn_dataset = to_time_series_dataset(dataset, dtype=dtype)
    n_ts = tslearn_dataset.shape[0]
    d = tslearn_dataset.shape[2]
    if return_dim:
        return tslearn_dataset.reshape((n_ts, -1)), d
    else:
        return tslearn_dataset.reshape((n_ts, -1))


def timeseries_to_str(ts, fmt="%.18e"):
    """Transforms a time series to its representation as a string (used when saving time series to disk).

    Parameters
    ----------
    ts : array-like
        Time series to be represented.
    fmt : string (default: "%.18e")
        Format to be used to write each value.

    Returns
    -------
    string
        String representation of the time-series.

    Examples
    --------
    >>> timeseries_to_str([1, 2, 3, 4], fmt="%.1f")  # doctest: +NORMALIZE_WHITESPACE
    '1.0 2.0 3.0 4.0'
    >>> timeseries_to_str([[1, 3], [2, 4]], fmt="%.1f")  # doctest: +NORMALIZE_WHITESPACE
    '1.0 2.0|3.0 4.0'

    See Also
    --------
    load_timeseries_txt : Load time series from disk
    str_to_timeseries : Transform a string into a time series
    """
    ts_ = to_time_series(ts)
    dim = ts_.shape[1]
    s = ""
    for d in range(dim):
        s += " ".join([fmt % v for v in ts_[:, d]])
        if d < dim - 1:
            s += "|"
    return s


def str_to_timeseries(ts_str):
    """Reads a time series from its string representation (used when loading time series from disk).

    Parameters
    ----------
    ts_str : string
        String representation of the time-series.

    Returns
    -------
    numpy.ndarray
        Represented time-series.

    Examples
    --------
    >>> str_to_timeseries("1 2 3 4")  # doctest: +NORMALIZE_WHITESPACE
    array([[ 1.],
           [ 2.],
           [ 3.],
           [ 4.]])
    >>> str_to_timeseries("1 2|3 4")  # doctest: +NORMALIZE_WHITESPACE
    array([[ 1., 3.],
           [ 2., 4.]])

    See Also
    --------
    load_timeseries_txt : Load time series from disk
    timeseries_to_str : Transform a time series into a string
    """
    dimensions = ts_str.split("|")
    ts = [dim_str.split(" ") for dim_str in dimensions]
    return to_time_series(numpy.transpose(ts))


def save_timeseries_txt(fname, dataset, fmt="%.18e"):
    """Writes a time series dataset to disk.

    Parameters
    ----------
    fname : string
        Path to the file in which time series should be written.
    dataset : array-like
        The dataset of time series to be saved.
    fmt : string (default: "%.18e")
        Format to be used to write each value.

    See Also
    --------
    load_timeseries_txt : Load time series from disk
    """
    fp = open(fname, "wt")
    for ts in dataset:
        fp.write(timeseries_to_str(ts, fmt=fmt) + "\n")
    fp.close()


def load_timeseries_txt(fname):
    """Loads a time series dataset from disk.

    Parameters
    ----------
    fname : string
        Path to the file from which time series should be read.

    Returns
    -------
    numpy.ndarray or array of numpy.ndarray
        The dataset of time series.

    Examples
    --------
    >>> dataset = to_time_series_dataset([[1, 2, 3, 4], [1, 2, 3]])
    >>> save_timeseries_txt("tmp-tslearn-test.txt", dataset)
    >>> reloaded_dataset = load_timeseries_txt("tmp-tslearn-test.txt")
    >>> [numpy.alltrue((ts0[:ts_size(ts0)] - ts1[:ts_size(ts1)]) < 1e-6) for ts0, ts1 in zip(dataset, reloaded_dataset)]
    [True, True]
    >>> dataset = to_time_series_dataset([[1, 2, 4], [1, 2, 3]])
    >>> save_timeseries_txt("tmp-tslearn-test.txt", dataset)
    >>> reloaded_dataset = load_timeseries_txt("tmp-tslearn-test.txt")
    >>> [numpy.alltrue((ts0 - ts1) < 1e-6) for ts0, ts1 in zip(dataset, reloaded_dataset)]
    [True, True]

    See Also
    --------
    save_timeseries_txt : Save time series to disk
    """
    dataset = []
    fp = open(fname, "rt")
    for row in fp.readlines():
        ts = str_to_timeseries(row)
        dataset.append(ts)
    fp.close()
    return to_time_series_dataset(dataset)


def check_equal_size(dataset):
    """Check if all time series in the dataset have the same size.

    Parameters
    ----------
    dataset: array-like
        The dataset to check.

    Returns
    -------
    bool
        Whether all time series in the dataset have the same size.

    Examples
    --------
    >>> check_equal_size([[1, 2, 3], [4, 5, 6], [5, 3, 2]])
    True
    >>> check_equal_size([[1, 2, 3, 4], [4, 5, 6], [5, 3, 2]])
    False
    """
    dataset_ = to_time_series_dataset(dataset)
    sz = -1
    for ts in dataset_:
        if sz < 0:
            sz = ts_size(ts)
        else:
            if sz != ts_size(ts):
                return False
    return True


def ts_size(ts):
    """Returns actual time series size.

    Final timesteps that have NaN values for all dimensions will be removed from the count.

    Parameters
    ----------
    ts : array-like
        A time series.

    Returns
    -------
    int
        Actual size of the time series.

    Examples
    --------
    >>> ts_size([1, 2, 3, numpy.nan])
    3
    >>> ts_size([1, numpy.nan])
    1
    >>> ts_size([numpy.nan])
    0
    >>> ts_size([[1, 2], [2, 3], [3, 4], [numpy.nan, 2], [numpy.nan, numpy.nan]])
    4
    """
    ts_ = to_time_series(ts)
    sz = ts_.shape[0]
    while sz > 0 and not numpy.any(numpy.isfinite(ts_[sz - 1])):
        sz -= 1
    return sz


def ts_zeros(sz, d=1):
    """Returns a time series made of zero values.

    Parameters
    ----------
    sz : int
        Time series size.
    d : int (optional, default: 1)
        Time series dimensionality.

    Returns
    -------
    numpy.ndarray
        A time series made of zeros.

    Examples
    --------
    >>> ts_zeros(3, 2)  # doctest: +NORMALIZE_WHITESPACE
    array([[ 0., 0.],
           [ 0., 0.],
           [ 0., 0.]])
    >>> ts_zeros(5).shape
    (5, 1)
    """
    return numpy.zeros((sz, d))


class LabelCategorizer(BaseEstimator, TransformerMixin):
    """Transformer to transform indicator-based labels into categorical ones.

    Attributes
    ----------
    single_column_if_binary : boolean (optional, default: False)
        If true, generate a single column for binary classification case.
        Otherwise, will generate 2.
        If there are more than 2 labels, thie option will not change anything.

    Examples
    --------
    >>> y = numpy.array([-1, 2, 1, 1, 2])
    >>> lc = LabelCategorizer()
    >>> lc.fit_transform(y)  # doctest: +NORMALIZE_WHITESPACE
    array([[ 1., 0., 0.],
           [ 0., 0., 1.],
           [ 0., 1., 0.],
           [ 0., 1., 0.],
           [ 0., 0., 1.]])
    >>> lc.inverse_transform([[0, 1, 0], [0, 0, 1], [1, 0, 0]])  # doctest: +NORMALIZE_WHITESPACE
    array([ 1., 2., -1.])
    >>> import pickle
    >>> s = pickle.dumps(lc)
    >>> lc2 = pickle.loads(s)
    >>> lc2.inverse_transform([[0, 1, 0], [0, 0, 1], [1, 0, 0]])  # doctest: +NORMALIZE_WHITESPACE
    array([ 1., 2., -1.])
    >>> y = numpy.array([-1, 2, -1, -1, 2])
    >>> lc = LabelCategorizer(single_column_if_binary=True)
    >>> lc.fit_transform(y)  # doctest: +NORMALIZE_WHITESPACE
    array([[ 1.],
           [ 0.],
           [ 1.],
           [ 1.],
           [ 0.]])
    >>> lc.inverse_transform(lc.transform(y))  # doctest: +NORMALIZE_WHITESPACE
    array([-1.,  2., -1., -1.,  2.])

    References
    ----------
    .. [1] J. Grabocka et al. Learning Time-Series Shapelets. SIGKDD 2014.
    """
    def __init__(self, single_column_if_binary=False):
        self.single_column_if_binary = single_column_if_binary
        self._init()

    def _init(self):
        self.forward_match = {}
        self.backward_match = []

    def fit(self, y):
        self._init()
        values = sorted(set(y))
        for i, v in enumerate(values):
            self.forward_match[v] = i
            self.backward_match.append(v)
        return self

    def transform(self, y):
        n_classes = len(self.backward_match)
        n = len(y)
        y_out = numpy.zeros((n, n_classes))
        for i in range(n):
            y_out[i, self.forward_match[y[i]]] = 1
        if n_classes == 2 and self.single_column_if_binary:
            return y_out[:, 0].reshape((-1, 1))
        else:
            return y_out

    def inverse_transform(self, y):
        y_ = numpy.array(y)
        n, n_c = y_.shape
        if n_c == 1 and self.single_column_if_binary:
            y_ = numpy.hstack((y_, 1 - y_))
        y_out = numpy.zeros((n, ))
        for i in range(n):
            y_out[i] = self.backward_match[y_[i].argmax()]
        return y_out

    def get_params(self, deep=True):
        """Get parameters for this estimator.
        Parameters
        ----------
        deep : boolean, optional
            If True, will return the parameters for this estimator and
            contained subobjects that are estimators.
        Returns
        -------
        params : mapping of string to any
            Parameter names mapped to their values.
        """
        out = BaseEstimator.get_params(self, deep=deep)
        out["forward_match"] = self.forward_match
        out["backward_match"] = self.backward_match


def load_arff(dataset_path):
    """
    Load arff file for uni/multi variate dataset
    Parameters
    ----------
    dataset_path: string of dataset_path

    Returns
    -------
    numpy.ndarray
        y: an 1d-array of examples.
        x: a time series with dimension
            (examples, length) for uni variate time seris.
            (examples, length, channels) for multi variable time series.
    """

    data, meta = arff.loadarff(dataset_path)
    names = meta.names()  # ["input", "class"] for multi-variate

    # firstly get y_train
    y_ = data[names[-1]]  # data["class"]
    y = numpy.array(y_).astype("str")

    # get x_train
    if len(names) == 2:  # len=2 => multi-variate
        x_ = data[names[0]]
        x_ = numpy.asarray(x_.tolist())

        nb_example = x_.shape[0]
        nb_channel = x_.shape[1]
        length_one_channel = len(x_.dtype.descr)
        x = numpy.empty([nb_example, length_one_channel, nb_channel])

        for i in range(length_one_channel):
            # x_.dtype.descr: [('t1', '<f8'), ('t2', '<f8'), ('t3', '<f8')]
            time_stamp = x_.dtype.descr[i][0]  # ["t1", "t2", "t3"]
            x[:, i, :] = x_[time_stamp]

    else:  # uni-variate situation
        x_ = data[names[:-1]]
        x = numpy.asarray(x_.tolist(), dtype=numpy.float32)
        x = x.reshape(len(x), -1, 1)

    return x, y


# Function for converting arff list to csv list
def to_txt(content):
    data = False
    header = ""
    new_x, new_y = [], []
    nb_example = 0
    for line in content:
        if not data:
            if "@attribute" in line:
                attri = line.split()
                columnName = attri[attri.index("@attribute") + 1]
                header = header + columnName + ","
            elif "@data" in line:
                data = True
                header = (',').join(header.split(',')[1:-2])
                header += '\n'
                # new_x.append(header)
        else:
            nb_example += 1
            temp_line = line.replace('"', "'").split("',")
            new_x.append(temp_line[0].replace("'", '') + '\n')
            new_y.append(temp_line[-1])
    one_channel = line.rstrip().split('\\n')
    # channels = len(one_channel)
    # not precise (because SpokenArabic has an extra '\n' in each example)
    channels = -1
    length = len(one_channel[0].split(','))
    return new_x, new_y, channels, length, nb_example


def remake_files(dataset_full_path):
    folder_all = os.listdir(dataset_full_path)
    dataset_name = dataset_full_path.split('/')[-1]
    folder = os.path.join(dataset_full_path, dataset_name)
    files = [folder + '_TEST.arff', folder + '_TRAIN.arff']

    # Main loop for reading and writing files
    for file in files:
        with open(file, "r") as inFile:
            content = inFile.readlines()
            name, ext = os.path.splitext(inFile.name)
            new_x, new_y, channels, length, nb_example = to_txt(content)
            new_xx = []
            for item in new_x:
                new_xx.append(item.replace("\\n\n", "\n").replace("\\n", ","))
            with open(name + "_x.txt", "w") as outFile:
                outFile.write('#{}, {}, {}\n'.format(nb_example, channels, length))
                outFile.writelines(new_xx)
            with open(name + "_y.txt", "w") as outFile:
                outFile.writelines(new_y)


def load_multivariate_x(f_name):
    with open(f_name, 'r') as f:
        shape = map(int, f.readline()[1:].split(','))
        # load txt as (nb_example, channels, length)
        # columns = range(tuple(shape)[2])
        temp = numpy.loadtxt(f, delimiter=',').reshape(tuple(shape))
        # reshpe to (nb_example, length, channels)
        xx = temp.transpose(0, 2, 1)
    return xx
